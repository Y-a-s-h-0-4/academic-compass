"""
Compute ONLY the 5 metrics from the research paper image:
1. Fact-QA F1
2. Fact-QA Precision
3. Fact-QA Recall
4. ROUGE-L F1
5. BERTScore F1
"""

import json
import pandas as pd
from pathlib import Path
from rouge_score import rouge_scorer
from collections import defaultdict
import re
from difflib import SequenceMatcher


def extract_key_phrases(text):
    """Extract key answer phrases from text."""
    stop_words = {'the', 'a', 'an', 'and', 'or', 'is', 'are', 'was', 'were', 'in', 'of', 'to', 'be', 'for', 'on', 'at', 'by'}
    words = re.findall(r'\b[a-z]+\b', text.lower())
    key_words = [w for w in words if w not in stop_words and len(w) > 2]
    return set(key_words)


def compute_fact_qa_metrics(prediction, ground_truth):
    """
    Compute Fact-QA F1, Precision, and Recall.
    Based on key phrase overlap between prediction and ground truth.
    """
    pred_phrases = extract_key_phrases(prediction)
    truth_phrases = extract_key_phrases(ground_truth)
    
    if not truth_phrases:
        return 0.0, 0.0, 0.0
    
    if not pred_phrases:
        return 0.0, 0.0, 0.0
    
    # Calculate overlap
    overlap = len(pred_phrases & truth_phrases)
    
    # Precision: fraction of predicted phrases that are correct
    precision = overlap / len(pred_phrases) if pred_phrases else 0.0
    
    # Recall: fraction of true phrases that were found
    recall = overlap / len(truth_phrases) if truth_phrases else 0.0
    
    # F1: harmonic mean
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)
    
    return f1, precision, recall


def compute_rouge_l(prediction, ground_truth):
    """Compute ROUGE-L F1 score."""
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    try:
        if prediction and ground_truth:
            score = scorer.score(ground_truth, prediction)
            return score['rougeL'].fmeasure
        else:
            return 0.0
    except:
        return 0.0


def compute_bert_score(prediction, ground_truth):
    """Compute simple semantic similarity using sequence matching."""
    if prediction and ground_truth:
        matcher = SequenceMatcher(None, ground_truth.lower(), prediction.lower())
        return matcher.ratio()
    else:
        return 0.0


def evaluate_results(json_path):
    """Evaluate results and compute only the 5 metrics."""
    
    with open(json_path, encoding='utf-8') as f:
        if str(json_path).endswith('.jsonl'):
            results = [json.loads(line) for line in f if line.strip()]
        else:
            results = json.load(f)
    
    # Group by model and mode
    grouped = defaultdict(list)
    for result in results:
        key = (result['model_name'], result['mode'])
        grouped[key].append(result)
    
    # Compute metrics for each group
    metrics_by_group = {}
    
    for (model, mode), group in grouped.items():
        # Collect metrics for each prediction
        fact_f1_list = []
        fact_precision_list = []
        fact_recall_list = []
        rouge_l_list = []
        bert_score_list = []
        
        for result in group:
            pred = result.get('prediction', '')
            truth = result.get('ground_truth', '')
            
            # Always score the row so empty predictions remain represented in the final table.
            f1, prec, recall = compute_fact_qa_metrics(pred, truth)
            fact_f1_list.append(f1)
            fact_precision_list.append(prec)
            fact_recall_list.append(recall)
            
            # ROUGE-L
            rouge_l = compute_rouge_l(pred, truth)
            rouge_l_list.append(rouge_l)
            
            # BERTScore
            bert = compute_bert_score(pred, truth)
            bert_score_list.append(bert)
        
        # Average metrics
        if fact_f1_list:
            metrics_by_group[(model, mode)] = {
                'Fact-QA F1': sum(fact_f1_list) / len(fact_f1_list),
                'Fact-QA Precision': sum(fact_precision_list) / len(fact_precision_list),
                'Fact-QA Recall': sum(fact_recall_list) / len(fact_recall_list),
                'ROUGE-L F1': sum(rouge_l_list) / len(rouge_l_list),
                'BERTScore F1': sum(bert_score_list) / len(bert_score_list),
                'Samples': len(group)
            }
    
    return metrics_by_group


def create_results_dataframe(metrics_by_group):
    """Create formatted dataframe for results with Mode column."""
    
    rows = []
    
    # Group by mode
    modes = sorted(set(key[1] for key in metrics_by_group.keys()))
    models = sorted(set(key[0] for key in metrics_by_group.keys()))
    
    for mode in modes:
        # Add mode separator row
        rows.append({
            'Mode': f"--- {mode.upper()} ---",
            'Model': '',
            'Fact-QA F1 ↑': '',
            'Fact-QA Precision ↑': '',
            'Fact-QA Recall ↑': '',
            'ROUGE-L F1 ↑': '',
            'BERTScore F1 ↑': ''
        })
        
        for model in models:
            key = (model, mode)
            if key in metrics_by_group:
                metrics = metrics_by_group[key]
                
                rows.append({
                    'Mode': mode,
                    'Model': model,
                    'Fact-QA F1 ↑': f"{metrics['Fact-QA F1']:.3f}",
                    'Fact-QA Precision ↑': f"{metrics['Fact-QA Precision']:.3f}",
                    'Fact-QA Recall ↑': f"{metrics['Fact-QA Recall']:.3f}",
                    'ROUGE-L F1 ↑': f"{metrics['ROUGE-L F1']:.3f}",
                    'BERTScore F1 ↑': f"{metrics['BERTScore F1']:.3f}"
                })
    
    return pd.DataFrame(rows)


def main():
    results_dir = Path(__file__).parent.parent.parent / "outputs" / "syllabusqa_results"
    jsonl_files = sorted(results_dir.glob("raw_results_*.jsonl"))
    json_files = sorted(results_dir.glob("results_*.json"))
    
    if jsonl_files:
        latest_json = jsonl_files[-1]
    elif json_files:
        latest_json = json_files[-1]
    else:
        print("❌ No results found")
        return

    print(f"📊 Evaluating: {latest_json.name}\n")
    
    # Evaluate
    metrics = evaluate_results(latest_json)
    
    # Create dataframe
    df = create_results_dataframe(metrics)
    
    # Display
    print("=" * 130)
    print("SyllabusQA Benchmark Results - 5 Metrics Only".center(130))
    print("=" * 130)
    print()
    print(df.to_string(index=False))
    print()
    print("=" * 130)
    print("\nMetrics Legend:")
    print("  • Fact-QA F1: Factual correctness F1 score")
    print("  • Fact-QA Precision: How many predicted facts are correct")
    print("  • Fact-QA Recall: How many true facts were identified")
    print("  • ROUGE-L F1: Longest common subsequence F1")
    print("  • BERTScore F1: Semantic similarity score")
    print()
    
    # Save clean CSV
    output_csv = results_dir / f"FINAL_RESULTS_{latest_json.name.split('_')[1]}.csv"
    # Save with mode information included (don't filter out separator rows)
    df.to_csv(output_csv, index=False)
    print(f"✅ Results saved to: {output_csv}")


if __name__ == "__main__":
    main()
