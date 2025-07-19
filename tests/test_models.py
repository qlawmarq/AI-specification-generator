"""
Unit tests for spec_generator.models module.

Tests for Pydantic models including Language enum, CodeChunk,
SemanticChange, SpecificationConfig, and related classes.
"""

from pathlib import Path

import pytest

from spec_generator.models import (
    CodeChunk,
    ConfigLoader,
    Language,
    PerformanceSettings,
    ProcessingStats,
    SemanticChange,
    SpecificationConfig,
    SpecificationOutput,
)


class TestLanguageEnum:
    """Test Language enum functionality."""

    def test_supported_languages(self):
        """Test that all expected languages are supported."""
        expected_languages = {"python", "javascript", "typescript", "java", "cpp"}
        actual_languages = {lang.value for lang in Language}
        assert expected_languages == actual_languages

    def test_language_from_string(self):
        """Test creating Language from string values."""
        assert Language("python") == Language.PYTHON
        assert Language("javascript") == Language.JAVASCRIPT
        assert Language("typescript") == Language.TYPESCRIPT

    def test_language_invalid_value(self):
        """Test handling of invalid language values."""
        with pytest.raises(ValueError):
            Language("invalid_language")


class TestCodeChunk:
    """Test CodeChunk model functionality."""

    def test_code_chunk_creation(self):
        """Test basic CodeChunk creation."""
        chunk = CodeChunk(
            content="def hello(): pass",
            file_path=Path("test.py"),
            start_line=1,
            end_line=1,
            language=Language.PYTHON,
            chunk_type="function",
        )

        assert chunk.content == "def hello(): pass"
        assert chunk.file_path == Path("test.py")
        assert chunk.start_line == 1
        assert chunk.end_line == 1
        assert chunk.language == Language.PYTHON
        assert chunk.chunk_type == "function"

    def test_code_chunk_with_metadata(self):
        """Test CodeChunk with metadata."""
        chunk = CodeChunk(
            content="def hello(): pass",
            file_path=Path("test.py"),
            start_line=1,
            end_line=1,
            language=Language.PYTHON,
            chunk_type="function",
        )

        assert chunk.chunk_type == "function"

    def test_code_chunk_line_validation(self):
        """Test that end_line must be >= start_line."""
        with pytest.raises(ValueError):
            CodeChunk(
                content="test",
                file_path=Path("test.py"),
                start_line=5,
                end_line=3,  # Invalid: end < start
                language=Language.PYTHON,
                chunk_type="function",
            )

    def test_code_chunk_serialization(self):
        """Test CodeChunk serialization."""
        chunk = CodeChunk(
            content="def hello(): pass",
            file_path=Path("test.py"),
            start_line=1,
            end_line=1,
            language=Language.PYTHON,
            chunk_type="function",
        )

        data = chunk.model_dump()
        assert data["content"] == "def hello(): pass"
        assert str(data["file_path"]) == "test.py"
        assert data["language"] == Language.PYTHON


class TestSemanticChange:
    """Test SemanticChange model functionality."""

    def test_semantic_change_creation(self):
        """Test basic SemanticChange creation."""
        change = SemanticChange(
            element_name="test_function",
            element_type="function",
            change_type="added",
            file_path=Path("test.py"),
            impact_score=5.0,
        )

        assert change.element_name == "test_function"
        assert change.element_type == "function"
        assert change.change_type == "added"
        assert change.file_path == Path("test.py")
        assert change.impact_score == 5.0
        assert change.dependencies == []

    def test_semantic_change_with_description(self):
        """Test SemanticChange with dependencies."""
        dependencies = ["module1", "module2"]
        change = SemanticChange(
            element_name="critical_function",
            element_type="function",
            change_type="modified",
            file_path=Path("core.py"),
            impact_score=8.5,
            dependencies=dependencies,
        )

        assert change.dependencies == dependencies
        assert change.element_name == "critical_function"

    def test_impact_score_validation(self):
        """Test impact score validation."""
        # Valid impact scores
        change1 = SemanticChange(
            element_name="test",
            element_type="function",
            change_type="added",
            file_path=Path("test.py"),
            impact_score=0.0,
        )
        assert change1.impact_score == 0.0

        change2 = SemanticChange(
            element_name="test",
            element_type="function",
            change_type="added",
            file_path=Path("test.py"),
            impact_score=10.0,
        )
        assert change2.impact_score == 10.0

        # Invalid impact scores
        with pytest.raises(ValueError):
            SemanticChange(
                element_name="test",
                element_type="function",
                change_type="added",
                file_path=Path("test.py"),
                impact_score=-1.0,  # Too low
            )

        with pytest.raises(ValueError):
            SemanticChange(
                element_name="test",
                element_type="function",
                change_type="added",
                file_path=Path("test.py"),
                impact_score=11.0,  # Too high
            )


