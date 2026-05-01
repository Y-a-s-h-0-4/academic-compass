"""
Evaluate SyllabusQA benchmark results and format into comparison table.
Computes ROUGE-L metrics and simple similarity scores.
"""

import json
import csv
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
from difflib import SequenceMatcher

import pandas as pd
from rouge_score import rouge_scorer


def load_results(json_path: str) -> List[Dict]:
    """Load results from JSON file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def compute_rouge_l(predictions: List[str], references: List[str]) -> float:
    """Compute ROUGE-L F1 score."""
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    try:
        f1_scores = []
        for pred, ref in zip(predictions, references):
            score = scorer.score(ref, pred)
            f1_scores.append(score['rougeL'].fmeasure)
        return sum(f1_scores) / len(f1_scores) if f1_scores else 0.0
    except Exception as e:
        print(f"Warning: ROUGE computation failed: {e}", file=sys.stderr)
        return 0.0


def compute_bert_score(predictions: List[str], references: List[str]) -> float:
    """Compute simple similarity F1 using SequenceMatcher (fast alternative)."""
    try:
        similarities = []
        for pred, ref in zip(predictions, references):
            matcher = SequenceMatcher(None, ref.lower(), pred.lower())
            ratio = matcher.ratio()
            similarities.append(ratio)
        return sum(similarities) / len(similarities) if similarities else 0.0
    except Exception as e:
        print(f"Warning: Similarity computation failed: {e}", file=sys.stderr)
        return 0.0


def group_results(results: List[Dict]) -> Dict[Tuple[str, str], List[Dict]]:
    """Group results by (model_name, mode)."""
    grouped = defaultdict(list)
    for result in results:
        key = (result['model_name'], result['mode'])
        grouped[key].append(result)
    return grouped


def compute_metrics(group: List[Dict]) -> Dict[str, float]:
    """Compute metrics for a group of results."""
    predictions = [r['prediction'] for r in group]
    references = [r['ground_truth'] for r in group]
    
    metrics = {
        'rouge_l_f1': compute_rouge_l(predictions, references),
        'similarity': compute_bert_score(predictions, references),
        'count': len(group)
    }
    return metrics


def format_results_table(grouped_results: Dict) -> str:
    """Format results into a comparison table."""
    lines = []
    
    # Get unique modes and models
    modes = sorted(set(key[1] for key in grouped_results.keys()))
    models = sorted(set(key[0] for key in grouped_results.keys()))
    
    # Table header
    lines.append("=" * 110)
    lines.append(f"{'Model':<30} | {'Mode':<15} | {'ROUGE-L F1':>12} | {'Similarity':>12} | {'Samples':>8}")
    lines.append("-" * 110)
    
    # Results by mode
    current_mode = None
    for model in models:
        for mode in modes:
            key = (model, mode)
            if key in grouped_results:
                metrics = grouped_results[key]['metrics']
                if mode != current_mode:
                    current_mode = mode
                    lines.append(f"\n{mode.upper()}")
                
                lines.append(
                    f"{model:<30} | {mode:<15} | {metrics['rouge_l_f1']:>12.4f} | "
                    f"{metrics['similarity']:>12.4f} | {metrics['count']:>8}"
                )
    
    lines.append("=" * 110)
    return "\n".join(lines)


def save_metrics_csv(grouped_results: Dict, output_path: str):
    """Save metrics to CSV file."""
    rows = []
    for (model, mode), data in sorted(grouped_results.items()):
        metrics = data['metrics']
        rows.append({
            'Model': model,
            'Mode': mode,
            'ROUGE-L F1': metrics['rouge_l_f1'],
            'Similarity': metrics['similarity'],
            'Samples': metrics['count']
        })
    
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    print(f"Metrics saved to: {output_path}")


def main():
    # Get the most recent results file
    results_dir = Path(__file__).parent.parent.parent / "outputs" / "syllabusqa_results"
    
    # Find the latest results JSON
    json_files = sorted(results_dir.glob("results_*.json"))
    if not json_files:
        print("Error: No results JSON files found!")
        return
    
    latest_json = json_files[-1]
    print(f"Loading results from: {latest_json}")
    
    # Load and process results
    results = load_results(latest_json)
    print(f"Loaded {len(results)} results")
    
    # Group by model and mode
    grouped = group_results(results)
    
    # Compute metrics for each group
    grouped_with_metrics = {}
    print("\nComputing metrics...")
    for key, group in grouped.items():
        metrics = compute_metrics(group)
        grouped_with_metrics[key] = {
            'group': group,
            'metrics': metrics
        }
        print(f"  {key[0]} - {key[1]}: ROUGE-L={metrics['rouge_l_f1']:.4f}, Similarity={metrics['similarity']:.4f}")
    
    # Print formatted table
    print("\n" + format_results_table(grouped_with_metrics))
    
    # Save metrics to CSV
    metrics_csv = results_dir / f"metrics_{latest_json.name.split('_', 1)[1]}"
    save_metrics_csv(grouped_with_metrics, metrics_csv)


if __name__ == "__main__":
    main()
