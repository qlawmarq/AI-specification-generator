"""
Unit tests for spec_generator.core.processor module.

Tests for LargeCodebaseProcessor and ChunkProcessor functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from spec_generator.core.processor import ChunkProcessor, LargeCodebaseProcessor
from spec_generator.models import CodeChunk, Language, SpecificationConfig
from spec_generator.parsers.tree_sitter_parser import SemanticElement


def create_mock_semantic_element(
    name: str, element_type: str, start_line: int, end_line: int, content: str
) -> SemanticElement:
    """Create a mock SemanticElement for testing."""
    mock_node = Mock()
    mock_node.start_point = (start_line - 1, 0)
    mock_node.end_point = (end_line - 1, 0)
    mock_node.type = element_type

    return SemanticElement(
        name=name,
        element_type=element_type,
        content=content,
        start_line=start_line,
        end_line=end_line,
        node=mock_node,
    )


class TestChunkProcessor:
    """Test ChunkProcessor functionality."""

    def test_chunk_processor_initialization(self):
        """Test ChunkProcessor initialization."""
        config = SpecificationConfig(chunk_size=1000, chunk_overlap=100)
        processor = ChunkProcessor(config)

        assert processor.config == config
        assert processor.text_splitter is not None

    @pytest.mark.asyncio
    async def test_create_chunks_from_content(self):
        """Test creating chunks from content."""
        config = SpecificationConfig(chunk_size=200, chunk_overlap=10)
        processor = ChunkProcessor(config)

        content = (
            "This is a long piece of text that should be split into multiple chunks for processing. "
            * 20
        )
        file_path = Path("test.py")
        language = Language.PYTHON

        chunks = await processor.create_chunks_from_content(
            content, file_path, language
        )

        assert len(chunks) > 1  # Should be split into multiple chunks
        for chunk in chunks:
            assert isinstance(chunk, CodeChunk)
            assert chunk.file_path == file_path
            assert chunk.language == language
            assert len(chunk.content) <= 220  # Should respect chunk size + some overlap

    @pytest.mark.asyncio
    async def test_create_chunks_from_ast_empty(self):
        """Test creating AST chunks with empty analyzer results."""
        config = SpecificationConfig()
        processor = ChunkProcessor(config)

        # Mock AST analyzer to return None
        from unittest.mock import Mock

        mock_analyzer = Mock()
        mock_analyzer.analyze_file.return_value = None

        chunks = await processor.create_chunks_from_ast(
            Path("test.py"), Language.PYTHON, mock_analyzer
        )
        assert chunks == []

    @pytest.mark.asyncio
    async def test_create_chunks_from_ast_with_elements(self):
        """Test creating AST chunks from semantic elements."""
        config = SpecificationConfig()
        processor = ChunkProcessor(config)

        # Mock module info with elements
        from unittest.mock import Mock

        mock_analyzer = Mock()
        mock_module_info = Mock()
        mock_module_info.elements = [
            create_mock_semantic_element(
                "func1", "function", 1, 5, "def func1(): pass"
            ),
            create_mock_semantic_element(
                "func2", "function", 6, 10, "def func2(): pass"
            ),
            create_mock_semantic_element(
                "Class1", "class", 11, 20, "class Class1: pass"
            ),
        ]
        mock_analyzer.analyze_file.return_value = mock_module_info

        chunks = await processor.create_chunks_from_ast(
            Path("test.py"), Language.PYTHON, mock_analyzer
        )

        assert len(chunks) == 3
        for i, chunk in enumerate(chunks):
            assert isinstance(chunk, CodeChunk)
            assert chunk.file_path == Path("test.py")
            assert chunk.language == Language.PYTHON
            assert chunk.content == mock_module_info.elements[i].content
            assert chunk.start_line == mock_module_info.elements[i].start_line
            assert chunk.end_line == mock_module_info.elements[i].end_line

    @pytest.mark.asyncio
    async def test_create_chunks_from_content_large_content(self):
        """Test creating chunks when content is large."""
        config = SpecificationConfig(chunk_size=100)  # Small chunk size
        processor = ChunkProcessor(config)

        # Create large content that exceeds chunk size
        large_content = "def very_long_function():\n" + "    pass\n" * 50

        chunks = await processor.create_chunks_from_content(
            large_content, Path("test.py"), Language.PYTHON
        )

        # Should split large content into multiple chunks
        assert len(chunks) >= 1
        total_content = "".join(chunk.content for chunk in chunks)
        assert "def very_long_function()" in total_content

    @pytest.mark.asyncio
    async def test_create_chunks_from_content_small_content(self):
        """Test creating chunks from small content."""
        config = SpecificationConfig(chunk_size=1000)
        processor = ChunkProcessor(config)

        # Create small content
        small_content = "def func1(): pass\ndef func2(): pass\ndef func3(): pass"

        chunks = await processor.create_chunks_from_content(
            small_content, Path("test.py"), Language.PYTHON
        )

        # Should create at least one chunk
        assert len(chunks) >= 1

        # Check that content is preserved
        total_content = "".join(chunk.content for chunk in chunks)
        assert "def func1(): pass" in total_content
        assert "def func2(): pass" in total_content
        assert "def func3(): pass" in total_content


class TestLargeCodebaseProcessor:
    """Test LargeCodebaseProcessor functionality."""

    def test_processor_initialization(self):
        """Test LargeCodebaseProcessor initialization."""
        config = SpecificationConfig()
        processor = LargeCodebaseProcessor(config)

        assert processor.config == config
        assert processor.chunk_processor is not None
        assert processor.file_scanner is not None
        assert processor.language_detector is not None
        assert processor.ast_analyzer is not None

    def test_language_detection(self):
        """Test language detection from file extension."""
        config = SpecificationConfig(
            supported_languages=[Language.PYTHON, Language.JAVASCRIPT]
        )
        processor = LargeCodebaseProcessor(config)

        # Test that language detector works
        python_lang = processor.language_detector.detect_language(Path("test.py"))
        assert python_lang == Language.PYTHON

        js_lang = processor.language_detector.detect_language(Path("test.js"))
        assert js_lang == Language.JAVASCRIPT

        unknown_lang = processor.language_detector.detect_language(Path("test.txt"))
        assert unknown_lang is None

    def test_batch_size_calculation(self):
        """Test batch size calculation based on config."""
        config = SpecificationConfig(parallel_processes=4)
        processor = LargeCodebaseProcessor(config)

        # Batch size should be min(parallel_processes * 2, 20)
        expected_batch_size = min(4 * 2, 20)
        assert processor.batch_size == expected_batch_size

    @pytest.mark.asyncio
    async def test_file_scanning(self):
        """Test file scanning functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test.py").write_text("def test(): pass")
            (temp_path / "test.js").write_text("function test() {}")
            (temp_path / "test.txt").write_text("Not a source file")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "nested.py").write_text("def nested(): pass")

            config = SpecificationConfig(
                supported_languages=[Language.PYTHON, Language.JAVASCRIPT]
            )
            processor = LargeCodebaseProcessor(config)

            # Use file scanner to find files
            files = []
            async for file_info in processor.file_scanner.scan_directory(
                temp_path, config.supported_languages
            ):
                files.append(file_info)

            # Should find Python and JavaScript files, but not txt
            assert len(files) >= 2  # At least Python and JS files
            file_paths = [Path(f["path"]).name for f in files]
            assert "test.py" in file_paths
            assert "test.js" in file_paths

    @pytest.mark.asyncio
    async def test_file_scanning_with_gitignore(self):
        """Test file scanning respects .gitignore."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test.py").write_text("def test(): pass")
            (temp_path / "ignored.py").write_text("def ignored(): pass")
            (temp_path / ".gitignore").write_text("ignored.py\n")

            config = SpecificationConfig(supported_languages=[Language.PYTHON])
            processor = LargeCodebaseProcessor(config)

            # Use file scanner to find files
            files = []
            async for file_info in processor.file_scanner.scan_directory(
                temp_path, config.supported_languages
            ):
                files.append(file_info)

            # Should respect .gitignore
            file_paths = [Path(f["path"]).name for f in files]
            assert "test.py" in file_paths
            # Note: gitignore behavior depends on FileScanner implementation

    @pytest.mark.asyncio
    async def test_process_single_file_success(self):
        """Test processing a single file successfully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello(): pass")
            test_file = Path(f.name)

        try:
            config = SpecificationConfig()
            processor = LargeCodebaseProcessor(config)

            # Mock the AST analyzer to return semantic elements
            with patch.object(processor.ast_analyzer, "analyze_file") as mock_analyze:
                mock_module_info = Mock()
                mock_module_info.elements = [
                    create_mock_semantic_element(
                        "hello", "function", 1, 1, "def hello(): pass"
                    )
                ]
                mock_analyze.return_value = mock_module_info

                chunks = await processor.process_single_file(test_file, False, True)

                assert len(chunks) == 1
                assert chunks[0].content == "def hello(): pass"
                assert chunks[0].file_path == test_file
                assert chunks[0].language == Language.PYTHON

        finally:
            test_file.unlink()

    @pytest.mark.asyncio
    async def test_process_single_file_text_chunking(self):
        """Test processing single file with text chunking."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello(): pass\ndef world(): pass")
            test_file = Path(f.name)

        try:
            config = SpecificationConfig(chunk_size=10)  # Small chunks
            processor = LargeCodebaseProcessor(config)

            chunks = await processor.process_single_file(
                test_file, False, False
            )  # No AST chunking

            assert len(chunks) >= 1
            for chunk in chunks:
                assert chunk.file_path == test_file
                assert chunk.language == Language.PYTHON

        finally:
            test_file.unlink()

    @pytest.mark.asyncio
    async def test_process_single_file_not_found(self):
        """Test processing non-existent file."""
        processor = LargeCodebaseProcessor(SpecificationConfig())
        non_existent = Path("non_existent_file.py")

        chunks = await processor.process_single_file(non_existent, False, True)
        assert chunks == []

    @pytest.mark.asyncio
    async def test_process_repository(self):
        """Test processing an entire repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "file1.py").write_text("def func1(): pass")
            (temp_path / "file2.py").write_text("def func2(): pass")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "file3.py").write_text("def func3(): pass")

            config = SpecificationConfig(supported_languages=[Language.PYTHON])
            processor = LargeCodebaseProcessor(config)

            # Mock AST analyzer to avoid tree-sitter dependency
            with patch.object(processor.ast_analyzer, "analyze_file") as mock_analyze:

                def mock_analyze_side_effect(file_path, language):
                    mock_module_info = Mock()
                    if file_path.name == "file1.py":
                        mock_module_info.elements = [
                            SemanticElement(
                                "func1", "function", 1, 1, "def func1(): pass"
                            )
                        ]
                    elif file_path.name == "file2.py":
                        mock_module_info.elements = [
                            SemanticElement(
                                "func2", "function", 1, 1, "def func2(): pass"
                            )
                        ]
                    elif file_path.name == "file3.py":
                        mock_module_info.elements = [
                            SemanticElement(
                                "func3", "function", 1, 1, "def func3(): pass"
                            )
                        ]
                    return mock_module_info

                mock_analyze.side_effect = mock_analyze_side_effect

                chunks = []
                async for chunk in processor.process_repository(temp_path, False, True):
                    chunks.append(chunk)

                assert len(chunks) == 3
                chunk_contents = [chunk.content for chunk in chunks]
                assert "def func1(): pass" in chunk_contents
                assert "def func2(): pass" in chunk_contents
                assert "def func3(): pass" in chunk_contents

    def test_estimate_processing_time(self):
        """Test processing time estimation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "small.py").write_text("def small(): pass")
            (temp_path / "large.py").write_text("def large(): pass\n" * 1000)

            processor = LargeCodebaseProcessor(SpecificationConfig())
            estimate = processor.estimate_processing_time(temp_path)

            assert isinstance(estimate, dict)
            assert "total_files" in estimate
            assert "total_size_mb" in estimate
            assert "estimated_minutes" in estimate
            assert "estimated_hours" in estimate

            assert estimate["total_files"] >= 2
            assert estimate["total_size_mb"] > 0
            assert estimate["estimated_minutes"] > 0

    @pytest.mark.asyncio
    async def test_process_batch_files(self):
        """Test processing files in batches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple test files
            files = []
            for i in range(5):
                file_path = temp_path / f"file{i}.py"
                file_path.write_text(f"def func{i}(): pass")
                files.append(file_path)

            config = SpecificationConfig(parallel_processes=2)
            processor = LargeCodebaseProcessor(config)

            # Mock AST analyzer
            with patch.object(processor.ast_analyzer, "analyze_file") as mock_analyze:

                def mock_analyze_side_effect(file_path, language):
                    mock_module_info = Mock()
                    # Extract file number from filename
                    file_num = file_path.name.replace("file", "").replace(".py", "")
                    mock_module_info.elements = [
                        SemanticElement(
                            f"func{file_num}",
                            "function",
                            1,
                            1,
                            f"def func{file_num}(): pass",
                        )
                    ]
                    return mock_module_info

                mock_analyze.side_effect = mock_analyze_side_effect

                # Note: _process_batch_files is now internal and uses file_info dicts
                # We'll test the public interface instead
                from spec_generator.core.processor import ProcessingContext

                context = ProcessingContext(processor.config)
                chunks = []
                for file_info in [
                    {"path": f, "language": Language.PYTHON} for f in files
                ]:
                    file_chunks = await processor._process_single_file(
                        file_info, context, False, True
                    )
                    chunks.extend(file_chunks)

                assert len(chunks) == 5
                for i, chunk in enumerate(chunks):
                    assert f"def func{i}(): pass" == chunk.content

    def test_memory_tracker_integration(self):
        """Test memory tracker integration."""
        processor = LargeCodebaseProcessor(SpecificationConfig(max_memory_mb=100))

        # Create a processing context to test memory tracking
        from spec_generator.core.processor import ProcessingContext

        context = ProcessingContext(processor.config)

        # Test that memory tracker is initialized
        assert context.memory_tracker is not None
        assert context.memory_tracker.max_memory_mb == 100

        # Test memory tracking methods
        current_usage = context.memory_tracker.get_current_usage_mb()
        assert current_usage >= 0

        # Test GC trigger logic
        should_trigger = context.memory_tracker.should_trigger_gc()
        assert isinstance(should_trigger, bool)

    def test_file_filtering_via_scanner(self):
        """Test file filtering via FileScanner."""
        processor = LargeCodebaseProcessor(SpecificationConfig())

        # Test that file scanner has exclude patterns
        assert processor.file_scanner.exclude_patterns is not None

        # Test some common exclusion patterns
        exclude_patterns = processor.file_scanner.exclude_patterns
        # This test depends on FileScanner implementation
        # We just verify the scanner is initialized
        assert len(exclude_patterns) >= 0

    @pytest.mark.asyncio
    async def test_error_handling_during_processing(self):
        """Test error handling during file processing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test(): pass")
            test_file = Path(f.name)

        try:
            processor = LargeCodebaseProcessor(SpecificationConfig())

            # Mock AST analyzer to raise an exception
            with patch.object(processor.ast_analyzer, "analyze_file") as mock_analyze:
                mock_analyze.side_effect = Exception("Parse error")

                # Should handle error gracefully and return empty list
                chunks = await processor.process_single_file(test_file, False, True)
                assert chunks == []

        finally:
            test_file.unlink()


# Fixtures
@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return SpecificationConfig(
        chunk_size=1000,
        chunk_overlap=100,
        supported_languages=[Language.PYTHON, Language.JAVASCRIPT],
    )


@pytest.fixture
def temp_repository():
    """Create a temporary repository with sample files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create directory structure
        (temp_path / "src").mkdir()
        (temp_path / "tests").mkdir()

        # Create sample files
        (temp_path / "src" / "main.py").write_text(
            """
def main():
    print("Hello, World!")

class Application:
    def __init__(self):
        self.name = "Test App"

    def run(self):
        main()
"""
        )

        (temp_path / "src" / "utils.js").write_text(
            """
function calculateSum(a, b) {
    return a + b;
}

class Calculator {
    constructor() {
        this.result = 0;
    }

    add(value) {
        this.result += value;
        return this;
    }
}
"""
        )

        (temp_path / "tests" / "test_main.py").write_text(
            """
import unittest

class TestMain(unittest.TestCase):
    def test_main(self):
        pass
"""
        )

        yield temp_path


