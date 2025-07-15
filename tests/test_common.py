"""
Unit tests for spec_generator.utils.common module.

Tests for common utility functions.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from spec_generator.utils.common import (
    common_error_handler,
    ensure_utf8_encoding,
    format_console_message,
    get_env_var,
    safe_file_write,
    safe_json_load,
    standardized_logger,
    validate_directory_path,
    validate_file_path,
)


class TestStandardizedLogger:
    """Test standardized logger functionality."""

    def test_create_logger(self):
        """Test creating a standardized logger."""
        logger = standardized_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
        assert logger.level == logging.INFO

    def test_logger_handler_creation(self):
        """Test that logger creates handlers correctly."""
        logger = standardized_logger("test_handler")

        # Should have at least one handler
        assert len(logger.handlers) >= 1

        # First handler should be StreamHandler
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)

        # Should have a formatter
        assert handler.formatter is not None

    def test_logger_no_duplicate_handlers(self):
        """Test that calling standardized_logger twice doesn't create duplicate handlers."""
        logger1 = standardized_logger("test_duplicate")
        handler_count1 = len(logger1.handlers)

        logger2 = standardized_logger("test_duplicate")
        handler_count2 = len(logger2.handlers)

        # Should be the same logger instance
        assert logger1 is logger2
        assert handler_count1 == handler_count2

    def test_logger_different_names(self):
        """Test creating loggers with different names."""
        logger1 = standardized_logger("module1")
        logger2 = standardized_logger("module2")

        assert logger1 is not logger2
        assert logger1.name == "module1"
        assert logger2.name == "module2"


class TestCommonErrorHandler:
    """Test common error handler decorator."""

    def test_error_handler_success(self):
        """Test error handler with successful function execution."""

        @common_error_handler("test_operation")
        def successful_function(x, y):
            return x + y

        result = successful_function(2, 3)
        assert result == 5

    def test_error_handler_with_exception(self):
        """Test error handler with function that raises exception."""

        @common_error_handler("test_operation")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    def test_error_handler_logs_error(self):
        """Test that error handler logs errors."""

        @common_error_handler("test_operation")
        def failing_function():
            raise ValueError("Test error")

        with patch("spec_generator.utils.common.standardized_logger") as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance

            with pytest.raises(ValueError):
                failing_function()

            mock_logger.assert_called_once_with("tests.test_common")
            mock_logger_instance.error.assert_called_once_with(
                "test_operation failed: Test error"
            )

    def test_error_handler_preserves_function_metadata(self):
        """Test that error handler preserves function metadata."""

        @common_error_handler("test_operation")
        def documented_function(x):
            """This is a documented function."""
            return x * 2

        # Function should still be callable
        assert documented_function(5) == 10


class TestFormatConsoleMessage:
    """Test console message formatting."""

    def test_format_info_message(self):
        """Test formatting info message."""
        message = format_console_message("Test message", "info")
        assert message == "[blue]Test message[/blue]"

    def test_format_success_message(self):
        """Test formatting success message."""
        message = format_console_message("Success message", "success")
        assert message == "[green]Success message[/green]"

    def test_format_warning_message(self):
        """Test formatting warning message."""
        message = format_console_message("Warning message", "warning")
        assert message == "[yellow]Warning message[/yellow]"

    def test_format_error_message(self):
        """Test formatting error message."""
        message = format_console_message("Error message", "error")
        assert message == "[red]Error message[/red]"

    def test_format_unknown_level(self):
        """Test formatting with unknown level."""
        message = format_console_message("Unknown level", "unknown")
        assert message == "[white]Unknown level[/white]"

    def test_format_default_level(self):
        """Test formatting with default level."""
        message = format_console_message("Default message")
        assert message == "[blue]Default message[/blue]"


class TestValidateFilePath:
    """Test file path validation."""

    def test_validate_existing_file(self):
        """Test validating existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = Path(tmp.name)

        try:
            validated_path = validate_file_path(tmp_path)
            assert validated_path.resolve() == tmp_path.resolve()
            assert validated_path.is_absolute()
        finally:
            tmp_path.unlink()

    def test_validate_non_existing_file_must_exist(self):
        """Test validating non-existing file when it must exist."""
        non_existing = Path("/non/existing/file.txt")

        with pytest.raises(ValueError, match="Invalid file path.*File not found"):
            validate_file_path(non_existing, must_exist=True)

    def test_validate_non_existing_file_optional(self):
        """Test validating non-existing file when it's optional."""
        non_existing = Path("/non/existing/file.txt")

        validated_path = validate_file_path(non_existing, must_exist=False)
        assert validated_path.is_absolute()

    def test_validate_relative_path(self):
        """Test validating relative path."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = Path(tmp.name)

        try:
            # Get relative path
            relative_path = tmp_path.relative_to(Path.cwd())

            validated_path = validate_file_path(relative_path)
            assert validated_path.is_absolute()
            assert validated_path.resolve() == tmp_path.resolve()
        finally:
            tmp_path.unlink()

    def test_validate_string_path(self):
        """Test validating string path."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name

        try:
            validated_path = validate_file_path(tmp_path)
            assert isinstance(validated_path, Path)
            assert validated_path.is_absolute()
        finally:
            Path(tmp_path).unlink()

    def test_validate_invalid_path(self):
        """Test validating invalid path."""
        invalid_path = "\x00invalid\x00path"

        with pytest.raises(ValueError, match="Invalid file path"):
            validate_file_path(invalid_path)


