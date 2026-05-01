# Integration Guide: SyllabusQA Testing with Academic Compass

How to use SyllabusQA dataset to test and improve your Academic Compass project.

## Overview

The SyllabusQA testing framework allows you to:

1. **Benchmark** different LLMs (GPT, Gemini, Claude) on standardized domain data
2. **Compare** your project's performance vs commercial models
3. **Identify** which models/prompting strategies work best
4. **Optimize** your system before production deployment

## Your Current Setup

Your Academic Compass project has:

- ✅ FastAPI backend with RAG pipeline (`notebook-lm-clone/`)
- ✅ Document processing & embeddings
- ✅ Existing evaluation framework
- ✅ Multiple model support (Gemini, OpenAI)
- ✅ Benchmarking infrastructure

## Integration Steps

### Step 1: Run Baseline Test (30 minutes)

Test your current setup against SyllabusQA:

```bash
cd c:\Projects\academic-compass

# Quick sample
python notebook-lm-clone/evaluation/quickstart.py

# Then run:
python notebook-lm-clone/evaluation/benchmarks/syllabusqa_benchmark.py \
  --config notebook-lm-clone/evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv \
  --sample-size 50 \
  --models gpt-4o-mini gemini-2.0-flash
```

**Expected output**: 
- ~50 QA results
- Performance metrics (Token F1, word overlap, etc.)
- ~$0.50-2 cost

### Step 2: Analyze Results (10 minutes)

```bash
python notebook-lm-clone/evaluation/comparison_analysis.py \
  --results outputs/syllabusqa_results/raw_results_*.jsonl
```

**Creates**:
- `ANALYSIS_REPORT.md` - Full findings
- `model_comparison.csv` - Which models perform best
- `mode_comparison.csv` - Does RAG help?
- CSV files for Excel analysis

### Step 3: Full Benchmark (2-4 hours)

```bash
python notebook-lm-clone/evaluation/benchmarks/syllabusqa_benchmark.py \
  --config notebook-lm-clone/evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv
```

**Tests**:
- 3 models × default config = comprehensive comparison
- Zero-shot, RAG, and chain-of-thought modes
- ~1,000 questions
- ~$30-60 cost

### Step 4: Optimize Your System

Based on results, improve:

```python
# notebook-lm-clone/api/main.py

# Use best-performing model
BEST_MODEL = "gemini-2.0-flash"  # Or whatever tests best

# Use best mode
USE_RAG = True  # If RAG improves scores
USE_COT = True  # If chain-of-thought helps
```

## Test Scenarios

### Scenario 1: Find Best Model for Your Domain

```bash
# Test all models on your domain
python notebook-lm-clone/evaluation/benchmarks/syllabusqa_benchmark.py \
  --config notebook-lm-clone/evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv

# View results
cat outputs/syllabusqa_results/model_comparison.csv
```

**Decision**: Use model with highest `token_f1_mean`

### Scenario 2: Compare RAG vs Zero-Shot

Edit `syllabusqa_config.json`:

```json
"modes": ["zero_shot", "rag"]
```

Then run benchmark and check `mode_comparison.csv`

### Scenario 3: Cost-Benefit Analysis

Compare:
- **Quality**: Which model gives best answers?
- **Cost**: API pricing per 1K tokens
- **Speed**: Response time
- **Trade-off**: Use smaller model if close performance

```python
# Example decision matrix
import pandas as pd

results = pd.read_csv("outputs/syllabusqa_results/model_comparison.csv")
results['cost_per_1k_tokens'] = [0.03, 0.015, 0.04, 0.075, 0.04]  # Sample prices
results['quality_to_cost'] = results['token_f1_mean'] / results['cost_per_1k_tokens']

print(results.sort_values('quality_to_cost', ascending=False))
```

### Scenario 4: Test Your Custom Prompts

Modify prompts in `syllabusqa_benchmark.py`:

```python
def _build_prompt(self, item, mode):
    question = item['question']
    context = item.get('context', '')
    
    if mode == "your_mode":
        return f"""Your custom prompt format
        
Question: {question}
Context: {context}

Provide a concise answer:"""
```

Then test:

```bash
python notebook-lm-clone/evaluation/benchmarks/syllabusqa_benchmark.py \
  --config notebook-lm-clone/evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv \
  --sample-size 100
```

## Expected Results

### Typical Metrics

For course QA tasks like SyllabusQA:

| Model | Token F1 | Word Overlap | Exact Match |
|-------|----------|--------------|-------------|
| GPT-4o-mini | 0.70-0.75 | 0.60-0.65 | 10-15% |
| Gemini-2.0 | 0.68-0.73 | 0.58-0.63 | 8-12% |
| Claude-Sonnet | 0.72-0.78 | 0.62-0.68 | 12-18% |

**Note**: Actual results vary by domain and context quality

### Improvement with RAG

Expect 5-15% boost with retrieval:

- Zero-shot Token F1: ~0.65
- RAG Token F1: ~0.70-0.75 (+7-15%)

### Chain-of-Thought Impact

CoT can help on complex questions:

- Standard RAG: 0.70
- RAG + CoT: 0.72-0.74 (+2-4%)

## Integration with Your Backend

### Option 1: Update Model Selection

```python
# notebook-lm-clone/src/generation/rag.py

# Based on benchmark results, use best model
class RAGGenerator:
    def __init__(self, model_name: str = "best_performer"):
        # Test showed gemini-2.0-flash performs well
        if model_name == "best_performer":
            self.model = "gemini-2.0-flash"
        self.llm = initialize_model(self.model)
```

