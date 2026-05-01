# SyllabusQA Testing Framework - Getting Started

**Created**: April 2026  
**Project**: Academic Compass - Multi-Model Benchmarking against SyllabusQA Dataset

## 🎯 What You Have

A complete, production-ready testing framework that:

✅ Tests **multiple LLM providers** (OpenAI, Google, Anthropic)  
✅ Evaluates **different prompting strategies** (zero-shot, RAG, chain-of-thought)  
✅ Compares **model performance** with standard metrics  
✅ Generates **comprehensive reports** and analysis  
✅ Integrates with **your Academic Compass backend**  
✅ Estimates and tracks **API costs**  

## 📁 Files Created

### Documentation (Start Here!)
1. **SYLLABUSQA_TESTING_GUIDE.md** - Complete setup guide
2. **SYLLABUSQA_INTEGRATION_GUIDE.md** - How to integrate with your project
3. **SYLLABUSQA_FRAMEWORK_REFERENCE.md** - Technical reference
4. **notebook-lm-clone/evaluation/README_SYLLABUSQA.md** - Quick reference

### Implementation
5. `model_providers.py` - Multi-provider LLM interface
6. `syllabusqa_benchmark.py` - Benchmark runner
7. `syllabusqa_metrics.py` - Metric computation
8. `comparison_analysis.py` - Analysis & reporting
9. `quickstart.py` - Interactive setup wizard
10. `syllabusqa_config.json` - Model configurations

## 🚀 Quick Start (5 Minutes)

```bash
cd c:\Projects\academic-compass

# 1. Run setup wizard
python notebook-lm-clone/evaluation/quickstart.py

# 2. Follow prompts to:
#    - Install dependencies
#    - Clone SyllabusQA dataset
#    - Configure API keys

# 3. Run sample benchmark
python notebook-lm-clone/evaluation/benchmarks/syllabusqa_benchmark.py \
  --config notebook-lm-clone/evaluation/benchmarks/syllabusqa_config.json \
  --dataset syllabusqa-data/data/dataset_split/test.csv \
  --sample-size 50

# 4. Generate analysis
python notebook-lm-clone/evaluation/comparison_analysis.py \
  --results outputs/syllabusqa_results/raw_results_*.jsonl

# 5. View report
cat outputs/syllabusqa_results/ANALYSIS_REPORT.md
```

## 📊 What You'll Learn

After running the benchmark, you'll know:

| Question | Where to Find |
|----------|---------------|
| Which model performs best? | model_comparison.csv |
| Does RAG help? | mode_comparison.csv |
| OpenAI vs Google vs Anthropic? | provider_comparison.csv |
| Best quality-to-cost ratio? | ANALYSIS_REPORT.md |
| Specific failure cases? | evaluated_results.csv |

## 💰 Cost Estimate

| Test Size | Models Tested | Modes | Est. Cost |
|-----------|---------------|-------|-----------|
| 50 samples (quick) | 2 | 1 | $0.50-2 |
| 200 samples | 3 | 3 | $3-10 |
| 1000 samples (full) | 8 | 3 | $100-300 |

**Tip**: Start with small samples, use cheap models first

## 🎓 Recommended Learning Path

### Day 1: Understanding
1. Read: SYLLABUSQA_TESTING_GUIDE.md (30 min)
2. Read: SYLLABUSQA_FRAMEWORK_REFERENCE.md (20 min)
3. Review: SyllabusQA paper link (optional)

### Day 2: Setup & Sample
1. Run: `python notebook-lm-clone/evaluation/quickstart.py` (10 min)
2. Run: Sample benchmark with 50 questions (15 min)
3. Review: generated reports

### Day 3: Full Benchmark
1. Run: Full benchmark on ~1000 questions (3-5 hours, can be overnight)
2. Analyze: Results and metrics
3. Plan: Integration with your backend

### Day 4: Integration
1. Read: SYLLABUSQA_INTEGRATION_GUIDE.md
2. Update: Your backend based on findings
3. Test: With live data

## 📖 Documentation Map