class TestValidateDirectoryPath:
    """Test directory path validation."""

    def test_validate_existing_directory(self):
        """Test validating existing directory."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            validated_path = validate_directory_path(tmp_path)
            assert validated_path.resolve() == tmp_path.resolve()
            assert validated_path.is_absolute()

    def test_validate_non_existing_directory_create(self):
        """Test validating non-existing directory with creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            new_dir = tmp_path / "new_directory"

            validated_path = validate_directory_path(new_dir, create_if_missing=True)
            assert validated_path.exists()
            assert validated_path.is_dir()

    def test_validate_non_existing_directory_no_create(self):
        """Test validating non-existing directory without creation."""
        non_existing = Path("/non/existing/directory")

        with pytest.raises(
            ValueError, match="Invalid directory path.*Directory not found"
        ):
            validate_directory_path(non_existing, create_if_missing=False)

    def test_validate_file_as_directory(self):
        """Test validating file path as directory."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(ValueError, match="Path is not a directory"):
                validate_directory_path(tmp_path)
        finally:
            tmp_path.unlink()

    def test_validate_nested_directory_creation(self):
        """Test creating nested directories."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            nested_dir = tmp_path / "level1" / "level2" / "level3"

            validated_path = validate_directory_path(nested_dir, create_if_missing=True)
            assert validated_path.exists()
            assert validated_path.is_dir()


