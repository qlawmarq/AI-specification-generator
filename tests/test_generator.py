"""
Unit tests for spec_generator.core.generator module.

Tests for SpecificationGenerator, LLMProvider, and AnalysisProcessor functionality.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from spec_generator.core.generator import (
    AnalysisProcessor,
    LLMProvider,
    SpecificationGenerator,
)
from spec_generator.models import (
    CodeChunk,
    Language,
    SpecificationConfig,
    SpecificationOutput,
)


class TestLLMProvider:
    """Test LLMProvider functionality."""

    def test_llm_provider_initialization_openai(self):
        """Test LLMProvider initialization with OpenAI."""
        config = SpecificationConfig(openai_api_key="test-key")

        with patch('spec_generator.core.generator.ChatOpenAI') as mock_chat_openai:
            mock_llm = Mock()
            mock_chat_openai.return_value = mock_llm

            provider = LLMProvider(config)

            assert provider.config == config
            assert provider.llm == mock_llm
            assert provider.request_count == 0
            assert provider.last_request_time == 0.0

            # Verify ChatOpenAI was called with correct parameters
            mock_chat_openai.assert_called_once()
            call_args = mock_chat_openai.call_args
            assert call_args[1]['model'] == "gpt-4"
            assert call_args[1]['temperature'] == 0.3
            assert call_args[1]['openai_api_key'] == "test-key"

    def test_llm_provider_initialization_azure(self):
        """Test LLMProvider initialization with Azure OpenAI."""
        config = SpecificationConfig(
            azure_openai_endpoint="https://test.azure.com",
            azure_openai_key="azure-key",
            azure_openai_version="2023-05-15"
        )

        with patch('spec_generator.core.generator.ChatOpenAI') as mock_chat_openai:
            mock_llm = Mock()
            mock_chat_openai.return_value = mock_llm

            LLMProvider(config)

            # Verify Azure configuration
            call_args = mock_chat_openai.call_args
            assert call_args[1]['azure_endpoint'] == "https://test.azure.com"
            assert call_args[1]['openai_api_key'] == "azure-key"
            assert call_args[1]['openai_api_version'] == "2023-05-15"

    def test_llm_provider_no_api_key(self):
        """Test LLMProvider raises error with no API configuration."""
        config = SpecificationConfig()  # No API keys

        with pytest.raises(ValueError, match="No valid OpenAI configuration found"):
            LLMProvider(config)

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Test successful LLM generation."""
        config = SpecificationConfig(openai_api_key="test-key")

        with patch('spec_generator.core.generator.ChatOpenAI') as mock_chat_openai:
            mock_llm = Mock()
            mock_llm.invoke.return_value = "Generated response"
            mock_chat_openai.return_value = mock_llm

            provider = LLMProvider(config)

            with patch('asyncio.get_event_loop') as mock_get_loop:
                mock_loop = Mock()
                mock_loop.run_in_executor.return_value = asyncio.Future()
                mock_loop.run_in_executor.return_value.set_result("Generated response")
                mock_get_loop.return_value = mock_loop

                result = await provider.generate("Test prompt")

                assert result == "Generated response"
                assert provider.request_count == 1

    @pytest.mark.asyncio
    async def test_generate_with_rate_limiting(self):
        """Test generation with rate limiting."""
        config = SpecificationConfig(openai_api_key="test-key")
        config.performance_settings.rate_limit_rpm = 60  # 1 request per second

        with patch('spec_generator.core.generator.ChatOpenAI') as mock_chat_openai:
            mock_llm = Mock()
            mock_llm.invoke.return_value = "Generated response"
            mock_chat_openai.return_value = mock_llm

            provider = LLMProvider(config)

            with patch('asyncio.get_event_loop') as mock_get_loop, \
                 patch('asyncio.sleep') as mock_sleep, \
                 patch('time.time') as mock_time:

                mock_loop = Mock()
                mock_loop.run_in_executor.return_value = asyncio.Future()
                mock_loop.run_in_executor.return_value.set_result("Generated response")
                mock_get_loop.return_value = mock_loop

                # Mock time to simulate quick successive calls
                mock_time.side_effect = [0.0, 0.5, 1.0]  # Second call too soon

                # First call
                await provider.generate("Test prompt 1")

                # Second call should trigger rate limiting
                await provider.generate("Test prompt 2")

                # Should have slept to respect rate limit
                mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_generate_error_handling(self):
        """Test error handling in generation."""
        config = SpecificationConfig(openai_api_key="test-key")

        with patch('spec_generator.core.generator.ChatOpenAI') as mock_chat_openai:
            mock_llm = Mock()
            mock_llm.invoke.side_effect = Exception("API Error")
            mock_chat_openai.return_value = mock_llm

            provider = LLMProvider(config)

            with patch('asyncio.get_event_loop') as mock_get_loop:
                mock_loop = Mock()
                mock_loop.run_in_executor.return_value = asyncio.Future()
                mock_loop.run_in_executor.return_value.set_exception(Exception("API Error"))
                mock_get_loop.return_value = mock_loop

                with pytest.raises(Exception, match="API Error"):
                    await provider.generate("Test prompt")


