import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from crewai import LLM

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.document_processing.doc_processor import DocumentProcessor
from src.embeddings.embedding_generator import EmbeddingGenerator
from src.generation.rag import RAGGenerator
from src.vector_database.milvus_vector_db import MilvusVectorDB


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> List[str]:
    if not text:
        return []
    return normalize_text(text).split()


def token_f1(prediction: str, reference: str) -> float:
    pred_tokens = tokenize(prediction)
    ref_tokens = tokenize(reference)
    if not pred_tokens or not ref_tokens:
        return 0.0

    pred_counts: Dict[str, int] = defaultdict(int)
    ref_counts: Dict[str, int] = defaultdict(int)

    for token in pred_tokens:
        pred_counts[token] += 1
    for token in ref_tokens:
        ref_counts[token] += 1

    common = 0
    for token, count in pred_counts.items():
        common += min(count, ref_counts.get(token, 0))

    if common == 0:
        return 0.0

    precision = common / len(pred_tokens)
    recall = common / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def lcs_length(a: List[str], b: List[str]) -> int:
    if not a or not b:
        return 0
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i, token_a in enumerate(a, start=1):
        for j, token_b in enumerate(b, start=1):
            if token_a == token_b:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def rouge_l_f1(prediction: str, reference: str) -> float:
    pred_tokens = tokenize(prediction)
    ref_tokens = tokenize(reference)
    if not pred_tokens or not ref_tokens:
        return 0.0

    lcs = lcs_length(pred_tokens, ref_tokens)
    precision = lcs / len(pred_tokens)
    recall = lcs / len(ref_tokens)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = float(np.linalg.norm(a))
    b_norm = float(np.linalg.norm(b))
    if a_norm == 0.0 or b_norm == 0.0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def citation_precision_recall(predicted: Set[str], expected: Set[str]) -> Tuple[float, float]:
    if not predicted and not expected:
        return 1.0, 1.0
    if not predicted:
        return 0.0, 0.0 if expected else 1.0

    true_positive = len(predicted.intersection(expected))
    precision = true_positive / len(predicted) if predicted else 0.0
    recall = true_positive / len(expected) if expected else 1.0
    return precision, recall


def get_provider_api_key(provider: str) -> Optional[str]:
    provider = provider.lower().strip()
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    if provider in {"gemini", "google"}:
        return os.getenv("GEMINI_API_KEY")
    return None


def build_model_identifier(provider: str, model: str) -> str:
    if "/" in model:
        return model
    normalized_provider = "gemini" if provider in {"gemini", "google"} else provider
    return f"{normalized_provider}/{model}"


@dataclass
class ModelSpec:
    name: str
    provider: str
    model: str
    modes: List[str]
    temperature: float = 0.1
    max_tokens: int = 1000


class FactualityJudge:
    def __init__(self, provider: str, model: str):
        api_key = get_provider_api_key(provider)
        if not api_key:
            raise ValueError(f"Missing API key for factuality judge provider '{provider}'")

        model_id = build_model_identifier(provider, model)
        self.llm = LLM(model=model_id, api_key=api_key, temperature=0, max_tokens=300)

    def score(self, question: str, reference: str, prediction: str) -> Tuple[float, str]:
        prompt = (
            "You are a strict factuality evaluator.\n"
            "Given question, reference answer, and model answer, return JSON only with this schema:\n"
            "{\"score\": <float from 0 to 1>, \"reason\": \"short reason\"}.\n"
            "Score should reflect factual consistency of model answer with reference answer.\n"
            f"Question: {question}\n"
            f"Reference: {reference}\n"
            f"Model Answer: {prediction}\n"
        )

        raw = self.llm.call(prompt)
        data = self._safe_parse_json(raw)
        score = float(data.get("score", 0.0))
        reason = str(data.get("reason", "no reason provided"))
        score = max(0.0, min(1.0, score))
        return score, reason

    @staticmethod
    def _safe_parse_json(text: str) -> Dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return {}
            return {}