class TestPerformanceSettings:
    """Test PerformanceSettings model functionality."""

    def test_performance_settings_defaults(self):
        """Test default performance settings."""
        settings = PerformanceSettings()

        assert settings.request_timeout == 300
        assert settings.max_retries == 3
        assert settings.retry_delay == 1
        assert settings.rate_limit_rpm == 200
        assert settings.batch_size == 10

    def test_performance_settings_custom(self):
        """Test custom performance settings."""
        settings = PerformanceSettings(
            batch_size=20, max_retries=5, request_timeout=60, rate_limit_rpm=100
        )

        assert settings.batch_size == 20
        assert settings.max_retries == 5
        assert settings.request_timeout == 60
        assert settings.rate_limit_rpm == 100


class TestSpecificationConfig:
    """Test SpecificationConfig model functionality."""

    def test_specification_config_defaults(self):
        """Test default configuration values."""
        config = SpecificationConfig()

        assert config.chunk_size == 4000
        assert config.chunk_overlap == 200
        assert config.max_memory_mb == 1024
        assert config.parallel_processes == 4
        assert config.output_format == "japanese_detailed_design"
        assert config.supported_languages == [
            Language.PYTHON,
            Language.JAVASCRIPT,
            Language.TYPESCRIPT,
            Language.JAVA,
            Language.CPP,
        ]
        assert config.openai_api_key is None
        assert config.azure_openai_endpoint is None
        assert isinstance(config.performance_settings, PerformanceSettings)

    def test_specification_config_custom(self):
        """Test custom configuration values."""
        performance = PerformanceSettings(batch_size=15, max_retries=2)
        config = SpecificationConfig(
            chunk_size=1500,
            chunk_overlap=150,
            max_memory_mb=8192,
            parallel_processes=8,
            output_format="json",
            supported_languages=[Language.PYTHON, Language.JAVA],
            openai_api_key="test-key",
            azure_openai_endpoint="https://test.azure.com",
            performance_settings=performance,
        )

        assert config.chunk_size == 1500
        assert config.chunk_overlap == 150
        assert config.max_memory_mb == 8192
        assert config.parallel_processes == 8
        assert config.output_format == "json"
        assert config.supported_languages == [Language.PYTHON, Language.JAVA]
        assert config.openai_api_key == "test-key"
        assert config.azure_openai_endpoint == "https://test.azure.com"
        assert config.performance_settings.batch_size == 15

    def test_specification_config_validation(self):
        """Test configuration validation."""
        # Invalid chunk size
        with pytest.raises(ValueError):
            SpecificationConfig(chunk_size=0)

        # Invalid parallel processes
        with pytest.raises(ValueError):
            SpecificationConfig(parallel_processes=0)

        # Invalid memory limit
        with pytest.raises(ValueError):
            SpecificationConfig(max_memory_mb=0)


class TestProcessingStats:
    """Test ProcessingStats model functionality."""

    def test_processing_stats_defaults(self):
        """Test default processing statistics."""
        stats = ProcessingStats()

        assert stats.files_processed == 0
        assert stats.lines_processed == 0
        assert stats.chunks_created == 0
        assert stats.processing_time_seconds == 0.0
        assert stats.errors_encountered == []

    def test_processing_stats_with_data(self):
        """Test processing statistics with data."""
        errors = ["Error 1", "Error 2"]
        stats = ProcessingStats(
            files_processed=50,
            lines_processed=10000,
            chunks_created=200,
            processing_time_seconds=45.5,
            errors_encountered=errors,
        )

        assert stats.files_processed == 50
        assert stats.lines_processed == 10000
        assert stats.chunks_created == 200
        assert stats.processing_time_seconds == 45.5
        assert stats.errors_encountered == errors