### Option 2: Add Model Selection Parameter

```python
# Allow frontend to select model
@app.post("/generate")
def generate(query: str, model: str = "best"):
    if model == "best":
        model = "gemini-2.0-flash"  # From benchmarks
    elif model == "fast":
        model = "gpt-4o-mini"
    elif model == "quality":
        model = "claude-3-5-sonnet"
    
    return generate_with_model(query, model)
```

### Option 3: A/B Testing

Compare models on live data:

```python
import random

@app.post("/generate")
def generate(query: str):
    model = random.choice(["gemini-2.0-flash", "gpt-4o-mini"])
    result = generate_with_model(query, model)
    
    # Log for later analysis
    log_performance(query, model, result)
    return result
```

## Comparing with Your System

### Extract Your Answers

If you have existing Q&A pairs tested:

```python
# Convert your format to SyllabusQA format
your_results = pd.read_csv("your_results.csv")

benchmark_format = pd.DataFrame({
    'id': your_results['question_id'],
    'question': your_results['question'],
    'answer': your_results['your_answer'],
    'ground_truth': your_results['expected_answer'],
    'context': your_results['context'],
})

benchmark_format.to_csv('your_results_formatted.csv', index=False)
```

### Evaluate Your Results

```python
from evaluation.metrics.syllabusqa_metrics import SyllabusQAMetrics

metrics = SyllabusQAMetrics()

for idx, row in benchmark_format.iterrows():
    scores = metrics.compute_per_sample_metrics(
        row['answer'],
        row['ground_truth']
    )
    print(f"Q{idx}: Token F1 = {scores['token_f1']:.3f}")
```

## Recommendations by Scenario

### Scenario A: Budget-Conscious (< $10/month)

```json
{
  "primary_model": "gemini-2.0-flash",
  "fallback_model": "gpt-4o-mini",
  "modes": ["zero_shot"],
  "enable_caching": true
}
```

- **Cost**: ~$5/month for 10k calls
- **Quality**: ~0.70-0.72 Token F1

### Scenario B: Quality-Focused (< $50/month)

```json
{
  "primary_model": "claude-3-5-sonnet",
  "fallback_model": "gemini-2.0-flash",
  "modes": ["zero_shot", "rag"],
  "enable_caching": true
}
```

- **Cost**: ~$30/month for 10k calls
- **Quality**: ~0.73-0.76 Token F1

### Scenario C: Maximum Performance (No Budget Limit)

```json
{
  "primary_model": "claude-3-opus",
  "secondary_model": "gpt-4-turbo",
  "fallback_model": "gemini-1.5-pro",
  "modes": ["rag", "rag_cot"],
  "ensemble": true
}
```

- **Cost**: ~$100-200/month
- **Quality**: ~0.76-0.82 Token F1 (with ensemble)

## Monitoring & Continuous Improvement

### Weekly Benchmark

```bash
# Every week, run benchmark to track improvements
0 0 * * 0 cd /path/to/project && \
  python notebook-lm-clone/evaluation/benchmarks/syllabusqa_benchmark.py \
    --config evaluation/benchmarks/syllabusqa_config.json \
    --dataset syllabusqa-data/data/dataset_split/test.csv \
    --sample-size 200 \
    --models gpt-4o-mini gemini-2.0-flash
```

### Track Metrics Over Time

```python
import json
from pathlib import Path

# Aggregate runs
results_dir = Path("outputs/syllabusqa_results")
all_runs = []

for result_file in results_dir.glob("model_comparison_*.csv"):
    df = pd.read_csv(result_file)
    df['run_date'] = result_file.stem.split('_')[2]
    all_runs.append(df)

combined = pd.concat(all_runs)
combined.to_csv("benchmark_history.csv")

# Plot trends
combined.groupby('run_date')['token_f1_mean'].plot()
```

## Troubleshooting Common Issues

### Q: My scores are lower than examples
**A**: Different datasets, questions, and domains. Your metrics are valid for your use case.

### Q: RAG makes scores worse
**A**: Check retrieval quality:
- Is context relevant?
- Is context too long/noisy?
- Try different chunk sizes
- Verify embedding quality

### Q: One model consistently fails
**A**: Check:
- API key validity
- Rate limiting
- Model availability
- Network connectivity

### Q: Costs are too high
**A**: Options:
- Use smaller models (gpt-4o-mini)
- Reduce sample size
- Test only zero-shot mode
- Use cached results
- Batch requests

## Next Steps

1. **Run quickstart**: `python notebook-lm-clone/evaluation/quickstart.py`
2. **Test baseline**: Run 50-question sample
3. **Analyze results**: Generate comparison report
4. **Optimize system**: Use best model/settings
5. **Deploy**: Update your backend with learnings
6. **Monitor**: Run weekly benchmarks

## Resources

- **Testing Guide**: [SYLLABUSQA_TESTING_GUIDE.md](../SYLLABUSQA_TESTING_GUIDE.md)
- **README**: [README_SYLLABUSQA.md](./README_SYLLABUSQA.md)
- **SyllabusQA Repo**: https://github.com/umass-ml4ed/SyllabusQA
- **Paper**: https://arxiv.org/pdf/2403.14666

---

**Questions?** Check README_SYLLABUSQA.md or see SYLLABUSQA_TESTING_GUIDE.md
