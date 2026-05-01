"""
Generate summary table directly from results and display metrics.
"""

import json
from pathlib import Path
import pandas as pd
from collections import defaultdict


def generate_summary():
    """Generate and display summary of results."""
    
    results_dir = Path(__file__).parent.parent.parent / "outputs" / "syllabusqa_results"
    json_files = sorted(results_dir.glob("results_*.json"))
    
    if not json_files:
        print("No results found")
        return
    
    latest_json = json_files[-1]
    print(f"Analyzing: {latest_json.name}\n")
    
    with open(latest_json) as f:
        results = json.load(f)
    
    # Group by model and mode
    grouped = defaultdict(list)
    for result in results:
        key = (result['model_name'], result['mode'])
        grouped[key].append(result)
    
    # Create summary table
    print("=" * 120)
    print(f"{'Model':<30} | {'Mode':<15} | {'Ground Truth':<50} | {'Has Prediction':>15}")
    print("-" * 120)
    
    summary_data = []
    for (model, mode), group in sorted(grouped.items()):
        for i, result in enumerate(group):
            pred_len = len(result.get('prediction', '')) if result.get('prediction') else 0
            has_pred = "✓ Yes" if pred_len > 0 else "✗ Empty"
            
            truth = result['ground_truth'][:45] + "..." if len(result['ground_truth']) > 45 else result['ground_truth']
            
            print(f"{model:<30} | {mode:<15} | {truth:<50} | {has_pred:>15}")
            
            summary_data.append({
                'Model': model,
                'Mode': mode,
                'Has Output': 'Yes' if pred_len > 0 else 'No',
                'Output Length': pred_len
            })
    
    print("=" * 120)
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    
    df_summary = pd.DataFrame(summary_data)
    
    print("\nBy Model:")
    model_summary = df_summary.groupby('Model').agg({
        'Has Output': lambda x: (x == 'Yes').sum(),
        'Output Length': ['mean', 'min', 'max']
    })
    print(model_summary)
    
    print("\nBy Mode:")
    mode_summary = df_summary.groupby('Mode').agg({
        'Has Output': lambda x: (x == 'Yes').sum(),
        'Output Length': ['mean', 'min', 'max']
    })
    print(mode_summary)
    
    # Save CSV
    csv_path = results_dir / f"summary_{latest_json.name.split('_', 1)[1].replace('.json', '.csv')}"
    df_summary.to_csv(csv_path, index=False)
    print(f"\nSummary saved to: {csv_path}")
    
    # Generate HTML table
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>SyllabusQA Benchmark Results - {latest_json.name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .title {{ font-size: 28px; font-weight: bold; margin-bottom: 10px; color: #333; }}
        .subtitle {{ color: #666; margin-bottom: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #2196F3; color: white; font-weight: 600; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #f0f0f0; }}
        .yes {{ color: #4CAF50; font-weight: bold; }}
        .no {{ color: #f44336; font-weight: bold; }}
        .metric {{ background-color: #e3f2fd; padding: 20px; margin: 20px 0; border-radius: 4px; }}
        .metric h3 {{ margin-top: 0; color: #1976d2; }}
        .metric table {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="title">SyllabusQA Benchmark Results</div>
        <div class="subtitle">Analysis of: <strong>{latest_json.name}</strong></div>
        
        <h2>Results by Model and Mode</h2>
        <table>
            <tr>
                <th>Model</th>
                <th>Mode</th>
                <th>Has Output</th>
                <th>Output Length</th>
            </tr>
"""
    
    for _, row in df_summary.iterrows():
        status_class = 'yes' if row['Has Output'] == 'Yes' else 'no'
        status_text = row['Has Output']
        html_content += f"""            <tr>
                <td>{row['Model']}</td>
                <td>{row['Mode']}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{row['Output Length']}</td>
            </tr>
"""
    
    html_content += """        </table>
        
        <div class="metric">
            <h3>Summary by Model</h3>
            <table>
                <tr>
                    <th>Model</th>
                    <th>Tests with Output</th>
                    <th>Avg Output Length</th>
                </tr>
"""
    
    for model in sorted(df_summary['Model'].unique()):
        model_data = df_summary[df_summary['Model'] == model]
        has_output = (model_data['Has Output'] == 'Yes').sum()
        avg_len = model_data['Output Length'].mean()
        html_content += f"""                <tr>
                    <td>{model}</td>
                    <td>{has_output} / {len(model_data)}</td>
                    <td>{avg_len:.0f}</td>
                </tr>
"""
    
    html_content += """            </table>
        </div>
        
        <div class="metric">
            <h3>Summary by Mode</h3>
            <table>
                <tr>
                    <th>Mode</th>
                    <th>Tests with Output</th>
                    <th>Avg Output Length</th>
                </tr>
"""
    
    for mode in sorted(df_summary['Mode'].unique()):
        mode_data = df_summary[df_summary['Mode'] == mode]
        has_output = (mode_data['Has Output'] == 'Yes').sum()
        avg_len = mode_data['Output Length'].mean()
        html_content += f"""                <tr>
                    <td><strong>{mode.upper()}</strong></td>
                    <td>{has_output} / {len(mode_data)}</td>
                    <td>{avg_len:.0f}</td>
                </tr>
"""
    
    html_content += """            </table>
        </div>
    </div>
</body>
</html>
"""
    
    html_path = results_dir / f"report_{latest_json.name.split('_', 1)[1]}"
    with open(html_path, 'w') as f:
        f.write(html_content)
    
    print(f"\nHTML report saved to: {html_path}")


if __name__ == "__main__":
    generate_summary()
