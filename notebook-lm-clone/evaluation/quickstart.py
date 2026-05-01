#!/usr/bin/env python3
"""
Quick Start Script for SyllabusQA Benchmarking
Downloads dataset, configures environment, and runs tests
"""

import os
import sys
import subprocess
import json
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(cmd: str, description: str = "") -> bool:
    """Run a shell command"""
    if description:
        logger.info(f"\n{'='*60}")
        logger.info(description)
        logger.info(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {cmd}")
        logger.error(f"Error: {e}")
        return False


def setup_environment():
    """Setup Python environment and dependencies"""
    logger.info("Setting up environment...")
    
    # Check Python version
    if sys.version_info < (3, 10):
        logger.error("Python 3.10+ required")
        return False
    
    # Install dependencies
    packages = [
        "pandas",
        "numpy",
        "openai",
        "google-generativeai",
        "anthropic",
        "huggingface-hub",
        "datasets",
        "rouge-score",
        "bertscore"
    ]
    
    logger.info("Installing required packages...")
    for package in packages:
        logger.info(f"  Installing {package}...")
        cmd = f"{sys.executable} -m pip install {package} -q"
        if not run_command(cmd):
            logger.warning(f"Failed to install {package}, continuing...")
    
    return True


def clone_syllabusqa_dataset():
    """Clone SyllabusQA dataset"""
    if Path("syllabusqa-data").exists():
        logger.info("✓ SyllabusQA dataset already exists")
        return True
    
    logger.info("Cloning SyllabusQA dataset...")
    cmd = "git clone https://github.com/umass-ml4ed/SyllabusQA.git syllabusqa-data"
    return run_command(cmd, "Downloading SyllabusQA Dataset")


def setup_api_keys():
    """Setup API keys"""
    env_file = ".env"
    env_content = ""
    
    if Path(env_file).exists():
        logger.info("✓ .env file already exists")
        return True
    
    logger.info("\nAPI Key Setup")
    logger.info("="*60)
    logger.info("Enter your API keys (press Enter to skip):")
    
    keys = {
        "OPENAI_API_KEY": input("OpenAI API Key: ").strip(),
        "GEMINI_API_KEY": input("Google Gemini API Key: ").strip(),
        "ANTHROPIC_API_KEY": input("Anthropic Claude API Key: ").strip(),
        "HUGGINGFACE_API_KEY": input("HuggingFace API Key: ").strip(),
    }
    
    env_content = "\n".join([
        f"{k}={v}" for k, v in keys.items() if v
    ])
    
    if env_content:
        with open(env_file, "w") as f:
            f.write(env_content)
        logger.info(f"✓ Saved API keys to {env_file}")
        return True
    else:
        logger.warning("No API keys provided. You'll need to set them in .env file")
        return False


def validate_setup():
    """Validate that everything is set up correctly"""
    logger.info("\nValidating setup...")
    
    # Check files exist
    required_files = [
        "evaluation/benchmarks/syllabusqa_benchmark.py",
        "evaluation/benchmarks/model_providers.py",
        "evaluation/benchmarks/syllabusqa_config.json",
        "evaluation/metrics/syllabusqa_metrics.py",
        "evaluation/comparison_analysis.py"
    ]
    
    for file in required_files:
        if not Path(file).exists():
            logger.error(f"Missing: {file}")
            return False
        logger.info(f"  ✓ {file}")
    
    # Check dataset
    dataset_path = Path("syllabusqa-data/data/dataset_split")
    if dataset_path.exists():
        logger.info(f"  ✓ Dataset found at {dataset_path}")
        return True
    else:
        logger.warning(f"⚠ Dataset not found at {dataset_path}")
        logger.info("    Run: git clone https://github.com/umass-ml4ed/SyllabusQA.git syllabusqa-data")
        return False


def run_sample_benchmark():
    """Run a sample benchmark with a small dataset"""
    logger.info("\nRunning sample benchmark (50 questions)...")
    
    cmd = f"""{sys.executable} evaluation/benchmarks/syllabusqa_benchmark.py \\
        --config evaluation/benchmarks/syllabusqa_config.json \\
        --dataset syllabusqa-data/data/dataset_split/test.csv \\
        --sample-size 50 \\
        --models gpt-4o-mini"""
    
    return run_command(cmd, "Running Sample Benchmark")


def generate_analysis():
    """Generate analysis from results"""
    results_file = Path("outputs/syllabusqa_results")
    
    if not results_file.exists():
        logger.warning("No results found. Run benchmark first.")
        return False
    
    # Find most recent results
    jsonl_files = list(results_file.glob("raw_results_*.jsonl"))
    if not jsonl_files:
        logger.warning("No result files found")
        return False
    
    latest_results = max(jsonl_files, key=os.path.getctime)
    logger.info(f"Analyzing results: {latest_results}")
    
    cmd = f"{sys.executable} evaluation/comparison_analysis.py --results {latest_results}"
    return run_command(cmd, "Generating Analysis Report")


def print_next_steps():
    """Print next steps"""
    print(f"""
{'='*70}
SETUP COMPLETE!
{'='*70}

Next Steps:

1. VERIFY API KEYS:
   - Check .env file has your API keys configured
   - Get keys from:
     * OpenAI: https://platform.openai.com/api-keys
     * Google: https://aistudio.google.com/app/apikey
     * Anthropic: https://console.anthropic.com/
     * HuggingFace: https://huggingface.co/settings/tokens

2. RUN SAMPLE BENCHMARK (quick test):
   python evaluation/benchmarks/syllabusqa_benchmark.py \\
     --config evaluation/benchmarks/syllabusqa_config.json \\
     --dataset syllabusqa-data/data/dataset_split/test.csv \\
     --sample-size 50

3. RUN FULL BENCHMARK:
   python evaluation/benchmarks/syllabusqa_benchmark.py \\
     --config evaluation/benchmarks/syllabusqa_config.json \\
     --dataset syllabusqa-data/data/dataset_split/test.csv

4. ANALYZE RESULTS:
   python evaluation/comparison_analysis.py \\
     --results outputs/syllabusqa_results/raw_results_*.jsonl

5. VIEW REPORT:
   - Open: outputs/syllabusqa_results/ANALYSIS_REPORT.md
   - Check: outputs/syllabusqa_results/model_comparison.csv
   - Details: outputs/syllabusqa_results/evaluated_results.csv

USAGE EXAMPLES:

Test specific models:
  python evaluation/benchmarks/syllabusqa_benchmark.py \\
    --config evaluation/benchmarks/syllabusqa_config.json \\
    --dataset syllabusqa-data/data/dataset_split/test.csv \\
    --models gpt-4o-mini gemini-2.0-flash

Test with different prompt modes:
  Edit evaluation/benchmarks/syllabusqa_config.json \\
  Set "modes": ["zero_shot", "rag", "rag_cot"]

For help:
  python evaluation/benchmarks/syllabusqa_benchmark.py --help

{'='*70}
Documentation: See SYLLABUSQA_TESTING_GUIDE.md
{'='*70}
""")


def main():
    logger.info("SyllabusQA Benchmark Setup")
    logger.info("="*60)
    
    # Change to repository root
    repo_root = Path(__file__).parent.parent.parent
    os.chdir(repo_root)
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Setup
    if not setup_environment():
        logger.error("Failed to setup environment")
        return False
    
    if not clone_syllabusqa_dataset():
        logger.warning("Failed to clone dataset (may already exist)")
    
    if not setup_api_keys():
        logger.warning("No API keys configured (you can add later to .env)")
    
    # Validate
    if not validate_setup():
        logger.error("Setup validation failed")
        return False
    
    # Optional: Run sample
    response = input("\nRun sample benchmark? (y/n, default: n): ").strip().lower()
    if response == 'y':
        if run_sample_benchmark():
            response2 = input("\nGenerate analysis report? (y/n, default: y): ").strip().lower()
            if response2 != 'n':
                generate_analysis()
    
    print_next_steps()
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