class BenchmarkRunner:
    def __init__(self, dataset_path: Path, config_path: Path, output_root: Path, top_k: int):
        self.dataset_path = dataset_path
        self.config_path = config_path
        self.output_root = output_root
        self.top_k = top_k

        self.dataset = self._load_dataset(dataset_path)
        self.config = self._load_json(config_path)

        self.documents = self.config.get("documents", [])
        self.model_specs = [ModelSpec(**m) for m in self.config.get("models", [])]

        judge_cfg = self.config.get("judge_model")
        self.judge: Optional[FactualityJudge] = None
        if judge_cfg:
            try:
                self.judge = FactualityJudge(
                    provider=judge_cfg["provider"],
                    model=judge_cfg["model"],
                )
            except Exception as exc:
                print(f"[WARN] Judge init failed, factuality will be skipped: {exc}")

        self.embedding_generator = EmbeddingGenerator()

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _load_dataset(path: Path) -> List[Dict[str, Any]]:
        rows = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows

    def _build_vector_store(self, collection_name: str) -> MilvusVectorDB:
        vector_db = MilvusVectorDB(collection_name=collection_name)
        doc_processor = DocumentProcessor()

        all_chunks = []
        for doc_path in self.documents:
            resolved = ROOT_DIR / doc_path
            chunks = doc_processor.process_document(str(resolved))
            all_chunks.extend(chunks)

        embedded_chunks = self.embedding_generator.generate_embeddings(all_chunks)
        vector_db.insert_embeddings(embedded_chunks)
        return vector_db

    def _build_llm(self, provider: str, model: str, temperature: float, max_tokens: int) -> LLM:
        api_key = get_provider_api_key(provider)
        if not api_key:
            raise ValueError(f"Missing API key for provider '{provider}'")
        model_id = build_model_identifier(provider, model)
        return LLM(model=model_id, api_key=api_key, temperature=temperature, max_tokens=max_tokens)

    def _run_zero_shot(self, llm: LLM, question: str, cot: bool) -> str:
        if cot:
            prompt = (
                "Answer the question carefully. Think through key facts before producing the final answer. "
                "Return only the final answer text.\n"
                f"Question: {question}"
            )
        else:
            prompt = f"Answer the question briefly and factually.\nQuestion: {question}"
        return llm.call(prompt)

    def _run_rag(self, rag_generator: RAGGenerator, question: str, cot: bool) -> Tuple[str, List[Dict[str, Any]], int]:
        if cot:
            question = (
                "Reason through the evidence from context before finalizing your answer. "
                "Then provide a concise final answer.\n"
                f"{question}"
            )

        result = rag_generator.generate_response(query=question, top_k=self.top_k)
        return result.response, result.sources_used, result.retrieval_count

    @staticmethod
    def _extract_predicted_sources(sources_used: List[Dict[str, Any]]) -> Set[str]:
        names = set()
        for source in sources_used:
            source_name = source.get("source_file")
            if source_name:
                names.add(Path(source_name).name.lower())
        return names

    def run(self) -> Path:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        per_question_rows: List[Dict[str, Any]] = []

        for spec in self.model_specs:
            print(f"[INFO] Running model: {spec.name}")
            for mode in spec.modes:
                print(f"[INFO]  - Mode: {mode}")
                llm = self._build_llm(spec.provider, spec.model, spec.temperature, spec.max_tokens)

                vector_db = None
                rag_generator = None
                needs_rag = mode in {"rag", "rag_cot"}
                if needs_rag:
                    collection_name = f"bench_{spec.name}_{mode}_{run_id}".lower().replace(" ", "_")
                    vector_db = self._build_vector_store(collection_name=collection_name)
                    rag_generator = RAGGenerator(
                        embedding_generator=self.embedding_generator,
                        vector_db=vector_db,
                        openai_api_key=os.getenv("OPENAI_API_KEY"),
                        gemini_api_key=os.getenv("GEMINI_API_KEY"),
                        provider=spec.provider,
                        model_name=spec.model,
                        temperature=spec.temperature,
                        max_tokens=spec.max_tokens,
                    )

                for sample in self.dataset:
                    question_id = sample.get("id", "")
                    question = sample["question"]
                    reference = sample["ground_truth"]
                    expected_sources = {s.lower() for s in sample.get("expected_sources", [])}

                    response_text = ""
                    sources_used: List[Dict[str, Any]] = []
                    retrieval_count = 0
                    error_message = ""

                    try:
                        if mode == "zero_shot":
                            response_text = self._run_zero_shot(llm, question, cot=False)
                        elif mode == "zero_shot_cot":
                            response_text = self._run_zero_shot(llm, question, cot=True)
                        elif mode == "rag":
                            response_text, sources_used, retrieval_count = self._run_rag(rag_generator, question, cot=False)
                        elif mode == "rag_cot":
                            response_text, sources_used, retrieval_count = self._run_rag(rag_generator, question, cot=True)
                        else:
                            raise ValueError(f"Unsupported mode: {mode}")
                    except Exception as exc:
                        error_message = str(exc)

                    pred_sources = self._extract_predicted_sources(sources_used)
                    citation_precision, citation_recall = citation_precision_recall(pred_sources, expected_sources)

                    tf1 = token_f1(response_text, reference)
                    rouge = rouge_l_f1(response_text, reference)

                    response_vec = self.embedding_generator.generate_query_embedding(response_text)
                    reference_vec = self.embedding_generator.generate_query_embedding(reference)
                    semantic_sim = cosine_similarity(response_vec, reference_vec)

                    factuality = None
                    factuality_reason = ""
                    if self.judge and not error_message:
                        try:
                            factuality, factuality_reason = self.judge.score(question, reference, response_text)
                        except Exception as exc:
                            factuality_reason = f"judge_failed: {exc}"

                    per_question_rows.append(
                        {
                            "model": spec.name,
                            "provider": spec.provider,
                            "mode": mode,
                            "question_id": question_id,
                            "question": question,
                            "reference": reference,
                            "response": response_text,
                            "retrieval_count": retrieval_count,
                            "predicted_sources": ";".join(sorted(pred_sources)),
                            "expected_sources": ";".join(sorted(expected_sources)),
                            "citation_precision": round(citation_precision, 4),
                            "citation_recall": round(citation_recall, 4),
                            "token_f1": round(tf1, 4),
                            "rouge_l_f1": round(rouge, 4),
                            "semantic_similarity": round(semantic_sim, 4),
                            "factuality": None if factuality is None else round(factuality, 4),
                            "factuality_reason": factuality_reason,
                            "error": error_message,
                        }
                    )

                if vector_db is not None:
                    try:
                        vector_db.delete_collection()
                    except Exception:
                        pass
                    vector_db.close()

        self._write_outputs(run_dir, per_question_rows)
        return run_dir

    def _write_outputs(self, run_dir: Path, rows: List[Dict[str, Any]]) -> None:
        per_question_path = run_dir / "per_question.csv"
        raw_jsonl_path = run_dir / "raw_results.jsonl"
        summary_csv_path = run_dir / "summary.csv"
        summary_md_path = run_dir / "summary.md"

        if not rows:
            raise ValueError("No benchmark rows were produced")

        fieldnames = list(rows[0].keys())
        with per_question_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        with raw_jsonl_path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=True) + "\n")

        grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[(row["model"], row["mode"])].append(row)

        summary_rows: List[Dict[str, Any]] = []
        for (model, mode), group_rows in grouped.items():
            def avg(metric: str) -> float:
                values = [r[metric] for r in group_rows if isinstance(r[metric], (int, float))]
                return round(sum(values) / len(values), 4) if values else 0.0

            summary_rows.append(
                {
                    "model": model,
                    "mode": mode,
                    "samples": len(group_rows),
                    "factuality": avg("factuality"),
                    "citation_precision": avg("citation_precision"),
                    "citation_recall": avg("citation_recall"),
                    "rouge_l_f1": avg("rouge_l_f1"),
                    "token_f1": avg("token_f1"),
                    "semantic_similarity": avg("semantic_similarity"),
                }
            )

        summary_fields = [
            "model",
            "mode",
            "samples",
            "factuality",
            "citation_precision",
            "citation_recall",
            "rouge_l_f1",
            "token_f1",
            "semantic_similarity",
        ]

        with summary_csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=summary_fields)
            writer.writeheader()
            writer.writerows(summary_rows)

        lines = [
            "| Model | Mode | Samples | Factuality | Citation Precision | Citation Recall | ROUGE-L F1 | Token F1 | Semantic Similarity |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in summary_rows:
            lines.append(
                f"| {row['model']} | {row['mode']} | {row['samples']} | {row['factuality']:.4f} | "
                f"{row['citation_precision']:.4f} | {row['citation_recall']:.4f} | {row['rouge_l_f1']:.4f} | "
                f"{row['token_f1']:.4f} | {row['semantic_similarity']:.4f} |"
            )

        summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-model QA benchmarks for Academic Compass")
    parser.add_argument("--dataset", type=Path, default=Path("evaluation/benchmark_dataset.jsonl"))
    parser.add_argument("--config", type=Path, default=Path("evaluation/benchmark_config.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/benchmark"))
    parser.add_argument("--top-k", type=int, default=10, help="Top-k retrieved chunks for RAG modes")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    runner = BenchmarkRunner(
        dataset_path=args.dataset,
        config_path=args.config,
        output_root=args.output_dir,
        top_k=args.top_k,
    )

    run_dir = runner.run()
    print(f"[DONE] Benchmark completed. Results in: {run_dir}")


if __name__ == "__main__":
    main()