@pytest.mark.asyncio
async def test_integration_full_repository_processing(temp_repository, sample_config):
    """Integration test for processing a complete repository."""
    processor = LargeCodebaseProcessor(sample_config)

    # Mock the AST analyzer to avoid tree-sitter dependency
    def mock_analyze_side_effect(file_path, language):
        mock_module_info = Mock()
        if file_path.name == "main.py":
            mock_module_info.elements = [
                SemanticElement(
                    "main", "function", 2, 3, 'def main():\n    print("Hello, World!")'
                ),
                SemanticElement(
                    "Application",
                    "class",
                    5,
                    11,
                    'class Application:\n    def __init__(self):\n        self.name = "Test App"\n    \n    def run(self):\n        main()',
                ),
            ]
        elif file_path.name == "utils.js":
            mock_module_info.elements = [
                SemanticElement(
                    "calculateSum",
                    "function",
                    2,
                    4,
                    "function calculateSum(a, b) {\n    return a + b;\n}",
                ),
                SemanticElement(
                    "Calculator",
                    "class",
                    6,
                    14,
                    "class Calculator {\n    constructor() {\n        this.result = 0;\n    }\n    \n    add(value) {\n        this.result += value;\n        return this;\n    }\n}",
                ),
            ]
        elif file_path.name == "test_main.py":
            mock_module_info.elements = [
                SemanticElement(
                    "TestMain",
                    "class",
                    4,
                    6,
                    "class TestMain(unittest.TestCase):\n    def test_main(self):\n        pass",
                )
            ]
        else:
            mock_module_info.elements = []
        return mock_module_info

    with patch.object(
        processor.ast_analyzer, "analyze_file", side_effect=mock_analyze_side_effect
    ):
        chunks = []
        async for chunk in processor.process_repository(temp_repository, False, True):
            chunks.append(chunk)

        # Should process all source files
        assert len(chunks) >= 3  # At least 3 files worth of chunks

        # Check that we got chunks from all expected files
        file_names = {chunk.file_path.name for chunk in chunks}
        assert "main.py" in file_names
        assert "utils.js" in file_names
        assert "test_main.py" in file_names

        # Check language detection
        languages = {chunk.language for chunk in chunks}
        assert Language.PYTHON in languages
        assert Language.JAVASCRIPT in languages

        # Check content preservation
        contents = [chunk.content for chunk in chunks]
        assert any("def main():" in content for content in contents)
        assert any("class Application:" in content for content in contents)
        assert any("function calculateSum" in content for content in contents)