class TestAnalysisProcessor:
    """Test AnalysisProcessor functionality."""

    def test_analysis_processor_initialization(self):
        """Test AnalysisProcessor initialization."""
        SpecificationConfig(openai_api_key="test-key")

        with patch('spec_generator.core.generator.LLMProvider') as mock_llm_provider:
            mock_provider = Mock()
            mock_llm_provider.return_value = mock_provider

            processor = AnalysisProcessor(mock_provider)

            assert processor.llm_provider == mock_provider
            assert processor.prompt_templates is not None

    @pytest.mark.asyncio
    async def test_analyze_code_chunk_success(self):
        """Test successful code chunk analysis."""
        mock_llm_provider = Mock()
        mock_llm_provider.generate.return_value = asyncio.Future()
        mock_llm_provider.generate.return_value.set_result(json.dumps({
            "overview": "Test function",
            "functions": [{"name": "test_func", "purpose": "Testing"}],
            "classes": [],
            "dependencies": [],
            "data_flow": "Simple flow",
            "error_handling": "Basic error handling"
        }))

        processor = AnalysisProcessor(mock_llm_provider)

        chunk = CodeChunk(
            content="def test_func(): pass",
            file_path=Path("test.py"),
            start_line=1,
            end_line=1,
            language=Language.PYTHON
        )

        result = await processor.analyze_code_chunk(chunk)

        assert result["overview"] == "Test function"
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "test_func"

    @pytest.mark.asyncio
    async def test_analyze_code_chunk_json_parse_error(self):
        """Test handling of JSON parse error in analysis."""
        mock_llm_provider = Mock()
        mock_llm_provider.generate.return_value = asyncio.Future()
        mock_llm_provider.generate.return_value.set_result("Invalid JSON response")

        processor = AnalysisProcessor(mock_llm_provider)

        chunk = CodeChunk(
            content="def test_func(): pass",
            file_path=Path("test.py"),
            start_line=1,
            end_line=1,
            language=Language.PYTHON
        )

        result = await processor.analyze_code_chunk(chunk)

        # Should return fallback structure
        assert "overview" in result
        assert result["overview"] == "Invalid JSON response"
        assert result["functions"] == []
        assert result["classes"] == []

    @pytest.mark.asyncio
    async def test_analyze_code_chunk_exception(self):
        """Test handling of exception during analysis."""
        mock_llm_provider = Mock()
        mock_llm_provider.generate.side_effect = Exception("Analysis failed")

        processor = AnalysisProcessor(mock_llm_provider)

        chunk = CodeChunk(
            content="def test_func(): pass",
            file_path=Path("test.py"),
            start_line=1,
            end_line=1,
            language=Language.PYTHON
        )

        result = await processor.analyze_code_chunk(chunk)

        # Should return error structure
        assert "overview" in result
        assert "Analysis failed" in result["overview"]
        assert result["functions"] == []

    @pytest.mark.asyncio
    async def test_combine_analyses(self):
        """Test combining multiple analysis results."""
        mock_llm_provider = Mock()
        processor = AnalysisProcessor(mock_llm_provider)

        analyses = [
            {
                "overview": "Module 1 overview",
                "functions": [{"name": "func1", "purpose": "Function 1"}],
                "classes": [{"name": "Class1", "purpose": "Class 1"}],
                "dependencies": [{"name": "dep1", "type": "internal"}]
            },
            {
                "overview": "Module 2 overview",
                "functions": [{"name": "func2", "purpose": "Function 2"}],
                "classes": [],
                "dependencies": [{"name": "dep2", "type": "external"}]
            }
        ]

        result = await processor.combine_analyses(analyses)

        assert "overview" in result
        assert "modules" in result
        assert len(result["functions"]) == 2
        assert len(result["classes"]) == 1
        assert len(result["dependencies"]) == 2

    def test_extract_module_name(self):
        """Test module name extraction from analysis."""
        mock_llm_provider = Mock()
        processor = AnalysisProcessor(mock_llm_provider)

        analysis_with_module = {"overview": "This is a utility module for processing"}
        name = processor._extract_module_name(analysis_with_module)
        assert name == "extracted_module"

        analysis_without_module = {"overview": "Simple function"}
        name = processor._extract_module_name(analysis_without_module)
        assert name == "general_module"

    def test_combine_module_analyses(self):
        """Test combining analyses for a single module."""
        mock_llm_provider = Mock()
        processor = AnalysisProcessor(mock_llm_provider)

        module_analyses = [
            {
                "overview": "File 1 overview",
                "functions": [{"name": "func1"}],
                "classes": [{"name": "Class1"}],
                "dependencies": [{"name": "dep1"}]
            },
            {
                "overview": "File 2 overview",
                "functions": [{"name": "func2"}],
                "classes": [],
                "dependencies": [{"name": "dep2"}]
            }
        ]

        result = processor._combine_module_analyses(module_analyses)

        assert "purpose" in result
        assert "File 1 overview File 2 overview" == result["purpose"]
        assert len(result["functions"]) == 2
        assert len(result["classes"]) == 1
        assert len(result["dependencies"]) == 2
        assert result["complexity"] == "low"  # 2 functions + 1 class = 3 elements

    def test_create_combined_overview(self):
        """Test creating combined system overview."""
        mock_llm_provider = Mock()
        processor = AnalysisProcessor(mock_llm_provider)

        combined = {
            "modules": {"mod1": {}, "mod2": {}},
            "functions": [{"name": "func1"}, {"name": "func2"}, {"name": "func3"}],
            "classes": [{"name": "Class1"}]
        }

        overview = processor._create_combined_overview(combined)

        assert "2個のモジュール" in overview
        assert "3個の関数" in overview
        assert "1個のクラス" in overview


