"""
Common utilities for the Specification Generator.

This module provides standardized utilities for logging, error handling,
console output, and file validation to reduce code duplication.
"""

import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def standardized_logger(name: str) -> logging.Logger:
    """
    Create a standardized logger with consistent formatting.

    Args:
        name: Logger name, typically __name__ from the calling module.
    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers if they already exist
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler()

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Configure handler
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Set level if not already set
        if logger.level == logging.NOTSET:
            logger.setLevel(logging.INFO)

    return logger


def common_error_handler(operation_name: str):
    """
    Decorator for standardized error handling across modules.

    Args:
        operation_name: Name of the operation for error logging.

    Returns:
        Decorator function.
    """

    def decorator(func: F) -> F:
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger = standardized_logger(func.__module__)
                logger.error(f"{operation_name} failed: {e}")
                raise

        return wrapper

    return decorator


def format_console_message(message: str, level: str = "info") -> str:
    """
    Format console messages with consistent styling.

    Args:
        message: Message to format.
        level: Message level (info, success, warning, error).

    Returns:
        Formatted message string.
    """
    color_map = {
        "info": "blue",
        "success": "green",
        "warning": "yellow",
        "error": "red",
    }

    color = color_map.get(level, "white")

    return f"[{color}]{message}[/{color}]"


def validate_file_path(file_path: str | Path, must_exist: bool = True) -> Path:
    """
    Validate and normalize file paths with consistent error handling.

    Args:
        file_path: Path to validate.
        must_exist: Whether the file must exist.

    Returns:
        Validated Path object.

    Raises:
        ValueError: If path is invalid.
        FileNotFoundError: If file doesn't exist and must_exist=True.
    """
    try:
        path = Path(file_path)

        # Check if path is absolute or make it absolute
        if not path.is_absolute():
            path = path.resolve()

        # Check existence if required
        if must_exist and not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        return path

    except Exception as e:
        raise ValueError(f"Invalid file path '{file_path}': {e}") from e


def validate_directory_path(
    dir_path: str | Path, create_if_missing: bool = False
) -> Path:
    """
    Validate and normalize directory paths with consistent error handling.

    Args:
        dir_path: Directory path to validate.
        create_if_missing: Whether to create directory if it doesn't exist.

    Returns:
        Validated Path object.

    Raises:
        ValueError: If path is invalid.
        FileNotFoundError: If directory doesn't exist and create_if_missing=False.
    """
    try:
        path = Path(dir_path)

        # Check if path is absolute or make it absolute
        if not path.is_absolute():
            path = path.resolve()

        # Check existence and create if needed
        if not path.exists():
            if create_if_missing:
                path.mkdir(parents=True, exist_ok=True)
            else:
                raise FileNotFoundError(f"Directory not found: {path}")
        elif not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        return path

    except Exception as e:
        raise ValueError(f"Invalid directory path '{dir_path}': {e}") from e


def safe_json_load(file_path: str | Path) -> dict[str, Any]:
    """
    Safely load JSON file with standardized error handling.

    Args:
        file_path: Path to JSON file.

    Returns:
        Parsed JSON data.

    Raises:
        ValueError: If file cannot be parsed or doesn't exist.
    """
    import json

    try:
        path = validate_file_path(file_path, must_exist=True)

        with open(path, encoding="utf-8") as f:
            return json.load(f)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file '{file_path}': {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load JSON from '{file_path}': {e}") from e


def safe_file_write(
    file_path: str | Path, content: str, encoding: str = "utf-8"
) -> None:
    """
    Safely write content to file with standardized error handling.

    Args:
        file_path: Path to write to.
        content: Content to write.
        encoding: File encoding.

    Raises:
        ValueError: If file cannot be written.
    """
    try:
        path = Path(file_path)

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding=encoding) as f:
            f.write(content)

    except Exception as e:
        raise ValueError(f"Failed to write to file '{file_path}': {e}") from e


def get_env_var(
    name: str, default: Optional[str] = None, required: bool = False
) -> str:
    """
    Get environment variable with standardized error handling.
    Args:
        name: Environment variable name.
        default: Default value if not found.
        required: Whether the variable is required.
    Returns:
        Environment variable value.
    Raises:
        ValueError: If required variable is not found.
    """
    value = os.getenv(name, default)

    if required and value is None:
        raise ValueError(f"Required environment variable '{name}' not found")

    return value


def ensure_utf8_encoding(text: str) -> str:
    """
    Ensure text is properly UTF-8 encoded for content.
    Args:
        text: Text to check/encode.
    Returns:
        UTF-8 encoded text.
    """
    try:
        # Try to encode/decode to ensure proper UTF-8
        return text.encode("utf-8").decode("utf-8")
    except UnicodeError as e:
        raise ValueError(f"Text encoding error: {e}") from e
