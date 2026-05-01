# SyllabusQA Framework - Architecture & Files Summary

Complete reference of all files created for SyllabusQA testing framework.

## 📁 File Structure

```
c:\Projects\academic-compass\
├── SYLLABUSQA_TESTING_GUIDE.md              # Comprehensive setup guide
├── SYLLABUSQA_INTEGRATION_GUIDE.md          # Integration with your project
├── notebook-lm-clone/evaluation/
│   ├── README_SYLLABUSQA.md                 # Benchmark README
│   ├── quickstart.py                        # Interactive setup wizard
│   ├── comparison_analysis.py               # Analysis & reporting
│   ├── benchmarks/
│   │   ├── __init__.py                      # Python module init
│   │   ├── model_providers.py               # Multi-provider LLM wrapper
│   │   ├── syllabusqa_benchmark.py          # Main benchmark runner
│   │   └── syllabusqa_config.json           # Model configurations
│   └── metrics/
│       └── syllabusqa_metrics.py            # Metric computation
│
└── outputs/syllabusqa_results/              # Generated during benchmark
    ├── raw_results_YYYYMMDD_HHMMSS.jsonl   # Raw benchmark output
    ├── results_YYYYMMDD_HHMMSS.csv         # CSV copy of results
    ├── evaluated_results.csv                # Results with computed metrics
    ├── model_comparison.csv                 # Model performance
    ├── provider_comparison.csv              # Provider comparison
    ├── mode_comparison.csv                  # Prompting mode comparison
    ├── model_mode_matrix.csv                # Performance matrix
    ├── ANALYSIS_REPORT.md                   # Full analysis
    └── analysis_summary.json                # Summary statistics
```

## 📄 File Reference

### Documentation Files

#### 1. **SYLLABUSQA_TESTING_GUIDE.md**
- **Purpose**: Comprehensive setup and usage guide
- **Contents**: 
  - Overview of SyllabusQA dataset
  - Installation steps
  - Model provider details
  - Step-by-step implementation
  - Metrics explanation
  - Cost estimation
- **When to read**: Starting out, need full details

#### 2. **SYLLABUSQA_INTEGRATION_GUIDE.md**
- **Purpose**: Integrate testing with your Academic Compass project
- **Contents**:
  - Integration steps
  - Test scenarios
  - Optimization recommendations
  - Backend integration patterns
  - Decision trees by scenario
- **When to read**: Ready to integrate into your system

#### 3. **notebook-lm-clone/evaluation/README_SYLLABUSQA.md**
- **Purpose**: Quick reference for running benchmarks
- **Contents**:
  - Quick start (2 minutes)
  - Supported models
  - Benchmark commands
  - Analysis examples
  - Cost optimization
  - Troubleshooting
- **When to read**: During benchmark execution

### Implementation Files

#### 4. **model_providers.py**
- **Purpose**: Unified interface for multiple LLM providers
- **Key Classes**:
  - `ModelConfig`: Configuration dataclass
  - `UnifiedLLMProvider`: Main provider interface
- **Features**:
  - Supports OpenAI, Gemini, Anthropic, HuggingFace
  - Automatic client initialization
  - Batch generation support
  - Error handling & logging
- **Usage**:
  ```python
  from model_providers import ModelConfig, UnifiedLLMProvider
  
  config = ModelConfig(
      provider="openai",
      model_id="gpt-4o-mini",
      name="GPT-4o-mini"
  )
  provider = UnifiedLLMProvider(config)
  response = provider.generate("Your prompt here")
  ```

#### 5. **syllabusqa_benchmark.py**
- **Purpose**: Run benchmarks across models and datasets
- **Key Classes**:
  - `SyllabusQABenchmark`: Main benchmark runner
- **Features**:
  - Load CSV/JSONL datasets
  - Test multiple models across different modes
  - Compute per-sample metrics
  - Generate summaries
  - Multiple output formats (JSONL, CSV, JSON)
- **CLI Arguments**:
  ```
  --config: Config JSON file path (required)
  --dataset: Dataset CSV path (required)
  --output-dir: Output directory
  --sample-size: Number of samples to test
  --models: Specific models to test
  ```