class TestSpecificationGenerator:
    """Test SpecificationGenerator functionality."""

    def test_specification_generator_initialization(self):
        """Test SpecificationGenerator initialization."""
        config = SpecificationConfig(openai_api_key="test-key")

        with patch('spec_generator.core.generator.LLMProvider') as mock_llm_provider, \
             patch('spec_generator.core.generator.AnalysisProcessor') as mock_analysis_processor:

            mock_provider = Mock()
            mock_processor = Mock()
            mock_llm_provider.return_value = mock_provider
            mock_analysis_processor.return_value = mock_processor

            generator = SpecificationGenerator(config)

            assert generator.config == config
            assert generator.llm_provider == mock_provider
            assert generator.analysis_processor == mock_processor
            assert generator.spec_template is not None

    @pytest.mark.asyncio
    async def test_generate_specification_success(self):
        """Test successful specification generation."""
        config = SpecificationConfig(openai_api_key="test-key")

        with patch('spec_generator.core.generator.LLMProvider') as mock_llm_provider, \
             patch('spec_generator.core.generator.AnalysisProcessor') as mock_analysis_processor:

            mock_provider = Mock()
            mock_processor = Mock()
            mock_llm_provider.return_value = mock_provider
            mock_analysis_processor.return_value = mock_processor

            # Mock analysis results
            mock_processor.combine_analyses.return_value = asyncio.Future()
            mock_processor.combine_analyses.return_value.set_result({
                "overview": "System overview",
                "modules": {"main": {"purpose": "Main module"}},
                "functions": [{"name": "main_func"}],
                "classes": []
            })

            # Mock LLM generation
            mock_provider.generate.return_value = asyncio.Future()
            mock_provider.generate.return_value.set_result("# Generated Specification\n\nThis is a test specification.")

            generator = SpecificationGenerator(config)

            # Mock _analyze_chunks to return analysis results
            with patch.object(generator, '_analyze_chunks') as mock_analyze:
                mock_analyze.return_value = [{"overview": "Analysis 1"}]

                chunks = [
                    CodeChunk(
                        content="def test(): pass",
                        file_path=Path("test.py"),
                        start_line=1,
                        end_line=1,
                        language=Language.PYTHON
                    )
                ]

                result = await generator.generate_specification(chunks, "Test Project")

                assert isinstance(result, SpecificationOutput)
                assert result.title == "Test Project 詳細設計書"
                assert "Generated Specification" in result.content
                assert result.language == "ja"
                assert len(result.source_files) == 1

    @pytest.mark.asyncio
    async def test_generate_specification_with_output_path(self):
        """Test specification generation with output file saving."""
        config = SpecificationConfig(openai_api_key="test-key")

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            output_path = Path(f.name)

        try:
            with patch('spec_generator.core.generator.LLMProvider') as mock_llm_provider, \
                 patch('spec_generator.core.generator.AnalysisProcessor') as mock_analysis_processor:

                mock_provider = Mock()
                mock_processor = Mock()
                mock_llm_provider.return_value = mock_provider
                mock_analysis_processor.return_value = mock_processor

                # Setup mocks
                mock_processor.combine_analyses.return_value = asyncio.Future()
                mock_processor.combine_analyses.return_value.set_result({"overview": "Test"})

                mock_provider.generate.return_value = asyncio.Future()
                mock_provider.generate.return_value.set_result("# Test Specification")

                generator = SpecificationGenerator(config)

                with patch.object(generator, '_analyze_chunks') as mock_analyze:
                    mock_analyze.return_value = [{"overview": "Analysis"}]

                    chunks = [
                        CodeChunk(
                            content="def test(): pass",
                            file_path=Path("test.py"),
                            start_line=1,
                            end_line=1,
                            language=Language.PYTHON
                        )
                    ]

                    await generator.generate_specification(
                        chunks, "Test Project", output_path
                    )

                    # Should save the file
                    assert output_path.exists()
                    content = output_path.read_text(encoding='utf-8')
                    assert "Test Specification" in content

                    # Note: metadata.json files are no longer generated (refactored to use logging)

        finally:
            if output_path.exists():
                output_path.unlink()

    @pytest.mark.asyncio
    async def test_analyze_chunks_in_batches(self):
        """Test analyzing chunks in batches."""
        config = SpecificationConfig(openai_api_key="test-key")
        config.performance_settings.batch_size = 2

        with patch('spec_generator.core.generator.LLMProvider') as mock_llm_provider, \
             patch('spec_generator.core.generator.AnalysisProcessor') as mock_analysis_processor:

            mock_provider = Mock()
            mock_processor = Mock()
            mock_llm_provider.return_value = mock_provider
            mock_analysis_processor.return_value = mock_processor

            generator = SpecificationGenerator(config)

            # Mock individual chunk analysis
            async def mock_analyze_chunk(chunk):
                return {"overview": f"Analysis for {chunk.file_path.name}"}

            mock_processor.analyze_code_chunk = mock_analyze_chunk

            chunks = [
                CodeChunk(content="def test1(): pass", file_path=Path("test1.py"),
                         start_line=1, end_line=1, language=Language.PYTHON),
                CodeChunk(content="def test2(): pass", file_path=Path("test2.py"),
                         start_line=1, end_line=1, language=Language.PYTHON),
                CodeChunk(content="def test3(): pass", file_path=Path("test3.py"),
                         start_line=1, end_line=1, language=Language.PYTHON)
            ]

            analyses = await generator._analyze_chunks(chunks)

            assert len(analyses) == 3
            assert all("Analysis for" in analysis["overview"] for analysis in analyses)

    @pytest.mark.asyncio
    async def test_generate_specification_fallback(self):
        """Test fallback document generation when LLM fails."""
        config = SpecificationConfig(openai_api_key="test-key")

        with patch('spec_generator.core.generator.LLMProvider') as mock_llm_provider, \
             patch('spec_generator.core.generator.AnalysisProcessor') as mock_analysis_processor:

            mock_provider = Mock()
            mock_processor = Mock()
            mock_llm_provider.return_value = mock_provider
            mock_analysis_processor.return_value = mock_processor

            # Mock analysis results
            mock_processor.combine_analyses.return_value = asyncio.Future()
            mock_processor.combine_analyses.return_value.set_result({
                "overview": "System overview",
                "modules": {"main": {"purpose": "Main module"}},
                "functions": [],
                "classes": []
            })

            # Mock LLM generation to fail
            mock_provider.generate.side_effect = Exception("LLM generation failed")

            generator = SpecificationGenerator(config)

            with patch.object(generator, '_analyze_chunks') as mock_analyze:
                mock_analyze.return_value = [{"overview": "Analysis"}]

                chunks = [
                    CodeChunk(
                        content="def test(): pass",
                        file_path=Path("test.py"),
                        start_line=1,
                        end_line=1,
                        language=Language.PYTHON
                    )
                ]

                result = await generator.generate_specification(chunks, "Test Project")

                # Should generate fallback document
                assert isinstance(result, SpecificationOutput)
                assert "詳細設計書" in result.content
                assert "System overview" in result.content

    @pytest.mark.asyncio
    async def test_update_specification(self):
        """Test updating existing specification."""
        config = SpecificationConfig(openai_api_key="test-key")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Existing Specification\n\nThis is the existing content.")
            existing_spec_path = Path(f.name)

        try:
            with patch('spec_generator.core.generator.LLMProvider') as mock_llm_provider:
                mock_provider = Mock()
                mock_llm_provider.return_value = mock_provider

                # Mock LLM generation for update
                mock_provider.generate.return_value = asyncio.Future()
                mock_provider.generate.return_value.set_result("# Updated Specification\n\nThis is the updated content.")

                generator = SpecificationGenerator(config)

                changes = [
                    {"element_name": "new_function", "change_type": "added", "impact_score": 5.0}
                ]

                result = await generator.update_specification(
                    existing_spec_path, changes
                )

                assert isinstance(result, SpecificationOutput)
                assert result.title == "更新された仕様書"
                assert "Updated Specification" in result.content
                assert result.metadata["update_type"] == "incremental"
                assert result.metadata["change_count"] == 1

        finally:
            existing_spec_path.unlink()

    def test_create_change_summary(self):
        """Test creating change summary for updates."""
        config = SpecificationConfig(openai_api_key="test-key")

        with patch('spec_generator.core.generator.LLMProvider'):
            generator = SpecificationGenerator(config)

            changes = [
                {"change_type": "added", "element_name": "func1"},
                {"change_type": "added", "element_name": "func2"},
                {"change_type": "modified", "element_name": "func3"},
                {"change_type": "removed", "element_name": "func4"}
            ]

            summary = generator._create_change_summary(changes)

            assert "added: 2件" in summary
            assert "modified: 1件" in summary
            assert "removed: 1件" in summary

    def test_calculate_language_distribution(self):
        """Test calculating language distribution from chunks."""
        config = SpecificationConfig(openai_api_key="test-key")

        with patch('spec_generator.core.generator.LLMProvider'):
            generator = SpecificationGenerator(config)

            chunks = [
                CodeChunk(content="def test1(): pass", file_path=Path("test1.py"),
                         start_line=1, end_line=1, language=Language.PYTHON),
                CodeChunk(content="def test2(): pass", file_path=Path("test2.py"),
                         start_line=1, end_line=1, language=Language.PYTHON),
                CodeChunk(content="function test() {}", file_path=Path("test.js"),
                         start_line=1, end_line=1, language=Language.JAVASCRIPT)
            ]

            distribution = generator._calculate_language_distribution(chunks)

            assert distribution["python"] == 2
            assert distribution["javascript"] == 1


