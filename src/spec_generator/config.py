"""
Configuration management for the Japanese Specification Generator.

This module provides centralized configuration loading and management.
"""

import logging
from pathlib import Path
from typing import Optional

from .models import ConfigLoader, SpecificationConfig

# Configuration now uses environment variables only

logger = logging.getLogger(__name__)




def load_config() -> SpecificationConfig:
    """
    Load configuration from environment variables.

    Returns:
        SpecificationConfig: Loaded configuration.

    Raises:
        ValueError: If configuration is invalid.
    """
    config = ConfigLoader.load_from_env()
    logger.info("Loaded configuration from environment variables")
    return config


def validate_config(config: SpecificationConfig) -> None:
    """
    Validate configuration for completeness and correctness.

    Args:
        config: Configuration to validate.

    Raises:
        ValueError: If configuration is invalid.
    """
    # Check for required API keys
    if not config.openai_api_key and not config.azure_openai_endpoint:
        raise ValueError(
            "Either OPENAI_API_KEY or Azure OpenAI configuration is required"
        )

    # Validate Azure configuration
    if config.azure_openai_endpoint and not config.azure_openai_key:
        raise ValueError(
            "AZURE_OPENAI_KEY is required when AZURE_OPENAI_ENDPOINT is provided"
        )

    # Validate chunk configuration
    if config.chunk_overlap >= config.chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    # Validate memory limits
    if config.max_memory_mb < 64:
        raise ValueError("max_memory_mb must be at least 64 MB")

    # Validate parallel processes
    if config.parallel_processes < 1 or config.parallel_processes > 16:
        raise ValueError("parallel_processes must be between 1 and 16")

    logger.info("Configuration validation passed")


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Set up logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional log file path.
    """
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Set up handlers
    handlers = [logging.StreamHandler()]

    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()), format=log_format, handlers=handlers
    )

    # Reduce verbosity of third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)

    logger.info(f"Logging configured with level: {log_level}")


def get_default_config() -> SpecificationConfig:
    """Get default configuration with sensible defaults."""
    return SpecificationConfig()




# Environment variable names for configuration
ENV_VAR_MAPPING = {
    "openai_api_key": "OPENAI_API_KEY",
    "azure_openai_endpoint": "AZURE_OPENAI_ENDPOINT",
    "azure_openai_key": "AZURE_OPENAI_KEY",
    "azure_openai_version": "AZURE_OPENAI_VERSION",
    "max_memory_mb": "MAX_MEMORY_MB",
    "parallel_processes": "PARALLEL_PROCESSES",
    "chunk_size": "CHUNK_SIZE",
    "chunk_overlap": "CHUNK_OVERLAP",
    "output_format": "OUTPUT_FORMAT",
}
