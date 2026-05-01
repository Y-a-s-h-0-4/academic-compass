"""
Generate research-style formatted results table
"""

import json
import pandas as pd
from pathlib import Path
from collections import defaultdict


def create_research_table(metrics_csv_path):
    """Create formatted research-style table."""
    
    df = pd.read_csv(metrics_csv_path)
    
    # Clean up empty rows
    df = df.dropna(subset=['Fact-QA F1'])
    df = df[~df['Model'].str.contains('---', na=False)]
    
    print("\n" + "="*140)
    print("SyllabusQA Benchmark Results - Research Format")
    print("="*140)
    print()
    
    # Print formatted table
    print(f"{'Model':<25} | {'Factuality':<45} | {'Surface Textual Similarity':<45}")
    print(f"{'':25} | {'F1':<12} {'Prec.':<12} {'Recall':<12} | {'ROUGE-L':<12} {'BERTScore':<12}")
    print("-"*140)
    
    current_mode = None
    for _, row in df.iterrows():
        model = str(row['Model']).strip()
        
        # Check if it's a mode separator
        if '---' in model:
            if current_mode is not None:
                print()
            current_mode = model.replace('---', '').strip()
            print(f"\n{current_mode.upper()}")
            print("-"*140)
            continue
        
        try:
            fact_f1 = float(row['Fact-QA F1']) if row['Fact-QA F1'] else 0.0
            fact_prec = float(row['Fact-QA Precision']) if row['Fact-QA Precision'] else 0.0
            fact_recall = float(row['Fact-QA Recall']) if row['Fact-QA Recall'] else 0.0
            rouge_l = float(row['ROUGE-L F1']) if row['ROUGE-L F1'] else 0.0
            bert = float(row['BERTScore F1']) if row['BERTScore F1'] else 0.0
            
            print(f"{model:<25} | {fact_f1:>6.3f}      {fact_prec:>6.3f}      {fact_recall:>6.3f}  | {rouge_l:>6.3f}       {bert:>6.3f}")
        except (ValueError, TypeError):
            continue
    
    print("="*140)
    print("\nLegend:")
    print("  F1: Fact-QA F1 Score")
    print("  Prec.: Fact-QA Precision") 
    print("  Recall: Fact-QA Recall")
    print("  ROUGE-L: ROUGE-L F1 Score")
    print("  BERTScore: Semantic similarity score")
    print()


def create_summary_csv(metrics_csv_path, output_path):
    """Create clean CSV for viewing in Excel."""
    
    df = pd.read_csv(metrics_csv_path)
    
    # Clean and rename columns
    df_clean = df.copy()
    df_clean = df_clean[~df_clean['Model'].str.contains('---', na=False)]
    df_clean = df_clean.dropna(subset=['Fact-QA F1'])
    
    # Rename columns for clarity
    df_clean.columns = ['Model', 'Fact-QA F1 ↑', 'Fact-QA Precision ↑', 
                        'Fact-QA Recall ↑', 'ROUGE-L F1 ↑', 'BERTScore F1 ↑']
    
    df_clean.to_csv(output_path, index=False)
    print(f"\n✓ Summary table saved to: {output_path}")
    print("\nTable preview:")
    print(df_clean.to_string(index=False))


if __name__ == "__main__":
    results_dir = Path(__file__).parent.parent.parent / "outputs" / "syllabusqa_results"
    
    # Find latest metrics CSV
    metrics_files = sorted(results_dir.glob("metrics_detailed_*.csv"))
    if not metrics_files:
        print("No metrics files found")
        exit(1)
    
    latest_metrics = metrics_files[-1]
    print(f"Loading metrics from: {latest_metrics.name}")
    
    # Create research table
    create_research_table(str(latest_metrics))
    
    # Create summary CSV
    summary_path = results_dir / f"RESEARCH_TABLE_{latest_metrics.name.split('_')[-1]}"
    create_summary_csv(str(latest_metrics), str(summary_path))