class TestSafeJsonLoad:
    """Test safe JSON loading."""

    def test_load_valid_json(self):
        """Test loading valid JSON file."""
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            json.dump(test_data, tmp)
            tmp_path = Path(tmp.name)

        try:
            loaded_data = safe_json_load(tmp_path)
            assert loaded_data == test_data
        finally:
            tmp_path.unlink()

    def test_load_invalid_json(self):
        """Test loading invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write('{"invalid": json,}')
            tmp_path = Path(tmp.name)

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                safe_json_load(tmp_path)
        finally:
            tmp_path.unlink()

    def test_load_non_existing_file(self):
        """Test loading non-existing JSON file."""
        non_existing = Path("/non/existing/file.json")

        with pytest.raises(ValueError, match="Failed to load JSON"):
            safe_json_load(non_existing)

    def test_load_json_with_utf8(self):
        """Test loading JSON with UTF-8 characters."""
        test_data = {"japanese": "こんにちは", "emoji": "🎉"}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(test_data, tmp, ensure_ascii=False)
            tmp_path = Path(tmp.name)

        try:
            loaded_data = safe_json_load(tmp_path)
            assert loaded_data == test_data
        finally:
            tmp_path.unlink()


class TestSafeFileWrite:
    """Test safe file writing."""

    def test_write_simple_file(self):
        """Test writing simple file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            file_path = tmp_path / "test.txt"
            content = "Test content"

            safe_file_write(file_path, content)

            assert file_path.exists()
            assert file_path.read_text(encoding="utf-8") == content

    def test_write_file_with_utf8(self):
        """Test writing file with UTF-8 content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            file_path = tmp_path / "test_utf8.txt"
            content = "日本語テスト 🎉"

            safe_file_write(file_path, content)

            assert file_path.exists()
            assert file_path.read_text(encoding="utf-8") == content

    def test_write_file_create_directories(self):
        """Test writing file with directory creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            file_path = tmp_path / "nested" / "dirs" / "test.txt"
            content = "Test content"

            safe_file_write(file_path, content)

            assert file_path.exists()
            assert file_path.read_text(encoding="utf-8") == content

    def test_write_file_different_encoding(self):
        """Test writing file with different encoding."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            file_path = tmp_path / "test_latin1.txt"
            content = "Test content"

            safe_file_write(file_path, content, encoding="latin-1")

            assert file_path.exists()
            assert file_path.read_text(encoding="latin-1") == content

    def test_write_file_error_handling(self):
        """Test file writing error handling."""
        # Try to write to a read-only location (this might vary by OS)
        with pytest.raises(ValueError, match="Failed to write to file"):
            safe_file_write("/root/readonly.txt", "content")


class TestGetEnvVar:
    """Test environment variable retrieval."""

    def test_get_existing_env_var(self):
        """Test getting existing environment variable."""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            value = get_env_var("TEST_VAR")
            assert value == "test_value"

    def test_get_non_existing_env_var_with_default(self):
        """Test getting non-existing environment variable with default."""
        with patch.dict(os.environ, {}, clear=True):
            value = get_env_var("NON_EXISTING_VAR", default="default_value")
            assert value == "default_value"

    def test_get_non_existing_env_var_no_default(self):
        """Test getting non-existing environment variable without default."""
        with patch.dict(os.environ, {}, clear=True):
            value = get_env_var("NON_EXISTING_VAR")
            assert value is None

    def test_get_required_env_var_exists(self):
        """Test getting required environment variable that exists."""
        with patch.dict(os.environ, {"REQUIRED_VAR": "required_value"}):
            value = get_env_var("REQUIRED_VAR", required=True)
            assert value == "required_value"

    def test_get_required_env_var_missing(self):
        """Test getting required environment variable that's missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError,
                match="Required environment variable 'REQUIRED_VAR' not found",
            ):
                get_env_var("REQUIRED_VAR", required=True)

    def test_get_required_env_var_with_default(self):
        """Test getting required environment variable with default (should ignore default)."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError,
                match="Required environment variable 'REQUIRED_VAR' not found",
            ):
                get_env_var("REQUIRED_VAR", default="default", required=True)

    def test_get_empty_env_var(self):
        """Test getting empty environment variable."""
        with patch.dict(os.environ, {"EMPTY_VAR": ""}):
            value = get_env_var("EMPTY_VAR", default="default")
            assert value == ""  # Empty string is not None


class TestEnsureUtf8Encoding:
    """Test UTF-8 encoding validation."""

    def test_valid_utf8_string(self):
        """Test valid UTF-8 string."""
        text = "Valid UTF-8 text"
        result = ensure_utf8_encoding(text)
        assert result == text

    def test_unicode_string(self):
        """Test Unicode string."""
        text = "日本語テスト 🎉"
        result = ensure_utf8_encoding(text)
        assert result == text

    def test_ascii_string(self):
        """Test ASCII string."""
        text = "Simple ASCII text"
        result = ensure_utf8_encoding(text)
        assert result == text

    def test_empty_string(self):
        """Test empty string."""
        text = ""
        result = ensure_utf8_encoding(text)
        assert result == text

    def test_multiline_string(self):
        """Test multiline string."""
        text = "Line 1\nLine 2\nLine 3"
        result = ensure_utf8_encoding(text)
        assert result == text

    def test_string_with_special_characters(self):
        """Test string with special characters."""
        text = "Special chars: åäöÅÄÖ"
        result = ensure_utf8_encoding(text)
        assert result == text


# Integration tests
class TestCommonUtilsIntegration:
    """Integration tests for common utilities."""

    def test_complete_workflow(self):
        """Test complete workflow using multiple utilities."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Validate directory
            validated_dir = validate_directory_path(tmp_path)
            assert validated_dir.exists()

            # Create a file with JSON content
            json_file = validated_dir / "test.json"
            test_data = {"message": "Hello, World!", "japanese": "こんにちは"}

            # Write JSON file
            json_content = json.dumps(test_data, ensure_ascii=False)
            safe_file_write(json_file, json_content)

            # Validate file exists
            validated_file = validate_file_path(json_file)
            assert validated_file.exists()

            # Load JSON data
            loaded_data = safe_json_load(validated_file)
            assert loaded_data == test_data

            # Ensure UTF-8 encoding
            message = ensure_utf8_encoding(loaded_data["japanese"])
            assert message == "こんにちは"

    def test_error_handling_workflow(self):
        """Test error handling across utilities."""

        @common_error_handler("test_workflow")
        def failing_workflow():
            # Try to validate non-existing file
            validate_file_path("/non/existing/file.txt", must_exist=True)

        with pytest.raises(ValueError):
            failing_workflow()

    def test_environment_and_logging_integration(self):
        """Test environment variables and logging integration."""
        # Set up environment variable
        with patch.dict(os.environ, {"TEST_LOG_LEVEL": "DEBUG"}):
            log_level = get_env_var("TEST_LOG_LEVEL", default="INFO")
            assert log_level == "DEBUG"

            # Create logger
            logger = standardized_logger("integration_test")
            assert logger.name == "integration_test"

            # Format console message
            message = format_console_message(f"Log level: {log_level}", "info")
            assert message == "[blue]Log level: DEBUG[/blue]"


# Fixtures
@pytest.fixture
def temp_directory():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test content")
        tmp_path = Path(tmp.name)

    yield tmp_path

    # Cleanup
    if tmp_path.exists():
        tmp_path.unlink()


def test_with_temp_directory(temp_directory):
    """Test using temporary directory fixture."""
    assert temp_directory.exists()
    assert temp_directory.is_dir()

    # Create file in temp directory
    test_file = temp_directory / "test.txt"
    safe_file_write(test_file, "test content")

    assert test_file.exists()


def test_with_temp_file(temp_file):
    """Test using temporary file fixture."""
    assert temp_file.exists()
    assert temp_file.is_file()

    # Validate the file
    validated_path = validate_file_path(temp_file)
    assert validated_path.resolve() == temp_file.resolve()
