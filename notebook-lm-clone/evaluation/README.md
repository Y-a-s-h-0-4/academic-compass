# LLM Benchmarking for Academic Compass

This folder provides a reproducible benchmark runner to compare multiple LLMs and prompting modes:
- `zero_shot`: direct QA without retrieval context.
- `rag`: response using your indexed project documents.
- `rag_cot`: RAG with a chain-of-thought-style instruction.

## Files
- `benchmark_dataset.jsonl`: QA benchmark set.
- `benchmark_config.json`: model matrix + retrieval docs.
- `run_benchmark.py`: executes comparisons and writes reports.

## Dataset format
Each line in `benchmark_dataset.jsonl` is one JSON object:

```json
{
  "id": "q1",
  "question": "Your question",
  "ground_truth": "Reference answer",
  "expected_sources": ["notes.txt"]
}
```

## Config format
`benchmark_config.json` controls which models/modes run.

```json
{
  "documents": ["data/notes.txt"],
  "judge_model": {"provider": "openai", "model": "gpt-4o-mini"},
  "models": [
    {
      "name": "GPT-4o-mini",
      "provider": "openai",
      "model": "gpt-4o-mini",
      "modes": ["zero_shot", "rag", "rag_cot"]
    }
  ]
}
```

## Metrics produced
- `factuality`: LLM-judge score from 0 to 1.
- `citation_precision`, `citation_recall`: source overlap vs expected sources.
- `token_f1`: token-level overlap with reference answer.
- `rouge_l_f1`: longest-common-subsequence based overlap.
- `semantic_similarity`: cosine similarity using your embedding model.

## Run
From `notebook-lm-clone/`:

```powershell
python evaluation/run_benchmark.py --dataset evaluation/benchmark_dataset.jsonl --config evaluation/benchmark_config.json
```

Optional:

```powershell
python evaluation/run_benchmark.py --output-dir outputs/benchmark --top-k 8
```

## Output
A timestamped folder is created under `outputs/benchmark/` with:
- `per_question.csv`
- `summary.csv`
- `summary.md`
- `raw_results.jsonl`

Use `summary.md` for quick reports and `per_question.csv` for deeper analysis or plotting.
