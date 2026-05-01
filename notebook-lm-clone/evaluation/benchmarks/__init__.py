"""
SyllabusQA Testing Module
Multi-model benchmarking framework for testing Academic Compass against SyllabusQA dataset
"""

from .model_providers import ModelConfig, UnifiedLLMProvider
from .syllabusqa_benchmark import SyllabusQABenchmark, load_config

__version__ = "1.0.0"
__all__ = [
    "ModelConfig",
    "UnifiedLLMProvider",
    "SyllabusQABenchmark",
    "load_config"
]
