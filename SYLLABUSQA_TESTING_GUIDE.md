# SyllabusQA Testing Framework for Academic Compass

## Overview
This guide integrates the SyllabusQA dataset into your Academic Compass project to compare performance across multiple LLM providers: OpenAI (GPT), Google (Gemini), and Anthropic (Claude).

## Dataset Information
- **Source**: https://github.com/umass-ml4ed/SyllabusQA
- **Domain**: Course logistics questions (syllabus content)
- **Paper**: "SyllabusQA: A Course Logistics Question Answering Dataset" (ACL 2024)
- **Dataset Size**: ~1k+ QA pairs from multiple syllabi
- **Evaluation Metrics**: BERTScore, ROUGE, Fact-QA

## Project Setup

### 1. Clone and Prepare SyllabusQA Dataset

```bash
cd c:\Projects\academic-compass
git clone https://github.com/umass-ml4ed/SyllabusQA syllabusqa-data
cd syllabusqa-data
```

Structure:
```
syllabusqa-data/
├── data/
│   └── dataset_split/
│       ├── train.csv
│       ├── val.csv
│       └── test.csv
├── syllabi/       # Raw syllabus PDFs
└── code/          # Original evaluation code
```

### 2. Environment Setup

**Backend Dependencies** (notebook-lm-clone/.env):
```env
# Existing keys
GEMINI_API_KEY=your_gemini_key

# Add for testing
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key
HUGGINGFACE_API_KEY=your_hf_token
```

**Install Additional Packages**:
```bash
python -m pip install anthropic huggingface-hub evaluate rouge-score bertscore
```

## Model Providers

### Supported Models

| Provider | Model ID | Notes |
|----------|----------|-------|
| OpenAI | gpt-4-turbo, gpt-4o, gpt-4o-mini | Via OpenAI API |
| Google | gemini-2.0-flash, gemini-1.5-pro | Via Google API (already supported) |
| Anthropic | claude-3-5-sonnet, claude-3-opus, claude-3-haiku | Via Anthropic API |
| HuggingFace | meta-llama/Llama-2-7b-chat-hf, mistralai/Mistral-7B-Instruct-v0.2 | Local or via Inference API |

## Testing Architecture

### File Structure
```
notebook-lm-clone/
├── evaluation/
│   ├── benchmarks/
│   │   ├── syllabusqa_benchmark.py     # SyllabusQA-specific benchmark
│   │   ├── model_providers.py          # Multi-provider wrapper
│   │   └── syllabusqa_config.json      # SyllabusQA test config
│   ├── metrics/
│   │   ├── syllabusqa_metrics.py       # Fact-QA, BERTScore, ROUGE
│   │   └── comparison_metrics.py       # Cross-model comparison
│   └── comparison_reports/             # Generated comparison reports
└── outputs/
    └── syllabusqa_results/
        ├── per_model_results.json
        ├── comparison_summary.csv
        └── visualization_data.json
```

## Implementation Steps

### Step 1: Create Unified Model Provider
File: `notebook-lm-clone/evaluation/benchmarks/model_providers.py`

```python
from typing import Optional, Dict, Any
from dataclasses import dataclass
import os

@dataclass
class ModelConfig:
    provider: str  # "openai", "gemini", "anthropic", "huggingface"
    model_id: str
    temperature: float = 0.1
    max_tokens: int = 1000
    api_key: Optional[str] = None

class UnifiedLLMProvider:
    def __init__(self, config: ModelConfig):
        self.config = config
        self._initialize_client()
    
    def _initialize_client(self):
        if self.config.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.config.provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.client = genai.GenerativeModel(self.config.model_id)
        elif self.config.provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        elif self.config.provider == "huggingface":
            from huggingface_hub import InferenceClient
            self.client = InferenceClient(
                model=self.config.model_id,
                token=os.getenv("HUGGINGFACE_API_KEY")
            )
    
    def generate(self, prompt: str) -> str:
        if self.config.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.config.model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            return response.choices[0].message.content
        
        elif self.config.provider == "gemini":
            response = self.client.generate_content(prompt)
            return response.text
        
        elif self.config.provider == "anthropic":
            response = self.client.messages.create(
                model=self.config.model_id,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        
        elif self.config.provider == "huggingface":
            response = self.client.text_generation(
                prompt,
                max_new_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            return response
```

### Step 2: SyllabusQA Benchmark Runner
File: `notebook-lm-clone/evaluation/benchmarks/syllabusqa_benchmark.py`