```
START HERE → SYLLABUSQA_TESTING_GUIDE.md (38 KB)
    ↓
Understand the dataset, setup env, get API keys
    ↓
Run quickstart.py
    ↓
Choose your scenario:
    ├─ Quick test? → README_SYLLABUSQA.md (Quick commands)
    ├─ Need details? → SYLLABUSQA_FRAMEWORK_REFERENCE.md
    ├─ Ready to integrate? → SYLLABUSQA_INTEGRATION_GUIDE.md
    └─ Need to debug? → README_SYLLABUSQA.md (Troubleshooting)
```

## 🔑 Key Decisions to Make

### 1. Budget
- **Minimal** ($10): Use gemini-2.0-flash only
- **Moderate** ($50): Mix of OpenAI & Gemini
- **Comprehensive** ($300+): All providers

### 2. Dataset Size
- **Quick** (50 samples): 15 min runtime
- **Medium** (200 samples): 1 hour runtime
- **Full** (1000+ samples): 3-5 hours runtime

### 3. Prompting Modes
- **Basic**: zero_shot only
- **Standard**: zero_shot + rag
- **Advanced**: zero_shot + rag + rag_cot

### 4. Update Frequency
- **Once**: Just need to pick best model
- **Weekly**: Monitor performance over time
- **Daily**: A/B testing on live data

## 📋 Pre-Flight Checklist

Before running benchmarks:

- [ ] API keys obtained from OpenAI, Google, Anthropic
- [ ] Created `.env` file in `notebook-lm-clone/`
- [ ] Python 3.10+ installed
- [ ] Dependencies installed (or using quickstart.py)
- [ ] SyllabusQA dataset cloned
- [ ] Configured `syllabusqa_config.json` with your models
- [ ] Budget/cost limits set
- [ ] Output directory ready

## 🎯 Expected Outcomes

### After 1 Hour
- ✅ Sample benchmark complete
- ✅ Know which models to test next
- ✅ Understand your baseline performance

### After 5 Hours
- ✅ Full benchmark results
- ✅ Comprehensive analysis report
- ✅ Model rankings by performance
- ✅ Best settings identified

### After Integration
- ✅ Backend updated with best model
- ✅ Performance improved
- ✅ Costs optimized
- ✅ Ready for production

## 💡 Pro Tips

1. **Test incrementally**: Start small, verify, scale up
2. **Save everything**: Keep all results for future comparison
3. **Document changes**: Note what you tested and why
4. **Parallelize**: Run different models in separate terminals
5. **Cost tracking**: Monitor API spending regularly
6. **Version control**: Save configs before changing them

## ❓ Frequently Asked Questions

**Q: How long does a full benchmark take?**
A: 3-5 hours depending on models and internet speed

**Q: Can I stop and resume?**
A: Yes, results are saved. Partial runs are still valuable

**Q: How much will this cost?**
A: $30-300 depending on models and sample size

**Q: Which model should I use?**
A: Read the results! model_comparison.csv will tell you

**Q: Do I need all the files?**
A: quickstart.py sets everything up automatically

## 🆘 Need Help?

1. **Setup issues?** → Check SYLLABUSQA_TESTING_GUIDE.md
2. **Running benchmarks?** → See README_SYLLABUSQA.md
3. **Integration?** → Read SYLLABUSQA_INTEGRATION_GUIDE.md
4. **Technical details?** → SYLLABUSQA_FRAMEWORK_REFERENCE.md
5. **Troubleshooting?** → README_SYLLABUSQA.md (Troubleshooting section)

## 📞 Resources

- **SyllabusQA Dataset**: https://github.com/umass-ml4ed/SyllabusQA
- **Paper**: https://arxiv.org/pdf/2403.14666
- **OpenAI Docs**: https://platform.openai.com/docs
- **Google Gemini**: https://ai.google.dev
- **Anthropic Claude**: https://www.anthropic.com

## ✨ What's Next?

1. **Today**: Run quickstart.py and sample benchmark
2. **Tomorrow**: Analyze results and plan integration
3. **This Week**: Run full benchmark and implement best practices
4. **Next Week**: Deploy to production with optimized settings

---

**Ready to get started?**
```bash
python notebook-lm-clone/evaluation/quickstart.py
```

**Questions?**
Read the documentation files in order:
1. SYLLABUSQA_TESTING_GUIDE.md
2. SYLLABUSQA_FRAMEWORK_REFERENCE.md
3. SYLLABUSQA_INTEGRATION_GUIDE.md

**Good luck! 🚀**