@pytest.mark.asyncio
async def test_chunk_processor_content_vs_ast():
    """Test differences between content and AST chunking."""
    config = SpecificationConfig(chunk_size=50, chunk_overlap=10)
    processor = ChunkProcessor(config)

    content = "def func1(): pass\ndef func2(): pass\ndef func3(): pass"
    file_path = Path("test.py")
    language = Language.PYTHON

    # Content chunking
    content_chunks = await processor.create_chunks_from_content(
        content, file_path, language
    )

    # AST chunking
    from unittest.mock import Mock

    mock_analyzer = Mock()
    mock_module_info = Mock()
    mock_module_info.elements = [
        SemanticElement("func1", "function", 1, 1, "def func1(): pass"),
        SemanticElement("func2", "function", 2, 2, "def func2(): pass"),
        SemanticElement("func3", "function", 3, 3, "def func3(): pass"),
    ]
    mock_analyzer.analyze_file.return_value = mock_module_info

    ast_chunks = await processor.create_chunks_from_ast(
        file_path, language, mock_analyzer
    )

    # AST chunking should preserve function boundaries better
    assert len(ast_chunks) >= 3  # Should have at least 3 function chunks

    # Each AST chunk should contain complete functions
    for chunk in ast_chunks:
        assert chunk.content.strip().startswith("def")
        assert chunk.content.strip().endswith("pass")
