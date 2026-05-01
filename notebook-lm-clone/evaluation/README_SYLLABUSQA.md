# SyllabusQA Benchmark Testing Framework

Complete multi-model testing framework for Academic Compass against the SyllabusQA dataset.

## Quick Start (2 minutes)

```bash
# Navigate to project root
cd c:\Projects\academic-compass

# Run setup wizard
python notebook-lm-clone/evaluation/quickstart.py

# Follow prompts to:
# 1. Install dependencies
# 2. Clone SyllabusQA dataset
# 3. Configure API keys
# 4. Optionally run sample benchmark
```

## What is SyllabusQA?

- **Dataset**: Course logistics question-answering dataset (ACL 2024)
- **Size**: ~1,000+ QA pairs from real syllabi
- **Domain**: University course logistics questions
- **Evaluation Metrics**: ROUGE, BERTScore, Token F1
- **Paper**: https://arxiv.org/pdf/2403.14666

## Project Structure

```
notebook-lm-clone/evaluation/
├── benchmarks/
│   ├── __init__.py
│   ├── model_providers.py      # Unified LLM provider interface
│   ├── syllabusqa_benchmark.py # Benchmark runner
│   └── syllabusqa_config.json  # Model configurations
├── metrics/
│   └── syllabusqa_metrics.py   # Metric computation
├── comparison_analysis.py       # Analysis & reporting
├── quickstart.py               # Setup wizard
└── README.md                   # This file
```

## Supported Models

### OpenAI
- `gpt-4-turbo`
- `gpt-4o`
- `gpt-4o-mini`

### Google Gemini
- `gemini-2.0-flash`
- `gemini-1.5-pro`

### Anthropic Claude
- `claude-3-5-sonnet-20241022`
- `claude-3-opus-20240229`
- `claude-3-haiku-20240307`

### HuggingFace
- Any model available on HuggingFace (inference API required)

## Environment Setup

### 1. Install Dependencies

```bash
pip install \
  pandas \
  numpy \
  openai \
  google-generativeai \
  anthropic \
  huggingface-hub \
  datasets \
  rouge-score \
  bertscore
```

### 2. Get API Keys

| Provider | Get Key | Free Tier |
|----------|---------|-----------|
| **OpenAI** | https://platform.openai.com/api-keys | $5 credit |
| **Google Gemini** | https://aistudio.google.com/app/apikey | ✓ Yes |
| **Anthropic Claude** | https://console.anthropic.com/ | Limited |
| **HuggingFace** | https://huggingface.co/settings/tokens | Free models |

### 3. Create `.env` File

In `notebook-lm-clone/`:

```env
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIzaSyD...
ANTHROPIC_API_KEY=sk-ant-...
HUGGINGFACE_API_KEY=hf_...
```

### 4. Clone Dataset

```bash
git clone https://github.com/umass-ml4ed/SyllabusQA.git syllabusqa-data
```

## Running Benchmarks

### Run Sample Test (50 questions)

```bash
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --config evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv \
  --sample-size 50
```

Estimated cost: $1-3 (depends on models)

### Run Full Benchmark (~1,000 questions)

```bash
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --config evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv
```

Estimated cost: $30-60 (depends on models)

### Test Specific Models

```bash
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --config evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv \
  --models gpt-4o-mini gemini-2.0-flash claude-3-5-sonnet
```

### Test Different Modes

Edit `syllabusqa_config.json`:

```json
"modes": ["zero_shot", "rag", "rag_cot"]
```

- **zero_shot**: Direct question answering
- **rag**: Question + retrieved context
- **rag_cot**: RAG + chain-of-thought prompting

## Analysis & Reports

### Generate Analysis Report

```bash
python evaluation/comparison_analysis.py \
  --results outputs/syllabusqa_results/raw_results_*.jsonl
```

Creates:
- `ANALYSIS_REPORT.md` - Comprehensive findings
- `model_comparison.csv` - Model performance metrics
- `provider_comparison.csv` - Provider comparison
- `mode_comparison.csv` - Prompting mode analysis
- `model_mode_matrix.csv` - Performance matrix
- `evaluated_results.csv` - Detailed per-result metrics

### View Results

Open in Excel or Python:

```python
import pandas as pd

# All results with computed metrics
results = pd.read_csv("outputs/syllabusqa_results/evaluated_results.csv")

# Model comparison
comparison = pd.read_csv("outputs/syllabusqa_results/model_comparison.csv")
print(comparison.to_string())

# By provider
providers = pd.read_csv("outputs/syllabusqa_results/provider_comparison.csv")

# By mode
modes = pd.read_csv("outputs/syllabusqa_results/mode_comparison.csv")
```

## Metrics Explained

### Token F1
- Token-level precision and recall
- 0 = completely different, 1 = identical
- Best for overall answer quality

### Word Overlap (Jaccard)
- Set similarity of words
- 0 = no shared words, 1 = identical words
- Sensitive to word choice but not order