#### 6. **syllabusqa_metrics.py**
- **Purpose**: Compute evaluation metrics
- **Key Classes**:
  - `SyllabusQAMetrics`: Metric computation
  - `MetricsComparator`: Cross-model comparison
- **Features**:
  - Token F1 computation
  - ROUGE scores
  - BERTScore
  - Word overlap (Jaccard)
  - Exact match
  - Per-sample and aggregate metrics
- **Usage**:
  ```python
  from syllabusqa_metrics import SyllabusQAMetrics
  
  metrics_eval = SyllabusQAMetrics()
  scores = metrics_eval.compute_per_sample_metrics(
      prediction="Your answer",
      reference="Expected answer"
  )
  ```

#### 7. **comparison_analysis.py**
- **Purpose**: Analyze and report benchmark results
- **Key Classes**:
  - `BenchmarkAnalyzer`: Comprehensive analysis
- **Features**:
  - Compute evaluation metrics
  - Model/provider/mode comparisons
  - Performance matrices
  - Failure case identification
  - Markdown report generation
  - Multiple output formats
- **CLI Arguments**:
  ```
  --results: Results file path (JSONL or CSV)
  --report-only: Only print report, don't save
  ```

#### 8. **quickstart.py**
- **Purpose**: Interactive setup wizard
- **Features**:
  - Environment validation
  - Dependency installation
  - Dataset downloading
  - API key configuration
  - Sample benchmark execution
  - Step-by-step guidance
- **Usage**:
  ```bash
  python notebook-lm-clone/evaluation/quickstart.py
  ```

### Configuration Files

#### 9. **syllabusqa_config.json**
- **Purpose**: Centralized benchmark configuration
- **Contents**:
  ```json
  {
    "dataset_path": "path/to/dataset",
    "models": [
      {
        "name": "Model Name",
        "provider": "openai|gemini|anthropic|huggingface",
        "model": "model-id",
        "temperature": 0.1,
        "max_tokens": 1000
      }
    ],
    "modes": ["zero_shot", "rag", "rag_cot"],
    "judge_model": {...}
  }
  ```

## 🔄 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SETUP PHASE                              │
│                                                             │
│  1. Run quickstart.py                                      │
│  2. Install dependencies                                   │
│  3. Clone SyllabusQA dataset                              │
│  4. Configure API keys (.env)                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  BENCHMARK PHASE                            │
│                                                             │
│  1. Configure syllabusqa_config.json                       │
│  2. Run syllabusqa_benchmark.py                            │
│  3. Loads dataset & initializes models                     │
│  4. For each model × question × mode:                      │
│     - Generate prompt using _build_prompt()               │
│     - Call UnifiedLLMProvider.generate()                   │
│     - Save prediction                                      │
│  5. Output raw results (JSONL)                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               EVALUATION PHASE                              │
│                                                             │
│  1. Run comparison_analysis.py                             │
│  2. Load raw results                                       │
│  3. Compute metrics using syllabusqa_metrics.py            │
│     - Token F1, word overlap, ROUGE, BERTScore             │
│  4. Generate comparisons:                                   │
│     - By model                                             │
│     - By provider                                          │
│     - By mode                                              │
│  5. Identify top performers & failures                     │
│  6. Generate markdown report                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  ANALYSIS PHASE                             │
│                                                             │
│  1. Read ANALYSIS_REPORT.md                                │
│  2. Review model_comparison.csv                            │
│  3. Check mode_comparison.csv                              │
│  4. Analyze model_mode_matrix.csv                          │
│  5. Identify insights & recommendations                    │
│  6. Make deployment decisions                              │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Quick Command Reference

### Setup
```bash
# Interactive setup
python notebook-lm-clone/evaluation/quickstart.py
```

### Sample Benchmark (50 questions, ~10 min)
```bash
python notebook-lm-clone/evaluation/benchmarks/syllabusqa_benchmark.py \
  --config notebook-lm-clone/evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv \
  --sample-size 50
```

### Full Benchmark (~1,000 questions, ~2-4 hours)
```bash
python notebook-lm-clone/evaluation/benchmarks/syllabusqa_benchmark.py \
  --config notebook-lm-clone/evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv
```

