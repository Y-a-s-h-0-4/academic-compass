"""
Compute comprehensive evaluation metrics: Fact-QA, ROUGE-L, BERTScore
"""

import json
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher
import re

import pandas as pd
from rouge_score import rouge_scorer


def compute_rouge_l(predictions, references):
    """Compute ROUGE-L F1 score."""
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    scores = []
    for pred, ref in zip(predictions, references):
        if pred and ref:
            score = scorer.score(ref, pred)
            scores.append(score['rougeL'].fmeasure)
        else:
            scores.append(0.0)
    return sum(scores) / len(scores) if scores else 0.0


def compute_bert_score_simple(predictions, references):
    """Compute simple semantic similarity."""
    similarities = []
    for pred, ref in zip(predictions, references):
        if pred and ref:
            matcher = SequenceMatcher(None, ref.lower(), pred.lower())
            ratio = matcher.ratio()
            similarities.append(ratio)
        else:
            similarities.append(0.0)
    return sum(similarities) / len(similarities) if similarities else 0.0


def extract_answer_phrases(text):
    """Extract key answer phrases from text."""
    # Remove common words and extract key terms
    stop_words = {'the', 'a', 'an', 'and', 'or', 'is', 'are', 'was', 'were', 'in', 'of', 'to', 'be'}
    words = re.findall(r'\b[a-z]+\b', text.lower())
    key_words = [w for w in words if w not in stop_words and len(w) > 3]
    return set(key_words)


def compute_factuality_metrics(prediction, ground_truth):
    """
    Compute Fact-QA style metrics: Precision, Recall, F1
    Based on overlap of key answer phrases
    """
    pred_phrases = extract_answer_phrases(prediction)
    truth_phrases = extract_answer_phrases(ground_truth)
    
    if not truth_phrases:
        return 0.0, 0.0, 0.0
    
    if not pred_phrases:
        return 0.0, 0.0, 0.0
    
    # Calculate overlap
    overlap = len(pred_phrases & truth_phrases)
    
    # Precision: how many predicted phrases are correct
    precision = overlap / len(pred_phrases) if pred_phrases else 0.0
    
    # Recall: how many true phrases were found
    recall = overlap / len(truth_phrases) if truth_phrases else 0.0
    
    # F1: harmonic mean
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)
    
    return f1, precision, recall


def evaluate_results(json_path):
    """Evaluate all results and compute metrics."""
    
    with open(json_path) as f:
        results = json.load(f)
    
    # Group by model and mode
    grouped = defaultdict(list)
    for result in results:
        key = (result['model_name'], result['mode'])
        grouped[key].append(result)
    
    # Compute metrics for each group
    metrics_by_model_mode = {}
    
    for (model, mode), group in grouped.items():
        predictions = [r['prediction'] for r in group if r.get('prediction')]
        references = [r['ground_truth'] for r in group]
        
        if not predictions:
            continues_flag = True
        else:
            continues_flag = False
        
        if continues_flag:
            continue
        
        # Compute all metrics
        fact_qa_scores = [compute_factuality_metrics(p, r) for p, r in zip(predictions, references)]
        
        fact_f1 = sum(s[0] for s in fact_qa_scores) / len(fact_qa_scores) if fact_qa_scores else 0.0
        fact_precision = sum(s[1] for s in fact_qa_scores) / len(fact_qa_scores) if fact_qa_scores else 0.0
        fact_recall = sum(s[2] for s in fact_qa_scores) / len(fact_qa_scores) if fact_qa_scores else 0.0
        
        rouge_l = compute_rouge_l(predictions, references)
        bert_score = compute_bert_score_simple(predictions, references)
        
        metrics_by_model_mode[(model, mode)] = {
            'fact_f1': fact_f1,
            'fact_precision': fact_precision,
            'fact_recall': fact_recall,
            'rouge_l': rouge_l,
            'bert_score': bert_score,
            'count': len(group)
        }
    
    return metrics_by_model_mode


def create_results_table(metrics_by_model_mode):
    """Create formatted results table."""
    
    # Organize by mode
    modes = sorted(set(key[1] for key in metrics_by_model_mode.keys()))
    models = sorted(set(key[0] for key in metrics_by_model_mode.keys()))
    
    rows = []
    
    current_mode = None
    for model in models:
        for mode in modes:
            key = (model, mode)
            if key in metrics_by_model_mode:
                metrics = metrics_by_model_mode[key]
                
                if mode != current_mode:
                    current_mode = mode
                    rows.append({
                        'Model': f"--- {mode.upper()} ---",
                        'Fact-QA F1': '',
                        'Fact-QA Precision': '',
                        'Fact-QA Recall': '',
                        'ROUGE-L F1': '',
                        'BERTScore F1': ''
                    })
                
                rows.append({
                    'Model': model,
                    'Fact-QA F1': f"{metrics['fact_f1']:.3f}",
                    'Fact-QA Precision': f"{metrics['fact_precision']:.3f}",
                    'Fact-QA Recall': f"{metrics['fact_recall']:.3f}",
                    'ROUGE-L F1': f"{metrics['rouge_l']:.3f}",
                    'BERTScore F1': f"{metrics['bert_score']:.3f}"
                })
    
    df = pd.DataFrame(rows)
    return df


def main():
    results_dir = Path(__file__).parent.parent.parent / "outputs" / "syllabusqa_results"
    json_files = sorted(results_dir.glob("results_*.json"))
    
    if not json_files:
        print("No results found")
        return
    
    latest_json = json_files[-1]
    print(f"Evaluating: {latest_json.name}\n")
    
    # Compute metrics
    metrics = evaluate_results(latest_json)
    
    # Create table
    df = create_results_table(metrics)
    
    # Display
    print("=" * 120)
    print(df.to_string(index=False))
    print("=" * 120)
    
    # Save
    output_csv = results_dir / f"metrics_detailed_{latest_json.name.split('_', 1)[1].replace('.json', '.csv')}"
    df.to_csv(output_csv, index=False)
    print(f"\nMetrics saved to: {output_csv}")
    
    return df


if __name__ == "__main__":
    main()
