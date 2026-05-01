"""
SyllabusQA Metrics Evaluator
Computes ROUGE, BERTScore, Factuality, and other metrics
"""

import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyllabusQAMetrics:
    """
    Evaluates benchmark results using multiple metrics:
    - ROUGE (ROUGE-1, ROUGE-L)
    - BERTScore
    - Token-level F1
    - Semantic similarity
    """
    
    def __init__(self):
        self.metrics_computed = {}
        self._load_metrics()
    
    def _load_metrics(self):
        """Load metric libraries"""
        try:
            from datasets import load_metric
            self.rouge = load_metric("rouge")
            logger.info("✓ Loaded ROUGE metric")
        except ImportError:
            logger.warning("ROUGE not available, install: pip install rouge-score")
            self.rouge = None
        
        try:
            from datasets import load_metric
            self.bertscore = load_metric("bertscore")
            logger.info("✓ Loaded BERTScore metric")
        except ImportError:
            logger.warning("BERTScore not available, install: pip install bertscore")
            self.bertscore = None
    
    def compute_all_metrics(self, predictions: List[str], references: List[str]) -> Dict[str, float]:
        """
        Compute all available metrics for predictions vs references
        """
        if not predictions or not references:
            return {}
        
        metrics = {}
        
        # ROUGE scores
        if self.rouge:
            try:
                rouge_results = self.rouge.compute(
                    predictions=predictions,
                    references=references,
                    use_stemmer=True
                )
                metrics['rouge1_f1'] = np.mean([r['fmeasure'] for r in rouge_results.get('rouge1', [])])
                metrics['rougeL_f1'] = np.mean([r['fmeasure'] for r in rouge_results.get('rougeL', [])])
                logger.info("✓ Computed ROUGE metrics")
            except Exception as e:
                logger.warning(f"ROUGE computation failed: {e}")
        
        # BERTScore
        if self.bertscore:
            try:
                bertscore_results = self.bertscore.compute(
                    predictions=predictions,
                    references=references,
                    lang="en"
                )
                metrics['bertscore_precision'] = np.mean(bertscore_results['precision'])
                metrics['bertscore_recall'] = np.mean(bertscore_results['recall'])
                metrics['bertscore_f1'] = np.mean(bertscore_results['f1'])
                logger.info("✓ Computed BERTScore metrics")
            except Exception as e:
                logger.warning(f"BERTScore computation failed: {e}")
        
        # Token-level metrics
        token_f1_scores = [self.token_f1(pred, ref) for pred, ref in zip(predictions, references)]
        metrics['token_f1'] = np.mean(token_f1_scores)
        
        # Length ratio
        pred_lens = [len(p.split()) for p in predictions]
        ref_lens = [len(r.split()) for r in references]
        metrics['avg_prediction_length'] = np.mean(pred_lens)
        metrics['avg_reference_length'] = np.mean(ref_lens)
        metrics['length_ratio'] = np.mean([p/r if r > 0 else 0 for p, r in zip(pred_lens, ref_lens)])
        
        return metrics
    
    def compute_per_sample_metrics(self, prediction: str, reference: str) -> Dict[str, float]:
        """
        Compute metrics for a single prediction-reference pair
        """
        metrics = {}
        
        # Token F1
        metrics['token_f1'] = self.token_f1(prediction, reference)
        
        # Length metrics
        pred_tokens = len(prediction.split())
        ref_tokens = len(reference.split())
        metrics['pred_length'] = pred_tokens
        metrics['ref_length'] = ref_tokens
        metrics['length_ratio'] = pred_tokens / ref_tokens if ref_tokens > 0 else 0
        
        # BLEU-like overlap
        metrics['word_overlap'] = self.word_overlap(prediction, reference)
        
        # Exact match
        metrics['exact_match'] = 1.0 if prediction.strip() == reference.strip() else 0.0
        
        return metrics
    
    @staticmethod
    def token_f1(prediction: str, reference: str) -> float:
        """
        Compute F1 score based on token overlap
        """
        from collections import defaultdict
        
        def normalize_text(text: str) -> str:
            import re
            text = text.lower().strip()
            text = re.sub(r'[^a-z0-9\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        
        def tokenize(text: str) -> List[str]:
            if not text:
                return []
            return normalize_text(text).split()
        
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
    
    @staticmethod
    def word_overlap(prediction: str, reference: str) -> float:
        """
        Compute word-level overlap (Jaccard similarity)
        """
        pred_words = set(prediction.lower().split())
        ref_words = set(reference.lower().split())
        
        intersection = len(pred_words & ref_words)
        union = len(pred_words | ref_words)
        
        return intersection / union if union > 0 else 0.0


class MetricsComparator:
    """
    Compare metrics across different models and modes
    """
    
    def __init__(self, results_df: pd.DataFrame):
        self.df = results_df
        self.metrics_evaluator = SyllabusQAMetrics()
    
    def evaluate_results(self) -> pd.DataFrame:
        """
        Compute metrics for all results
        """
        logger.info("Computing metrics for all results...")
        
        results_with_metrics = []
        
        for idx, row in self.df.iterrows():
            if idx % 10 == 0:
                logger.info(f"Processed {idx}/{len(self.df)} results")
            
            metrics = self.metrics_evaluator.compute_per_sample_metrics(
                row['prediction'],
                row['ground_truth']
            )
            
            result_dict = row.to_dict()
            result_dict.update(metrics)
            results_with_metrics.append(result_dict)
        
        return pd.DataFrame(results_with_metrics)
    
    def get_model_comparison(self, metric: str = "token_f1") -> pd.DataFrame:
        """
        Get performance comparison across models
        """
        if metric not in self.df.columns:
            logger.warning(f"Metric {metric} not found in results")
            return pd.DataFrame()
        
        comparison = self.df.groupby(['model_name', 'mode']).agg({
            metric: ['mean', 'std', 'min', 'max', 'count']
        }).round(4)
        
        return comparison
    
    def get_mode_comparison(self, metric: str = "token_f1") -> pd.DataFrame:
        """
        Compare prompting modes (zero_shot vs rag)
        """
        if metric not in self.df.columns:
            logger.warning(f"Metric {metric} not found in results")
            return pd.DataFrame()
        
        comparison = self.df.groupby('mode').agg({
            metric: ['mean', 'std', 'min', 'max', 'count']
        }).round(4)
        
        return comparison
    
    def get_provider_comparison(self, metric: str = "token_f1") -> pd.DataFrame:
        """
        Compare across providers (OpenAI, Gemini, Anthropic)
        """
        if metric not in self.df.columns:
            logger.warning(f"Metric {metric} not found in results")
            return pd.DataFrame()
        
        comparison = self.df.groupby('provider').agg({
            metric: ['mean', 'std', 'min', 'max', 'count']
        }).round(4)
        
        return comparison
    
    def save_comparison_report(self, output_path: str):
        """
        Generate and save comprehensive comparison report
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            f.write("# SyllabusQA Benchmark Comparison Report\n\n")
            f.write(f"Generated: {pd.Timestamp.now()}\n\n")
            
            # Model comparison
            f.write("## Model Performance Comparison (Token F1)\n\n")
            model_comp = self.get_model_comparison("token_f1")
            if not model_comp.empty:
                f.write(model_comp.to_string())
                f.write("\n\n")
            
            # Mode comparison
            f.write("## Prompting Mode Comparison\n\n")
            mode_comp = self.get_mode_comparison("token_f1")
            if not mode_comp.empty:
                f.write(mode_comp.to_string())
                f.write("\n\n")
            
            # Provider comparison
            f.write("## Provider Comparison\n\n")
            provider_comp = self.get_provider_comparison("token_f1")
            if not provider_comp.empty:
                f.write(provider_comp.to_string())
                f.write("\n\n")
        
        logger.info(f"✓ Saved comparison report to {output_path}")


def load_results(results_path: str) -> pd.DataFrame:
    """Load benchmark results from JSONL or CSV"""
    path = Path(results_path)
    
    if path.suffix == ".jsonl":
        data = []
        with open(path, "r") as f:
            for line in f:
                data.append(json.loads(line))
        return pd.DataFrame(data)
    
    elif path.suffix == ".csv":
        return pd.read_csv(path)
    
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python syllabusqa_metrics.py <results_file>")
        sys.exit(1)
    
    results = load_results(sys.argv[1])
    logger.info(f"Loaded {len(results)} results")
    
    comparator = MetricsComparator(results)
    evaluated = comparator.evaluate_results()
    
    # Save evaluated results
    output_path = Path(sys.argv[1]).parent / "evaluated_results.csv"
    evaluated.to_csv(output_path, index=False)
    logger.info(f"✓ Saved evaluated results to {output_path}")
    
    # Generate report
    report_path = Path(sys.argv[1]).parent / "comparison_report.md"
    comparator.save_comparison_report(str(report_path))
