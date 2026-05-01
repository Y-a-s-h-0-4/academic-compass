"""
Render the metrics CSV as publication-quality PDF and PNG with mode separators.
Generate both PDF and PNG exports with professional styling.
"""
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches


def find_latest_metrics_csv(results_dir: Path):
    # Prefer FINAL_RESULTS files that include Mode column
    files_final = sorted(results_dir.glob('FINAL_RESULTS_*.csv'))
    if files_final:
        return files_final[-1]
    # Fallback to metrics_detailed
    files_detailed = sorted(results_dir.glob('metrics_detailed_*.csv'))
    return files_detailed[-1] if files_detailed else None


def render_table_to_pdf_png(csv_path: Path, output_dir: Path):
    """Render metrics table to both PDF and PNG with professional styling and clear Mode labels."""
    
    df = pd.read_csv(csv_path, dtype=str).fillna('')
    
    # Clean up: remove separator rows and keep the Mode + Model info
    # Keep rows where Mode has a value (not separator rows or empty)
    df_clean = df.copy()
    df_clean = df_clean[~df_clean['Mode'].str.strip().str.startswith('---')]
    df_clean = df_clean[df_clean['Mode'].str.strip() != '']
    
    # Format Mode labels for clarity
    mode_map = {
        'rag': 'RAG',
        'rag_cot': 'RAG+CoT',
        'zero_shot': 'Zero-Shot'
    }
    df_clean['Mode'] = df_clean['Mode'].map(lambda x: mode_map.get(x.lower().strip(), x))
    
    # Create combined label for table display
    df_display = df_clean.copy()
    df_display['Model+Mode'] = df_display['Model'] + '\n(' + df_display['Mode'] + ')'
    
    # Reorder and drop redundant columns
    col_order = ['Model+Mode', 'Fact-QA F1 ↑', 'Fact-QA Precision ↑', 'Fact-QA Recall ↑', 'ROUGE-L F1 ↑', 'BERTScore F1 ↑']
    df_display = df_display[col_order]
    df_display.columns = ['Model (Mode)', 'Fact-QA F1', 'Fact-QA Precision', 'Fact-QA Recall', 'ROUGE-L F1', 'BERTScore F1']
    
    # Count rows and prepare dimensions
    num_rows = len(df_display)
    num_cols = len(df_display.columns)
    
    # Create figure with proper sizing
    fig_width = max(14, num_cols * 1.6)
    fig_height = max(3, 1.0 + 0.55 * num_rows)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis('off')
    
    # Prepare table data
    cell_text = df_display.values.tolist()
    col_labels = [
        'Model\n(Mode)',
        'Fact-QA\nF1',
        'Fact-QA\nPrecision',
        'Fact-QA\nRecall',
        'ROUGE-L\nF1',
        'BERTScore\nF1',
    ]
    
    # Create table with better styling
    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        cellLoc='center',
        loc='center',
        colWidths=[0.24, 0.14, 0.17, 0.16, 0.14, 0.15]
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(10.5)
    table.scale(1, 2.35)  # Increased row height for readability
    
    # Style the table
    for (r, c), cell in table.get_celld().items():
        cell.set_linewidth(1.5)
        
        if r == 0:
            # Header styling
            cell.set_text_props(weight='bold', color='white', size=11)
            cell.set_facecolor('#1f77b4')  # Professional blue
            cell.set_edgecolor('white')
        else:
            # Body row styling - alternate colors
            if r % 2 == 0:
                cell.set_facecolor('#f8f8f8')
            else:
                cell.set_facecolor('white')
            cell.set_edgecolor('#cccccc')
            cell.set_text_props(size=11)
    
    # Add title
    fig.text(0.5, 0.98, 'SyllabusQA Benchmark Results - 5 Gemini Models across 3 Modes', 
             ha='center', fontsize=14, weight='bold')
    
    # Add legend
    legend_text = 'Modes: RAG (Retrieval-Augmented Generation), RAG+CoT (RAG with Chain-of-Thought), Zero-Shot (No context)'
    fig.text(0.5, 0.01, legend_text, ha='center', fontsize=9, style='italic', color='#666666')
    
    # Generate PDF
    pdf_path = output_dir / f"FINAL_RESEARCH_TABLE.pdf"
    with PdfPages(pdf_path) as pdf:
        pdf.savefig(fig, bbox_inches='tight', pad_inches=0.5)
    print(f"✓ PDF saved to: {pdf_path}")
    
    # Generate PNG
    png_path = output_dir / f"FINAL_RESEARCH_TABLE.png"
    fig.savefig(png_path, dpi=300, bbox_inches='tight', pad_inches=0.5, facecolor='white')
    print(f"✓ PNG saved to: {png_path}")
    
    plt.close(fig)


def main():
    results_dir = Path(__file__).parent.parent.parent / 'outputs' / 'syllabusqa_results'
    latest = find_latest_metrics_csv(results_dir)
    if not latest:
        print('No suitable metrics CSV found in', results_dir)
        return
    
    print(f"Rendering {latest.name} to PDF and PNG...")
    render_table_to_pdf_png(latest, results_dir)


if __name__ == '__main__':
    main()