### BERTScore
- Semantic similarity using embeddings
- Captures meaning beyond word overlap
- More robust to paraphrasing

### ROUGE
- Recall-Oriented Understudy for Gisting Evaluation
- ROUGE-1: Unigram overlap
- ROUGE-L: Longest common subsequence
- Standard for summarization evaluation

### Exact Match
- Binary: did prediction exactly match reference
- Strict but informative about perfect predictions

## Comparison Examples

### Which model performs best?

```python
import pandas as pd

results = pd.read_csv("outputs/syllabusqa_results/model_comparison.csv")
results['token_f1_mean'] = results['token_f1_mean'].astype(float)
best = results.nlargest(1, 'token_f1_mean')
print(best)
```

### Does RAG help?

```python
modes = pd.read_csv("outputs/syllabusqa_results/mode_comparison.csv")
zero_shot = modes[modes['mode'] == 'zero_shot']['token_f1_mean'].values[0]
rag = modes[modes['mode'] == 'rag']['token_f1_mean'].values[0]
print(f"Improvement with RAG: {(rag - zero_shot) * 100:.1f}%")
```

### Provider comparison

```python
providers = pd.read_csv("outputs/syllabusqa_results/provider_comparison.csv")
print(providers.sort_values('token_f1_mean', ascending=False))
```

## Advanced Usage

### Custom Prompts

Modify `syllabusqa_benchmark.py` `_build_prompt()` method:

```python
elif mode == "your_custom_mode":
    return f"""Your custom prompt structure here
    Context: {context}
    Question: {question}
    """
```

### Add New Models

Edit `syllabusqa_config.json`:

```json
{
  "name": "Your Model",
  "provider": "openai",
  "model": "model-id",
  "temperature": 0.1,
  "max_tokens": 1000
}
```

### Batch Processing

Test across different datasets:

```bash
# Test on validation set
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --dataset syllabusqa-data/data/dataset_split/val.csv

# Test on training set (slower but more comprehensive)
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --dataset syllabusqa-data/data/dataset_split/train.csv
```

### Parallel Execution

Run multiple model configurations simultaneously:

```bash
# Terminal 1: OpenAI models
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --config evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv \
  --models gpt-4-turbo gpt-4o gpt-4o-mini &

# Terminal 2: Gemini models
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --config evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv \
  --models gemini-2.0-flash gemini-1.5-pro &

# Terminal 3: Claude models
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --config evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv \
  --models claude-3-5-sonnet claude-3-opus &

wait
```

## Troubleshooting

### API Rate Limits
```python
# Add retry logic
import time
for attempt in range(3):
    try:
        response = provider.generate(prompt)
        break
    except Exception as e:
        if attempt < 2:
            time.sleep(2 ** attempt)  # Exponential backoff
        else:
            raise
```

### Out of Memory
```bash
# Reduce sample size
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --sample-size 100  # Start small
```

### Missing Dependencies
```bash
pip install -r requirements.txt  # If available
# Or install individually
pip install pandas numpy openai google-generativeai anthropic
```

### API Key Issues
```bash
# Verify keys are loaded
python -c "import os; print({k: v[:10]+'...' for k, v in os.environ.items() if 'API' in k})"

# Or check .env file exists
cat notebook-lm-clone/.env
```

## Cost Estimation

Rough costs for full benchmark (1,000 questions × 5 models × 3 modes):

| Provider | Model | Cost |
|----------|-------|------|
| OpenAI | gpt-4-turbo | ~$60 |
| OpenAI | gpt-4o | ~$30 |
| OpenAI | gpt-4o-mini | ~$3 |
| Google | Gemini 2.0 | ~$5 |
| Anthropic | Claude 3.5 Sonnet | ~$60 |
| Anthropic | Claude 3 Opus | ~$150 |

**Total estimate**: $30-60 for minimal benchmark, $300-600 for comprehensive

## Tips for Cost Optimization

1. **Start small**: Test with sample_size=50 first
2. **Use cheaper models**: Start with gpt-4o-mini, gemini-2.0-flash
3. **Test one mode**: Start with "zero_shot" only
4. **Batch process**: Combine requests when possible
5. **Cache results**: Save intermediate results, restart if needed

## Citation

If you use this framework or the SyllabusQA dataset, please cite:

```bibtex
@inproceedings{fernandez-etal-2024-syllabusqa,
    title = "{S}yllabus{QA}: A Course Logistics Question Answering Dataset",
    author = "Fernandez, Nigel and Scarlatos, Alexander and Lan, Andrew",
    booktitle = "Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics",
    year = "2024",
}
```

## Support

- **Issues**: Check SYLLABUSQA_TESTING_GUIDE.md
- **Models**: See supported models list above
- **Dataset**: https://github.com/umass-ml4ed/SyllabusQA
- **Original Paper**: https://arxiv.org/pdf/2403.14666

---

**Last updated**: April 2026