### Analyze Results
```bash
python notebook-lm-clone/evaluation/comparison_analysis.py \
  --results outputs/syllabusqa_results/raw_results_*.jsonl
```

### Test Specific Models
```bash
python notebook-lm-clone/evaluation/benchmarks/syllabusqa_benchmark.py \
  --config notebook-lm-clone/evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv \
  --models gpt-4o-mini gemini-2.0-flash claude-3-5-sonnet
```

## 📊 Output Files Explanation

### Raw Results Format (JSONL)
```json
{
  "timestamp": "2026-04-29T10:30:45",
  "model_name": "GPT-4o-mini",
  "model_id": "gpt-4o-mini",
  "provider": "openai",
  "mode": "zero_shot",
  "question_id": "q1",
  "question": "What is the course name?",
  "ground_truth": "Introduction to Computer Science",
  "prediction": "The course is called Introduction to Computer Science",
  "context": "...",
  "sources": ["syllabus.pdf"]
}
```

### Evaluated Results (CSV)
```
model_name,prediction,ground_truth,token_f1,word_overlap,exact_match
GPT-4o-mini,answer1,reference1,0.85,0.75,0
Gemini-2.0,answer2,reference2,0.92,0.88,1
```

### Model Comparison (CSV)
```
model_name,token_f1_mean,token_f1_std,word_overlap_mean,exact_match_mean
Claude-3.5-Sonnet,0.78,0.12,0.68,0.14
GPT-4o,0.75,0.15,0.65,0.10
```

## 🔧 Extending the Framework

### Add New Model Provider
1. Update `model_providers.py` with new provider
2. Add case in `_initialize_client()`
3. Add case in `generate()` method
4. Add configuration to `syllabusqa_config.json`

### Add New Metric
1. Add method to `SyllabusQAMetrics` class
2. Call in `compute_per_sample_metrics()`
3. Update `comparison_analysis.py` to report it

### Add Custom Prompting Mode
1. Add case in `_build_prompt()` method
2. Add to `"modes"` array in config
3. Run benchmark with new mode

## 📈 Expected Performance

### Quality Metrics (Token F1)
- **Good**: 0.70-0.75
- **Very Good**: 0.75-0.80
- **Excellent**: >0.80

### Mode Impact
- **Zero-shot**: Baseline
- **RAG**: +5-15% improvement
- **RAG + CoT**: +2-5% additional

### Provider Ranking (typical)
1. Claude 3.5 Sonnet: ~0.77
2. GPT-4 Turbo: ~0.76
3. Claude 3 Opus: ~0.76
4. Gemini 2.0 Flash: ~0.72
5. GPT-4o-mini: ~0.70

## 💡 Tips & Best Practices

1. **Start small**: Run 50-question sample first
2. **Use cheap models**: Start with gpt-4o-mini
3. **Test one mode**: Start with zero_shot
4. **Monitor costs**: Check output after each run
5. **Save results**: Don't delete outputs
6. **Document changes**: Track what you've tested
7. **Parallelize**: Run multiple configs simultaneously
8. **Iterate**: Test → analyze → improve → repeat

## 🐛 Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| API key not found | Check .env file in notebook-lm-clone/ |
| Out of memory | Reduce sample_size or batch size |
| Rate limits | Add exponential backoff retry logic |
| Dataset not found | Clone: `git clone https://github.com/umass-ml4ed/SyllabusQA.git syllabusqa-data` |
| Low scores | Check if context quality is good; try RAG mode |
| High costs | Use cheaper models (gpt-4o-mini) or smaller sample |

## 📚 Related Documentation

- **SYLLABUSQA_TESTING_GUIDE.md**: Full setup guide
- **SYLLABUSQA_INTEGRATION_GUIDE.md**: Integration guide
- **notebook-lm-clone/evaluation/README_SYLLABUSQA.md**: Quick reference
- **SyllabusQA Paper**: https://arxiv.org/pdf/2403.14666
- **SyllabusQA Repo**: https://github.com/umass-ml4ed/SyllabusQA

---

**Version**: 1.0  
**Created**: April 2026  
**Last Updated**: April 2026