```python
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from model_providers import ModelConfig, UnifiedLLMProvider

class SyllabusQABenchmark:
    def __init__(self, dataset_path: str, output_dir: str = "outputs/syllabusqa_results"):
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
    
    def load_dataset(self, split: str = "test") -> List[Dict[str, Any]]:
        """Load SyllabusQA dataset from CSV"""
        csv_path = self.dataset_path / f"{split}.csv"
        df = pd.read_csv(csv_path)
        return df.to_dict('records')
    
    def run_benchmark(self, models: List[ModelConfig], modes: List[str] = None):
        """Run benchmark across multiple models and modes"""
        if modes is None:
            modes = ["zero_shot", "rag", "rag_cot"]
        
        dataset = self.load_dataset("test")
        
        for model_config in models:
            provider = UnifiedLLMProvider(model_config)
            model_results = self._test_model(provider, model_config, dataset, modes)
            self.results.extend(model_results)
            print(f"✓ Completed {model_config.model_id}")
    
    def _test_model(self, provider, config, dataset, modes) -> List[Dict]:
        """Test single model across dataset"""
        results = []
        for idx, item in enumerate(dataset):
            for mode in modes:
                prompt = self._build_prompt(item, mode)
                try:
                    response = provider.generate(prompt)
                    result = {
                        "model": config.model_id,
                        "provider": config.provider,
                        "mode": mode,
                        "question_id": item.get("id"),
                        "question": item.get("question"),
                        "ground_truth": item.get("answer"),
                        "prediction": response,
                        "expected_sources": item.get("sources", [])
                    }
                    results.append(result)
                except Exception as e:
                    print(f"Error for {config.model_id}: {e}")
        return results
    
    def _build_prompt(self, item: Dict, mode: str) -> str:
        """Build prompt based on mode"""
        question = item["question"]
        
        if mode == "zero_shot":
            return f"Answer this question: {question}"
        elif mode == "rag":
            context = item.get("context", "")
            return f"Context: {context}\n\nQuestion: {question}"
        elif mode == "rag_cot":
            context = item.get("context", "")
            return f"""Context: {context}

Question: {question}

Think through this step-by-step:
1. What information in the context is relevant?
2. What key details answer the question?
3. Provide a complete answer."""
    
    def save_results(self):
        """Save results to multiple formats"""
        # JSON format
        with open(self.output_dir / "raw_results.jsonl", "w") as f:
            for r in self.results:
                f.write(json.dumps(r) + "\n")
        
        # CSV format
        df = pd.DataFrame(self.results)
        df.to_csv(self.output_dir / "per_result.csv", index=False)
        print(f"Results saved to {self.output_dir}")
```

### Step 3: Unified Metrics Evaluator
File: `notebook-lm-clone/evaluation/metrics/syllabusqa_metrics.py`

```python
import numpy as np
from typing import List, Dict
from datasets import load_metric
import json

class SyllabusQAMetrics:
    def __init__(self):
        # Load standard metrics
        self.rouge = load_metric('rouge')
        self.bertscore = load_metric('bertscore')
    
    def compute_metrics(self, predictions: List[str], references: List[str]) -> Dict:
        """Compute all metrics for predictions"""
        metrics = {}
        
        # ROUGE scores
        rouge_results = self.rouge.compute(
            predictions=predictions,
            references=references,
            use_stemmer=True
        )
        metrics['rouge1'] = np.mean([r['fmeasure'] for r in rouge_results['rouge1']])
        metrics['rougeL'] = np.mean([r['fmeasure'] for r in rouge_results['rougeL']])
        
        # BERTScore
        bertscore_results = self.bertscore.compute(
            predictions=predictions,
            references=references,
            lang="en"
        )
        metrics['bertscore_f1'] = np.mean(bertscore_results['f1'])
        
        return metrics
    
    def fact_qa_score(self, prediction: str, reference: str, llm_judge=None) -> float:
        """Fact-QA style evaluation using an LLM judge"""
        if not llm_judge:
            return 0.0
        
        prompt = f"""Evaluate if the following prediction correctly answers the question based on the reference answer.
        
Reference: {reference}
Prediction: {prediction}

Rate factuality from 0 to 1 where:
0 = completely wrong/contradicts reference
0.5 = partially correct
1 = completely correct

Score:"""
        
        # Get score from LLM (implementation depends on your judge_model)
        response = llm_judge.generate(prompt)
        try:
            score = float(response.split(':')[-1].strip())
            return min(1.0, max(0.0, score))
        except:
            return 0.0
```

### Step 4: Configuration File
File: `notebook-lm-clone/evaluation/benchmarks/syllabusqa_config.json`

