"""
Generate a formatted HTML report of evaluation metrics.
"""

import json
from pathlib import Path
import pandas as pd


def create_html_report(json_path: str, csv_path: str):
    """Create formatted HTML report from metrics CSV."""
    
    # Load the CSV
    df = pd.read_csv(csv_path)
    
    # Group by model and mode
    pivot_table = []
    
    for model in sorted(df['Model'].unique()):
        model_data = df[df['Model'] == model]
        for mode in sorted(model_data['Mode'].unique()):
            mode_data = model_data[model_data['Mode'] == mode]
            if len(mode_data) > 0:
                row = mode_data.iloc[0]
                pivot_table.append({
                    'Model': model,
                    'Mode': mode,
                    'ROUGE-L F1': f"{row['ROUGE-L F1']:.4f}",
                    'Similarity': f"{row['Similarity']:.4f}",
                    'Samples': int(row['Samples'])
                })
    
    pivot_df = pd.DataFrame(pivot_table)
    
    # Create HTML
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SyllabusQA Benchmark Results</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #4CAF50; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            tr:hover { background-color: #ddd; }
            .header { font-size: 24px; font-weight: bold; margin-bottom: 10px; }
            .section { margin: 30px 0; }
            .metric-positive { color: green; }
            .metric-zero { color: #999; }
        </style>
    </head>
    <body>
        <div class="header">SyllabusQA Benchmark Evaluation Results</div>
        <div>Generated from: results_20260429_234944.json</div>
        
        <div class="section">
            <h2>Detailed Results by Model and Mode</h2>
            <table>
                <tr>
                    <th>Model</th>
                    <th>Mode</th>
                    <th>ROUGE-L F1</th>
                    <th>Similarity</th>
                    <th>Samples</th>
                </tr>
    """
    
    for _, row in pivot_df.iterrows():
        rouge = float(row['ROUGE-L F1'])
        sim = float(row['Similarity'])
        
        rouge_class = 'metric-positive' if rouge > 0 else 'metric-zero'
        sim_class = 'metric-positive' if sim > 0 else 'metric-zero'
        
        html += f"""
                <tr>
                    <td>{row['Model']}</td>
                    <td>{row['Mode']}</td>
                    <td class="{rouge_class}">{row['ROUGE-L F1']}</td>
                    <td class="{sim_class}">{row['Similarity']}</td>
                    <td>{row['Samples']}</td>
                </tr>
        """
    
    html += """
            </table>
        </div>
        
        <div class="section">
            <h2>Summary by Model</h2>
            <table>
                <tr>
                    <th>Model</th>
                    <th>Avg ROUGE-L F1</th>
                    <th>Avg Similarity</th>
                    <th>Modes Tested</th>
                </tr>
    """
    
    # Summary by model
    for model in sorted(df['Model'].unique()):
        model_data = df[df['Model'] == model]
        avg_rouge = model_data['ROUGE-L F1'].mean()
        avg_sim = model_data['Similarity'].mean()
        modes_count = model_data['Mode'].nunique()
        
        html += f"""
                <tr>
                    <td>{model}</td>
                    <td>{avg_rouge:.4f}</td>
                    <td>{avg_sim:.4f}</td>
                    <td>{modes_count}</td>
                </tr>
        """
    
    html += """
            </table>
        </div>
        
        <div class="section">
            <h2>Summary by Mode</h2>
            <table>
                <tr>
                    <th>Mode</th>
                    <th>Avg ROUGE-L F1</th>
                    <th>Avg Similarity</th>
                    <th>Models Tested</th>
                </tr>
    """
    
    # Summary by mode
    for mode in sorted(df['Mode'].unique()):
        mode_data = df[df['Mode'] == mode]
        avg_rouge = mode_data['ROUGE-L F1'].mean()
        avg_sim = mode_data['Similarity'].mean()
        models_count = mode_data['Model'].nunique()
        
        html += f"""
                <tr>
                    <td>{mode.upper()}</td>
                    <td>{avg_rouge:.4f}</td>
                    <td>{avg_sim:.4f}</td>
                    <td>{models_count}</td>
                </tr>
        """
    
    html += """
            </table>
        </div>
        
        <div class="section">
            <h3>Notes:</h3>
            <ul>
                <li><strong>ROUGE-L F1:</strong> Longest common subsequence F1 score (0-1)</li>
                <li><strong>Similarity:</strong> Simple string similarity ratio (0-1)</li>
                <li><strong>Modes:</strong> zero_shot (no context), rag (with retrieval), rag_cot (with chain-of-thought)</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    # Save HTML
    results_dir = Path(json_path).parent
    html_path = results_dir / "metrics_report.html"
    with open(html_path, 'w') as f:
        f.write(html)
    
    print(f"\nHTML report saved to: {html_path}")
    return str(html_path)


if __name__ == "__main__":
    results_dir = Path(__file__).parent.parent.parent / "outputs" / "syllabusqa_results"
    
    # Find the latest metrics CSV
    csv_files = sorted(results_dir.glob("metrics_*.json"))
    if not csv_files:
        print("No metrics CSV files found")
        exit(1)
    
    # The CSV should be alongside the metrics file
    json_files = sorted(results_dir.glob("results_*.json"))
    if json_files:
        latest_json = json_files[-1]
        csv_path = results_dir / f"metrics_{latest_json.name.split('_', 1)[1].replace('.json', '.csv')}"
        
        if not csv_path.exists():
            print(f"Metrics CSV not found: {csv_path}")
            exit(1)
        
        html_path = create_html_report(str(latest_json), str(csv_path))
        print(f"Successfully created report at: {html_path}")