class TestSpecificationOutput:
    """Test SpecificationOutput model functionality."""

    def test_specification_output_creation(self):
        """Test basic SpecificationOutput creation."""
        stats = ProcessingStats(files_processed=10, chunks_created=50)

        output = SpecificationOutput(
            title="Test Specification",
            content="# Test Content",
            language="ja",
            created_at="2024-01-01 12:00:00",
            source_files=[Path("test1.py"), Path("test2.py")],
            processing_stats=stats,
        )

        assert output.title == "Test Specification"
        assert output.content == "# Test Content"
        assert output.language == "ja"
        assert output.created_at == "2024-01-01 12:00:00"
        assert output.source_files == [Path("test1.py"), Path("test2.py")]
        assert output.processing_stats == stats
        assert output.metadata == {}

    def test_specification_output_with_metadata(self):
        """Test SpecificationOutput with metadata."""
        metadata = {"version": "1.0", "generator": "test"}
        output = SpecificationOutput(
            title="Test Specification",
            content="# Test Content",
            language="ja",
            created_at="2024-01-01 12:00:00",
            source_files=[],
            processing_stats=ProcessingStats(),
            metadata=metadata,
        )

        assert output.metadata == metadata


class TestConfigLoader:
    """Test ConfigLoader functionality."""

    def test_config_loader_direct_creation(self):
        """Test creating config directly."""
        config = SpecificationConfig(
            chunk_size=1500,
            chunk_overlap=150,
            supported_languages=[Language.PYTHON, Language.JAVASCRIPT],
            openai_api_key="test-key",
        )

        assert config.chunk_size == 1500
        assert config.chunk_overlap == 150
        assert config.supported_languages == [Language.PYTHON, Language.JAVASCRIPT]
        assert config.openai_api_key == "test-key"

    def test_config_loader_load_from_env(self):
        """Test loading config from environment variables."""
        import os

        # Set test environment variables
        test_env = {
            "CHUNK_SIZE": "1800",
            "PARALLEL_PROCESSES": "6",
            "OPENAI_API_KEY": "env-test-key",
        }

        # Backup original env vars
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)

        try:
            # Set test environment
            for key, value in test_env.items():
                os.environ[key] = value

            config = ConfigLoader.load_from_env()

            assert config.chunk_size == 1800
            assert config.parallel_processes == 6
            assert config.openai_api_key == "env-test-key"

        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_config_loader_invalid_language(self):
        """Test handling of invalid language in config."""
        with pytest.raises(ValueError):
            SpecificationConfig(
                supported_languages=[Language.PYTHON, "invalid_language"]
            )

    def test_config_loader_defaults(self):
        """Test default configuration values."""
        config = SpecificationConfig()

        # Should have default values
        assert config.chunk_size == 4000
        assert config.chunk_overlap == 200
        assert config.supported_languages == [
            Language.PYTHON,
            Language.JAVASCRIPT,
            Language.TYPESCRIPT,
            Language.JAVA,
            Language.CPP,
        ]


# Fixtures for testing
@pytest.fixture
def sample_code_chunk():
    """Create a sample CodeChunk for testing."""
    return CodeChunk(
        content="def hello_world():\n    print('Hello, World!')",
        file_path=Path("hello.py"),
        start_line=1,
        end_line=2,
        language=Language.PYTHON,
        chunk_type="function",
    )


@pytest.fixture
def sample_semantic_change():
    """Create a sample SemanticChange for testing."""
    return SemanticChange(
        element_name="hello_world",
        element_type="function",
        change_type="added",
        file_path=Path("hello.py"),
        impact_score=3.0,
    )


@pytest.fixture
def sample_config():
    """Create a sample SpecificationConfig for testing."""
    return SpecificationConfig(
        chunk_size=1000,
        supported_languages=[Language.PYTHON],
        openai_api_key="test-key-123",
    )


@pytest.fixture
def sample_processing_stats():
    """Create sample ProcessingStats for testing."""
    return ProcessingStats(
        files_processed=5,
        lines_processed=500,
        chunks_created=25,
        processing_time_seconds=10.5,
    )


# Integration test using multiple fixtures
def test_complete_workflow_models(
    sample_code_chunk, sample_semantic_change, sample_config, sample_processing_stats
):
    """Test a complete workflow using all model types."""
    # Create specification output
    output = SpecificationOutput(
        title="Integration Test Spec",
        content="# Generated from test data",
        language="ja",
        created_at="2024-01-01 00:00:00",
        source_files=[sample_code_chunk.file_path],
        processing_stats=sample_processing_stats,
        metadata={"test": True},
    )

    # Verify all components work together
    assert output.title == "Integration Test Spec"
    assert output.source_files == [Path("hello.py")]
    assert output.processing_stats.files_processed == 5
    assert output.metadata["test"] == True

    # Test serialization of complex objects
    chunk_dict = sample_code_chunk.model_dump()
    change_dict = sample_semantic_change.model_dump()
    config_dict = sample_config.model_dump()

    assert chunk_dict["language"] == Language.PYTHON
    assert change_dict["change_type"] == "added"
    assert config_dict["chunk_size"] == 1000