```json
{
  "dataset_path": "syllabusqa-data/data/dataset_split",
  "test_split": "test",
  "output_dir": "outputs/syllabusqa_results",
  "judge_model": {
    "provider": "openai",
    "model": "gpt-4o-mini"
  },
  "models": [
    {
      "name": "GPT-4-Turbo",
      "provider": "openai",
      "model": "gpt-4-turbo",
      "temperature": 0.1,
      "max_tokens": 1000
    },
    {
      "name": "GPT-4o-mini",
      "provider": "openai",
      "model": "gpt-4o-mini",
      "temperature": 0.1,
      "max_tokens": 1000
    },
    {
      "name": "Gemini-2.0-Flash",
      "provider": "gemini",
      "model": "gemini-2.0-flash",
      "temperature": 0.1,
      "max_tokens": 1000
    },
    {
      "name": "Claude-3.5-Sonnet",
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "temperature": 0.1,
      "max_tokens": 1000
    },
    {
      "name": "Claude-3-Opus",
      "provider": "anthropic",
      "model": "claude-3-opus-20240229",
      "temperature": 0.1,
      "max_tokens": 1000
    }
  ],
  "modes": ["zero_shot", "rag", "rag_cot"],
  "sample_size": null,
  "random_seed": 42
}
```

## Usage

### Run Full Benchmark
```bash
cd notebook-lm-clone
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --config evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv
```

### Run Specific Models
```bash
python evaluation/benchmarks/syllabusqa_benchmark.py \
  --config evaluation/benchmarks/syllabusqa_config.json \
  --models gpt-4o-mini gemini-2.0-flash claude-3-5-sonnet \
  --sample-size 50
```

## Expected Outputs

### 1. Per-Result CSV
```
model, provider, mode, question_id, question, ground_truth, prediction, rouge1, rougeL, bertscore_f1, factuality
```

### 2. Summary Report
Comparison table showing:
- Average metrics by model
- Performance by mode (zero_shot vs RAG)
- Metric breakdowns

### 3. Visualization Data
JSON for plotting:
- Model vs metric performance
- Mode effectiveness
- Provider comparison

## Metrics Explanation

| Metric | Formula | Interpretation |
|--------|---------|-----------------|
| **ROUGE-1** | Unigram overlap | 0-1, higher is better |
| **ROUGE-L** | Longest common subsequence | 0-1, higher is better |
| **BERTScore** | Contextual embedding similarity | 0-1, higher is better |
| **Factuality** | LLM-judge correctness rating | 0-1, higher is better |
| **Token F1** | Token overlap precision/recall | 0-1, higher is better |
| **Citation Precision** | Relevant sources cited | 0-1, higher is better |

## Cost Estimation

Rough API call costs (varies by provider):
```
Dataset: ~1,000 test samples
Models: 5 (GPT-4, GPT-4o-mini, Gemini, Claude-Sonnet, Claude-Opus)
Modes: 3 (zero_shot, rag, rag_cot)

Total calls: 1,000 × 5 × 3 = 15,000 calls

OpenAI: ~$150-300 (depending on model)
Gemini: ~$30-50 (free tier available)
Anthropic: ~$100-200
Judgment calls (GPT-4o-mini): ~$30-50

Total estimate: $310-600
```

## Advanced Options

### 1. A/B Testing
Compare your system output vs models on same questions

### 2. Error Analysis
Categorize failures: factual errors, hallucinations, out-of-context responses

### 3. Few-Shot Prompting
Add examples to prompts to improve performance

### 4. Retrieval Optimization
Test different chunking strategies, retrieval sizes (top-k)

## Troubleshooting

**Q: API Rate Limits**
A: Add retry logic with exponential backoff, batch requests

**Q: Out of Memory for BERTScore**
A: Use smaller batch sizes, compute per-sample metrics

**Q: Model API Unavailable**
A: Implement fallback models, save partially completed results

## Next Steps

1. ✅ Set up environment and install dependencies
2. ✅ Clone SyllabusQA dataset
3. ✅ Configure model credentials
4. ✅ Run initial benchmark on small sample (50 questions)
5. ✅ Review baseline metrics
6. ✅ Run full dataset comparison
7. ✅ Generate comparison report
8. ✅ Analyze results and identify improvements

---

**References**:
- SyllabusQA Paper: https://arxiv.org/pdf/2403.14666
- ROUGE: https://github.com/google-research/google-research/tree/master/rouge
- BERTScore: https://github.com/Tiiiger/bert_score
