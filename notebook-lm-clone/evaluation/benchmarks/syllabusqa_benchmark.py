"""
SyllabusQA Benchmark Runner
Tests multiple models on the SyllabusQA dataset
"""

from dotenv import load_dotenv
import json
import csv
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from model_providers import ModelConfig, UnifiedLLMProvider

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SyllabusQABenchmark:
    """
    Benchmark runner for SyllabusQA dataset across multiple models
    """
    
    def __init__(self, output_dir: str = "outputs/syllabusqa_results", sample_size: Optional[int] = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sample_size = sample_size
        self.results = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def load_dataset(self, dataset_path: str, split: str = "test") -> List[Dict[str, Any]]:
        """
        Load SyllabusQA dataset from CSV
        Expected columns: id, question, answer, sources (or similar)
        """
        csv_path = Path(dataset_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"Dataset not found: {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"✓ Loaded {len(df)} samples from {csv_path}")
            
            # Sample if requested
            if self.sample_size and len(df) > self.sample_size:
                df = df.sample(n=self.sample_size, random_state=42)
                logger.info(f"Sampled {len(df)} rows")
            
            return df.to_dict('records')
        
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise
    
    def run_benchmark(
        self,
        dataset: List[Dict[str, Any]],
        models: List[ModelConfig],
        modes: List[str] = None
    ):
        """
        Run benchmark across models and modes
        
        Args:
            dataset: List of QA samples
            models: List of ModelConfig objects
            modes: List of prompting modes (zero_shot, rag, rag_cot)
        """
        if modes is None:
            modes = ["zero_shot"]
        
        logger.info(f"Starting benchmark with {len(models)} models across {len(modes)} modes")
        logger.info(f"Total requests: {len(dataset) * len(models) * len(modes)}")
        
        for model_config in models:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Testing {model_config.name} ({model_config.model_id})")
                logger.info(f"{'='*60}")
                
                provider = UnifiedLLMProvider(model_config)
                model_results = self._test_model(provider, model_config, dataset, modes)
                self.results.extend(model_results)
                
                logger.info(f"✓ Completed {model_config.name}")
            
            except Exception as e:
                logger.error(f"Failed to test {model_config.name}: {e}")
                continue
    
    def _test_model(
        self,
        provider: UnifiedLLMProvider,
        config: ModelConfig,
        dataset: List[Dict[str, Any]],
        modes: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Test a single model across dataset
        """
        results = []
        total = len(dataset) * len(modes)
        current = 0
        
        for idx, item in enumerate(dataset):
            for mode in modes:
                current += 1
                try:
                    prompt = self._build_prompt(item, mode)
                    response = provider.generate(prompt)
                    
                    result = {
                        "timestamp": datetime.now().isoformat(),
                        "model_name": config.name,
                        "model_id": config.model_id,
                        "provider": config.provider,
                        "mode": mode,
                        "temperature": config.temperature,
                        "question_id": item.get("id", f"q{idx}"),
                        "question": item.get("question", ""),
                        "ground_truth": item.get("answer", ""),
                        "prediction": response,
                        "context": item.get("context", ""),
                        "sources": item.get("sources", []),
                    }
                    results.append(result)
                    
                    # Progress
                    if current % 5 == 0:
                        logger.info(f"  [{current}/{total}] Processed {idx+1} questions")
                
                except Exception as e:
                    logger.warning(f"Error for question {item.get('id')}: {e}")
                    results.append({
                        "model_name": config.name,
                        "model_id": config.model_id,
                        "provider": config.provider,
                        "mode": mode,
                        "question_id": item.get("id"),
                        "question": item.get("question", ""),
                        "ground_truth": item.get("answer", ""),
                        "prediction": f"[ERROR: {str(e)}]",
                    })
        
        return results
    
    def _build_prompt(self, item: Dict[str, Any], mode: str) -> str:
        """
        Build prompt based on mode
        
        Modes:
            - zero_shot: Direct question answering
            - rag: Question with retrieved context
            - rag_cot: RAG with chain-of-thought
        """
        question = item.get("question", "")
        context = item.get("context", "")
        
        if mode == "zero_shot":
            return f"Answer the following question:\n\n{question}"
        
        elif mode == "rag":
            if context:
                return f"""Using the provided context, answer the question.

Context:
{context}

Question: {question}

Answer:"""
            else:
                return f"Answer the following question:\n\n{question}"
        
        elif mode == "rag_cot":
            if context:
                return f"""Using the provided context, answer the question step-by-step.

Context:
{context}

Question: {question}

Think through this step-by-step:
1. What information in the context is relevant to the question?
2. What are the key details that help answer it?
3. What is the complete answer?

Answer:"""
            else:
                return f"""Answer the following question step-by-step:

Question: {question}

Think through this step-by-step:
1. What information is needed to answer this?
2. What are the key details?
3. What is the complete answer?

Answer:"""
        
        else:
            return f"Answer: {question}"
    
    def save_results(self) -> Dict[str, Path]:
        """
        Save results in multiple formats
        
        Returns:
            Dict with paths to saved files
        """
        if not self.results:
            logger.warning("No results to save")
            return {}
        
        saved_files = {}
        
        try:
            # JSONL format (one result per line)
            jsonl_path = self.output_dir / f"raw_results_{self.timestamp}.jsonl"
            with open(jsonl_path, "w") as f:
                for result in self.results:
                    f.write(json.dumps(result) + "\n")
            saved_files["jsonl"] = jsonl_path
            logger.info(f"✓ Saved JSONL: {jsonl_path}")
            
            # CSV format
            csv_path = self.output_dir / f"results_{self.timestamp}.csv"
            df = pd.DataFrame(self.results)
            df.to_csv(csv_path, index=False)
            saved_files["csv"] = csv_path
            logger.info(f"✓ Saved CSV: {csv_path}")
            
            # JSON format
            json_path = self.output_dir / f"results_{self.timestamp}.json"
            with open(json_path, "w") as f:
                json.dump(self.results, f, indent=2)
            saved_files["json"] = json_path
            logger.info(f"✓ Saved JSON: {json_path}")
            
            logger.info(f"\nResults saved to: {self.output_dir}")
            return saved_files
        
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise
    
    def generate_summary(self) -> str:
        """
        Generate summary statistics of the benchmark run
        """
        if not self.results:
            return "No results to summarize"
        
        df = pd.DataFrame(self.results)
        
        summary = f"""
{'='*70}
SYLLABUSQA BENCHMARK SUMMARY
{'='*70}

Run timestamp: {datetime.now().isoformat()}
Total results: {len(self.results)}

Models tested:
{df['model_name'].unique().tolist()}

Modes tested:
{df['mode'].unique().tolist()}

Results by model:
{df.groupby('model_name').size().to_string()}

Results by provider:
{df.groupby('provider').size().to_string()}

Results by mode:
{df.groupby('mode').size().to_string()}

{'='*70}
"""
        return summary


def load_config(config_path: str) -> Dict[str, Any]:
    """Load benchmark configuration from JSON"""
    with open(config_path, "r") as f:
        return json.load(f)


def main():
    load_dotenv(ROOT_DIR.parent / ".env", override=False)
    load_dotenv(ROOT_DIR / ".env", override=False)

    parser = argparse.ArgumentParser(description="SyllabusQA Benchmark Runner")
    parser.add_argument("--config", required=True, help="Path to config JSON file")
    parser.add_argument("--dataset", required=True, help="Path to dataset CSV file")
    parser.add_argument("--output-dir", default="outputs/syllabusqa_results", help="Output directory")
    parser.add_argument("--sample-size", type=int, default=None, help="Number of samples to test (default: all)")
    parser.add_argument("--models", nargs="+", default=None, help="Specific models to test")
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Initialize benchmark
    benchmark = SyllabusQABenchmark(output_dir=args.output_dir, sample_size=args.sample_size)
    
    # Load dataset
    dataset = benchmark.load_dataset(args.dataset)
    
    # Filter models if specified
    model_configs = config.get("models", [])
    if args.models:
        model_configs = [m for m in model_configs if m.get("model_id", m.get("model")) in args.models]
    
    # Create ModelConfig objects
    models = [
        ModelConfig(
            provider=m["provider"],
            model_id=m.get("model_id", m.get("model")),
            name=m.get("name", m.get("model_id", m.get("model", ""))),
            temperature=m.get("temperature", 0.1),
            max_tokens=m.get("max_tokens", 1000),
            top_p=m.get("top_p", 1.0)
        )
        for m in model_configs
    ]
    
    # Run benchmark
    modes = config.get("modes", ["zero_shot"])
    benchmark.run_benchmark(dataset, models, modes)
    
    # Save results
    benchmark.save_results()
    
    # Print summary
    print(benchmark.generate_summary())


if __name__ == "__main__":
    main()