# Fixtures
@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return SpecificationConfig(
        openai_api_key="test-key-123",
        chunk_size=1000,
        supported_languages=[Language.PYTHON, Language.JAVASCRIPT]
    )


@pytest.fixture
def sample_chunks():
    """Create sample code chunks for testing."""
    return [
        CodeChunk(
            content="def hello_world():\n    print('Hello, World!')",
            file_path=Path("hello.py"),
            start_line=1,
            end_line=2,
            language=Language.PYTHON,
            metadata={"function_count": 1}
        ),
        CodeChunk(
            content="class Calculator:\n    def add(self, x, y):\n        return x + y",
            file_path=Path("calc.py"),
            start_line=3,
            end_line=5,
            language=Language.PYTHON,
            metadata={"class_count": 1, "method_count": 1}
        ),
        CodeChunk(
            content="function greet(name) {\n    return `Hello, ${name}!`;\n}",
            file_path=Path("greet.js"),
            start_line=1,
            end_line=3,
            language=Language.JAVASCRIPT,
            metadata={"function_count": 1}
        )
    ]


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider for testing."""
    mock_provider = Mock()
    mock_provider.generate = AsyncMock()
    mock_provider.request_count = 0
    return mock_provider


@pytest.mark.asyncio
async def test_integration_full_specification_generation(sample_config, sample_chunks, mock_llm_provider):
    """Integration test for complete specification generation workflow."""

    # Mock the analysis results
    analysis_results = [
        {
            "overview": "Hello world function implementation",
            "functions": [{"name": "hello_world", "purpose": "Prints greeting"}],
            "classes": [],
            "dependencies": [],
            "data_flow": "Simple output flow",
            "error_handling": "None"
        },
        {
            "overview": "Calculator class for arithmetic operations",
            "functions": [],
            "classes": [{"name": "Calculator", "purpose": "Mathematical operations"}],
            "dependencies": [],
            "data_flow": "Input parameters to return value",
            "error_handling": "Basic validation"
        },
        {
            "overview": "JavaScript greeting function",
            "functions": [{"name": "greet", "purpose": "Generate personalized greeting"}],
            "classes": [],
            "dependencies": [],
            "data_flow": "String interpolation",
            "error_handling": "None"
        }
    ]

    # Mock combined analysis
    combined_analysis = {
        "overview": "Multi-language application with Python backend and JavaScript frontend",
        "modules": {
            "hello_module": {"purpose": "Greeting functionality"},
            "calc_module": {"purpose": "Mathematical operations"},
            "greet_module": {"purpose": "Frontend greeting"}
        },
        "functions": [
            {"name": "hello_world", "purpose": "Prints greeting"},
            {"name": "greet", "purpose": "Generate personalized greeting"}
        ],
        "classes": [
            {"name": "Calculator", "purpose": "Mathematical operations"}
        ],
        "dependencies": []
    }

    # Mock final specification content
    spec_content = """# Test System 詳細設計書

