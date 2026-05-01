"""
SyllabusQA Benchmark Comparison & Analysis Script
Analyzes and visualizes benchmark results across models
"""

import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BenchmarkAnalyzer:
    """Comprehensive analysis of benchmark results"""
    
    def __init__(self, results_path: str):
        self.results_path = Path(results_path)
        self.df = self._load_results()
        self.output_dir = self.results_path.parent
    
    def _load_results(self) -> pd.DataFrame:
        """Load results from JSONL or CSV"""
        if self.results_path.suffix == ".jsonl":
            data = []
            with open(self.results_path, "r") as f:
                for line in f:
                    data.append(json.loads(line))
            df = pd.DataFrame(data)
        elif self.results_path.suffix == ".csv":
            df = pd.read_csv(self.results_path)
        else:
            raise ValueError(f"Unsupported format: {self.results_path.suffix}")
        
        logger.info(f"✓ Loaded {len(df)} results")
        return df
    
    def compute_evaluation_metrics(self) -> pd.DataFrame:
        """
        Compute token F1, word overlap, and other metrics
        """
        from syllabusqa_metrics import SyllabusQAMetrics
        
        logger.info("Computing evaluation metrics...")
        metrics_eval = SyllabusQAMetrics()
        
        metrics_list = []
        for idx, row in self.df.iterrows():
            if idx % 50 == 0:
                logger.info(f"  [{idx}/{len(self.df)}] Computing metrics")
            
            pred = str(row.get('prediction', ''))
            ref = str(row.get('ground_truth', ''))
            
            metrics = metrics_eval.compute_per_sample_metrics(pred, ref)
            metrics_list.append(metrics)
        
        metrics_df = pd.DataFrame(metrics_list)
        self.df = pd.concat([self.df, metrics_df], axis=1)
        logger.info("✓ Computed metrics")
        return self.df
    
    def generate_model_comparison(self) -> pd.DataFrame:
        """
        Compare performance across models
        """
        logger.info("Generating model comparison...")
        
        comparison = self.df.groupby('model_name').agg({
            'token_f1': ['mean', 'std', 'min', 'max'],
            'word_overlap': ['mean', 'std'],
            'exact_match': 'mean',
            'pred_length': 'mean',
        }).round(4)
        
        comparison.columns = ['_'.join(col).strip() for col in comparison.columns.values]
        return comparison.reset_index()
    
    def generate_provider_comparison(self) -> pd.DataFrame:
        """
        Compare performance across providers (OpenAI, Gemini, Anthropic)
        """
        logger.info("Generating provider comparison...")
        
        comparison = self.df.groupby('provider').agg({
            'token_f1': ['mean', 'std', 'min', 'max', 'count'],
            'word_overlap': 'mean',
            'exact_match': 'mean',
        }).round(4)
        
        comparison.columns = ['_'.join(col).strip() for col in comparison.columns.values]
        return comparison.reset_index()
    
    def generate_mode_comparison(self) -> pd.DataFrame:
        """
        Compare effectiveness of different prompting modes
        """
        logger.info("Generating mode comparison...")
        
        comparison = self.df.groupby('mode').agg({
            'token_f1': ['mean', 'std', 'min', 'max'],
            'word_overlap': 'mean',
            'exact_match': 'mean',
        }).round(4)
        
        comparison.columns = ['_'.join(col).strip() for col in comparison.columns.values]
        return comparison.reset_index()
    
    def generate_model_mode_matrix(self) -> pd.DataFrame:
        """
        Create matrix of model x mode performance
        """
        logger.info("Generating model x mode performance matrix...")
        
        pivot = self.df.pivot_table(
            index='model_name',
            columns='mode',
            values='token_f1',
            aggfunc='mean'
        ).round(4)
        
        return pivot
    
    def identify_best_performers(self, metric: str = 'token_f1', top_k: int = 5) -> List[Dict]:
        """
        Identify top performing configurations
        """
        logger.info(f"Identifying top {top_k} performers by {metric}...")
        
        results = []
        for _, row in self.df.iterrows():
            results.append({
                'model': row['model_name'],
                'provider': row['provider'],
                'mode': row['mode'],
                'question_id': row['question_id'],
                metric: row.get(metric, 0)
            })
        
        results_sorted = sorted(results, key=lambda x: x[metric], reverse=True)
        return results_sorted[:top_k]
    
    def identify_failure_cases(self, metric: str = 'token_f1', threshold: float = 0.1, limit: int = 10) -> pd.DataFrame:
        """
        Identify cases where models performed poorly
        """
        logger.info(f"Identifying failure cases (threshold: {threshold})...")
        
        failures = self.df[self.df[metric] < threshold].copy()
        failures = failures.sort_values(metric).head(limit)
        
        return failures[['model_name', 'provider', 'mode', 'question', 'prediction', 'ground_truth', metric]]
    
    def generate_comprehensive_report(self) -> str:
        """
        Generate comprehensive markdown report
        """
        logger.info("Generating comprehensive report...")
        
        report = f"""# SyllabusQA Benchmark Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

- **Total Results**: {len(self.df)}
- **Models Tested**: {self.df['model_name'].nunique()}
- **Providers**: {', '.join(self.df['provider'].unique())}
- **Modes**: {', '.join(self.df['mode'].unique())}

## Dataset Breakdown

"""
        
        # Dataset info
        if 'question' in self.df.columns:
            report += f"- **Unique Questions**: {self.df['question'].nunique()}\n"
        
        report += f"""
## Key Metrics

All metrics are computed per-result using:
- **Token F1**: Token-level overlap (precision & recall)
- **Word Overlap**: Jaccard similarity of word sets
- **Exact Match**: Percentage of exact predictions
- **Length Ratio**: Prediction length vs reference length

## Performance by Model

"""
        
        model_comp = self.generate_model_comparison()
        report += model_comp.to_markdown(index=False)
        
        report += f"""

## Performance by Provider

"""
        provider_comp = self.generate_provider_comparison()
        report += provider_comp.to_markdown(index=False)
        
        report += f"""

## Performance by Mode

"""
        mode_comp = self.generate_mode_comparison()
        report += mode_comp.to_markdown(index=False)
        
        report += f"""

## Model × Mode Performance Matrix

"""
        matrix = self.generate_model_mode_matrix()
        report += matrix.to_markdown()
        
        report += f"""

## Top Performers

"""
        top_performers = self.identify_best_performers('token_f1', top_k=10)
        for i, perf in enumerate(top_performers, 1):
            report += f"{i}. {perf['model']} ({perf['provider']}) - Mode: {perf['mode']} - Token F1: {perf['token_f1']:.4f}\n"
        
        report += f"""

## Failure Cases

Models that underperformed (Token F1 < 0.1):

"""
        failures = self.identify_failure_cases('token_f1', threshold=0.1, limit=5)
        for idx, row in failures.iterrows():
            report += f"""
### {row['question_id']} - {row['model_name']} ({row['mode']})
- **Score**: {row['token_f1']:.4f}
- **Question**: {row['question'][:100]}...
- **Expected**: {row['ground_truth'][:150]}...
- **Got**: {row['prediction'][:150]}...

"""
        
        report += """
## Insights & Recommendations

### Strengths
- Compare which models/providers perform best overall
- Identify which prompting mode (zero-shot vs RAG) works best
- Determine if specific models excel at particular question types

### Recommendations
1. Use the best-performing model for production deployment
2. Apply the most effective prompting mode to maximize accuracy
3. Investigate failure cases for systematic issues
4. Consider ensemble approaches combining multiple models
5. Fine-tune prompts based on question category

## Detailed Statistics

"""
        
        # Overall statistics
        report += f"""### Overall Token F1 Distribution
- Mean: {self.df['token_f1'].mean():.4f}
- Median: {self.df['token_f1'].median():.4f}
- Std Dev: {self.df['token_f1'].std():.4f}
- Min: {self.df['token_f1'].min():.4f}
- Max: {self.df['token_f1'].max():.4f}

### Exact Match Rate: {(self.df['exact_match'].mean() * 100):.2f}%
### Average Prediction Length: {self.df['pred_length'].mean():.0f} tokens
### Average Reference Length: {self.df['ref_length'].mean():.0f} tokens

---
Report generated by SyllabusQA Benchmark Analysis Suite
"""
        
        return report
    
    def save_analysis(self):
        """Save all analysis outputs"""
        logger.info("Saving analysis outputs...")
        
        # Compute metrics first
        self.compute_evaluation_metrics()
        
        # Save evaluated results
        eval_csv = self.output_dir / "evaluated_results.csv"
        self.df.to_csv(eval_csv, index=False)
        logger.info(f"✓ Saved evaluated results: {eval_csv}")
        
        # Save comparisons
        model_comp = self.generate_model_comparison()
        model_csv = self.output_dir / "model_comparison.csv"
        model_comp.to_csv(model_csv, index=False)
        logger.info(f"✓ Saved model comparison: {model_csv}")
        
        provider_comp = self.generate_provider_comparison()
        provider_csv = self.output_dir / "provider_comparison.csv"
        provider_comp.to_csv(provider_csv, index=False)
        logger.info(f"✓ Saved provider comparison: {provider_csv}")
        
        mode_comp = self.generate_mode_comparison()
        mode_csv = self.output_dir / "mode_comparison.csv"
        mode_comp.to_csv(mode_csv, index=False)
        logger.info(f"✓ Saved mode comparison: {mode_csv}")
        
        # Save matrix
        matrix = self.generate_model_mode_matrix()
        matrix_csv = self.output_dir / "model_mode_matrix.csv"
        matrix.to_csv(matrix_csv)
        logger.info(f"✓ Saved model x mode matrix: {matrix_csv}")
        
        # Save comprehensive report
        report = self.generate_comprehensive_report()
        report_md = self.output_dir / "ANALYSIS_REPORT.md"
        with open(report_md, "w") as f:
            f.write(report)
        logger.info(f"✓ Saved comprehensive report: {report_md}")
        
        # Save summary JSON
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_results": len(self.df),
            "models": self.df['model_name'].unique().tolist(),
            "providers": self.df['provider'].unique().tolist(),
            "modes": self.df['mode'].unique().tolist(),
            "overall_metrics": {
                "token_f1_mean": float(self.df['token_f1'].mean()),
                "token_f1_std": float(self.df['token_f1'].std()),
                "word_overlap_mean": float(self.df['word_overlap'].mean()),
                "exact_match_rate": float(self.df['exact_match'].mean()),
            },
            "files_generated": [
                str(eval_csv),
                str(model_csv),
                str(provider_csv),
                str(mode_csv),
                str(matrix_csv),
                str(report_md),
            ]
        }
        
        summary_json = self.output_dir / "analysis_summary.json"
        with open(summary_json, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"✓ Saved analysis summary: {summary_json}")
        
        print(f"\n{'='*70}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*70}")
        print(f"Results directory: {self.output_dir}")
        print(f"Open ANALYSIS_REPORT.md for full details")
        print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="SyllabusQA Benchmark Analysis")
    parser.add_argument("--results", required=True, help="Path to results file (JSONL or CSV)")
    parser.add_argument("--report-only", action="store_true", help="Only generate report, don't save")
    
    args = parser.parse_args()
    
    analyzer = BenchmarkAnalyzer(args.results)
    
    if args.report_only:
        report = analyzer.generate_comprehensive_report()
        print(report)
    else:
        analyzer.save_analysis()


if __name__ == "__main__":
    main()
