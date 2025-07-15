"""
Japanese Specification Generator CLI Tool

A LangChain-based CLI tool that automatically generates Japanese IT industry
standard specification documents from codebases using Tree-sitter semantic
analysis and progressive prompting.
"""

__version__ = "0.1.0"

from .config import load_config, setup_logging, validate_config
from .models import (
    CodeChunk,
    ConfigLoader,
    Language,
    ProcessingStats,
    SemanticChange,
    SpecificationConfig,
    SpecificationOutput,
)

# Import core modules when they're created
try:
    from .core.diff_detector import SemanticDiffDetector
    from .core.generator import SpecificationGenerator
    from .core.processor import LargeCodebaseProcessor
except ImportError:
    # Modules not yet created, will be available after implementation
    pass

__all__ = [
    "load_config",
    "validate_config",
    "setup_logging",
    "SpecificationConfig",
    "CodeChunk",
    "SemanticChange",
    "Language",
    "ProcessingStats",
    "SpecificationOutput",
    "ConfigLoader",
]