## 1. 概要

### 1.1 システム概要
Multi-language application with Python backend and JavaScript frontend

### 1.2 主要機能
- hello_world: Prints greeting
- Calculator: Mathematical operations
- greet: Generate personalized greeting

## 2. システム構成

### 2.1 モジュール設計

#### hello_module
- 目的: Greeting functionality

#### calc_module
- 目的: Mathematical operations

#### greet_module
- 目的: Frontend greeting

## 3. 詳細設計

### 3.1 関数設計

#### hello_world
- 目的: Prints greeting
- 言語: Python

#### greet
- 目的: Generate personalized greeting
- 言語: JavaScript

### 3.2 クラス設計

#### Calculator
- 目的: Mathematical operations
- 言語: Python
"""

    with patch('spec_generator.core.generator.LLMProvider') as mock_llm_provider_class, \
         patch('spec_generator.core.generator.AnalysisProcessor') as mock_analysis_processor_class:

        # Setup analysis processor mock
        mock_processor = Mock()
        mock_processor.analyze_code_chunk = AsyncMock()
        mock_processor.analyze_code_chunk.side_effect = analysis_results
        mock_processor.combine_analyses = AsyncMock()
        mock_processor.combine_analyses.return_value = combined_analysis
        mock_analysis_processor_class.return_value = mock_processor

        # Setup LLM provider mock
        mock_provider = Mock()
        mock_provider.generate = AsyncMock()
        mock_provider.generate.return_value = spec_content
        mock_llm_provider_class.return_value = mock_provider

        # Create generator and run
        generator = SpecificationGenerator(sample_config)
        result = await generator.generate_specification(
            sample_chunks, "Test System"
        )

        # Verify results
        assert isinstance(result, SpecificationOutput)
        assert result.title == "Test System 詳細設計書"
        assert "Multi-language application" in result.content
        assert result.language == "ja"
        assert len(result.source_files) == 3

        # Verify processing stats
        stats = result.processing_stats
        assert stats.files_processed == 3  # 3 unique files
        assert stats.lines_processed == 8   # Total lines across all chunks
        assert stats.chunks_created == 3    # Number of analysis results

        # Verify metadata
        metadata = result.metadata
        assert metadata["chunk_count"] == 3
        assert "python" in metadata["language_distribution"]
        assert "javascript" in metadata["language_distribution"]
        assert metadata["language_distribution"]["python"] == 2
        assert metadata["language_distribution"]["javascript"] == 1

        # Verify analysis processor was called correctly
        assert mock_processor.analyze_code_chunk.call_count == 3
        mock_processor.combine_analyses.assert_called_once()

        # Verify LLM provider was called for final generation
        mock_provider.generate.assert_called_once()


def test_processing_stats_calculation():
    """Test processing statistics calculation."""
    config = SpecificationConfig(openai_api_key="test-key")

    with patch('spec_generator.core.generator.LLMProvider'):
        generator = SpecificationGenerator(config)

        chunks = [
            CodeChunk(content="line1\nline2", file_path=Path("file1.py"),
                     start_line=1, end_line=2, language=Language.PYTHON),
            CodeChunk(content="line3\nline4\nline5", file_path=Path("file2.py"),
                     start_line=1, end_line=3, language=Language.PYTHON),
            CodeChunk(content="line6", file_path=Path("file1.py"),  # Same file as first
                     start_line=3, end_line=3, language=Language.PYTHON)
        ]

        # Create a mock result to test stats calculation
        import time
        start_time = time.time() - 5.0  # Simulate 5 second processing

        result = generator._create_specification_output(
            "# Test Spec", chunks, "Test", start_time
        )

        stats = result.processing_stats
        assert stats.files_processed == 2  # 2 unique files
        assert stats.lines_processed == 6  # Total lines: 2+3+1
        assert stats.processing_time_seconds >= 4.9  # Should be around 5 seconds

        # Test language distribution
        lang_dist = result.metadata["language_distribution"]
        assert lang_dist["python"] == 3  # All chunks are Python
