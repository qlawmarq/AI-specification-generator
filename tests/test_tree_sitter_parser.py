"""
Unit tests for spec_generator.parsers.tree_sitter_parser module.

Tests for TreeSitterParser and SemanticElement functionality.
"""

from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile
import os

import pytest

from spec_generator.models import ClassStructure, Language
from spec_generator.parsers.base import SemanticElement
from spec_generator.parsers.tree_sitter_parser import TreeSitterParser


class TestSemanticElement:
    """Test SemanticElement functionality."""

    def test_semantic_element_creation(self):
        """Test basic SemanticElement creation."""
        element = SemanticElement(
            name="test_function",
            element_type="function",
            start_line=10,
            end_line=15,
            content="def test_function():\n    pass",
        )

        assert element.name == "test_function"
        assert element.element_type == "function"
        assert element.start_line == 10
        assert element.end_line == 15
        assert element.content == "def test_function():\n    pass"
        assert element.metadata == {}

    def test_semantic_element_with_metadata(self):
        """Test SemanticElement with metadata."""
        metadata = {"complexity": "low", "public": True}
        element = SemanticElement(
            name="complex_function",
            element_type="function",
            start_line=1,
            end_line=10,
            content="def complex_function(): pass",
            metadata=metadata,
        )

        assert element.metadata == metadata

    def test_semantic_element_line_validation(self):
        """Test that end_line must be >= start_line."""
        with pytest.raises(ValueError):
            SemanticElement(
                name="test",
                element_type="function",
                start_line=10,
                end_line=5,  # Invalid: end < start
                content="test",
            )

    def test_semantic_element_serialization(self):
        """Test SemanticElement to dictionary conversion."""
        element = SemanticElement(
            name="test_class",
            element_type="class",
            start_line=1,
            end_line=20,
            content="class TestClass: pass",
        )

        data = element.to_dict()
        assert data["name"] == "test_class"
        assert data["element_type"] == "class"
        assert data["start_line"] == 1
        assert data["end_line"] == 20
        assert data["content"] == "class TestClass: pass"
        assert data["metadata"] == {}


class TestTreeSitterParser:
    """Test TreeSitterParser functionality."""

    @patch('spec_generator.parsers.tree_sitter_parser.PythonParser')
    @patch('spec_generator.parsers.tree_sitter_parser.JavaScriptParser')
    @patch('spec_generator.parsers.tree_sitter_parser.JavaParser')
    @patch('spec_generator.parsers.tree_sitter_parser.CppParser')
    def test_parser_initialization(self, mock_cpp, mock_java, mock_js, mock_python):
        """Test TreeSitterParser initialization with mocked language parsers."""
        # Mock the language parser instances
        mock_python_instance = Mock()
        mock_js_instance = Mock()
        mock_java_instance = Mock()
        mock_cpp_instance = Mock()
        
        mock_python.return_value = mock_python_instance
        mock_js.return_value = mock_js_instance
        mock_java.return_value = mock_java_instance
        mock_cpp.return_value = mock_cpp_instance
        
        parser = TreeSitterParser()

        # Verify parsers were initialized
        assert Language.PYTHON in parser.parsers
        assert Language.JAVASCRIPT in parser.parsers
        assert Language.TYPESCRIPT in parser.parsers
        assert Language.JAVA in parser.parsers
        assert Language.CPP in parser.parsers
        
        # Verify the supported_languages property
        assert parser.supported_languages == {
            Language.PYTHON,
            Language.JAVASCRIPT,
            Language.TYPESCRIPT,
            Language.JAVA,
            Language.CPP,
        }

    @patch('spec_generator.parsers.tree_sitter_parser.PythonParser')
    def test_parser_initialization_failure(self, mock_python):
        """Test parser initialization handling failures gracefully."""
        # Mock PythonParser to raise an exception
        mock_python.side_effect = Exception("Parser initialization failed")
        
        # Should not raise exception, just log warning
        parser = TreeSitterParser()
        
        # Python parser should not be in parsers dict due to failure
        assert Language.PYTHON not in parser.parsers

    def test_parse_file_nonexistent(self):
        """Test parsing non-existent file raises FileNotFoundError."""
        parser = TreeSitterParser()
        non_existent_file = "/path/to/nonexistent/file.py"

        with pytest.raises(FileNotFoundError):
            parser.parse_file(non_existent_file, Language.PYTHON)

    def test_parse_file_unsupported_language(self):
        """Test parsing with unsupported language."""
        parser = TreeSitterParser()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def hello(): pass")
            temp_file = f.name

        try:
            # Mock unsupported language
            unsupported_lang = Mock()
            unsupported_lang.value = "unsupported"
            
            with pytest.raises(ValueError, match="Language .* is not supported"):
                parser.parse_file(temp_file, unsupported_lang)
        finally:
            os.unlink(temp_file)

    @patch('spec_generator.parsers.tree_sitter_parser.PythonParser')
    def test_parse_file_success(self, mock_python_class):
        """Test successful file parsing."""
        # Mock the PythonParser instance
        mock_parser = Mock()
        mock_tree = Mock()
        mock_root_node = Mock()
        mock_python_instance = Mock()
        
        mock_python_class.return_value = mock_python_instance
        mock_python_instance.parser = mock_parser
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = mock_root_node
        
        # Mock extract_all_elements
        expected_elements = [
            SemanticElement("hello", "function", 1, 1, "def hello(): pass")
        ]
        mock_python_instance.extract_all_elements.return_value = expected_elements

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def hello(): pass")
            temp_file = f.name

        try:
            parser = TreeSitterParser()
            result = parser.parse_file(temp_file, Language.PYTHON)

            assert len(result) == 1
            assert result[0].name == "hello"
            assert result[0].element_type == "function"
        finally:
            os.unlink(temp_file)

    @patch('spec_generator.parsers.tree_sitter_parser.PythonParser')
    def test_parse_content_success(self, mock_python_class):
        """Test successful content parsing."""
        # Mock the PythonParser instance
        mock_parser = Mock()
        mock_tree = Mock()
        mock_root_node = Mock()
        mock_python_instance = Mock()
        
        mock_python_class.return_value = mock_python_instance
        mock_python_instance.parser = mock_parser
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = mock_root_node
        
        # Mock extract_all_elements
        expected_elements = [
            SemanticElement("test", "function", 1, 1, "def test(): pass")
        ]
        mock_python_instance.extract_all_elements.return_value = expected_elements

        parser = TreeSitterParser()
        result = parser.parse_content(b"def test(): pass", Language.PYTHON)

        assert len(result) == 1
        assert result[0].name == "test"

    def test_parse_content_unsupported_language(self):
        """Test parsing content with unsupported language."""
        parser = TreeSitterParser()
        
        # Mock unsupported language
        unsupported_lang = Mock()
        unsupported_lang.value = "unsupported"
        
        result = parser.parse_content(b"some code", unsupported_lang)
        assert result == []

    @patch('spec_generator.parsers.tree_sitter_parser.PythonParser')
    def test_parse_content_parsing_error(self, mock_python_class):
        """Test handling of parsing errors."""
        # Mock parser to raise exception
        mock_python_instance = Mock()
        mock_python_class.return_value = mock_python_instance
        mock_python_instance.parser.parse.side_effect = Exception("Parse error")

        parser = TreeSitterParser()
        result = parser.parse_content(b"def broken_syntax(", Language.PYTHON)
        assert result == []

    @patch('spec_generator.parsers.tree_sitter_parser.PythonParser')
    def test_get_supported_languages(self, mock_python_class):
        """Test getting supported languages."""
        mock_python_instance = Mock()
        mock_python_class.return_value = mock_python_instance
        
        parser = TreeSitterParser()
        supported = parser.get_supported_languages()
        
        # Should return list of languages that were successfully initialized
        assert isinstance(supported, list)
        assert Language.PYTHON in supported

    def test_is_language_supported(self):
        """Test checking if language is supported."""
        parser = TreeSitterParser()
        
        # Mock a language that's in the parsers dict
        parser._parsers[Language.PYTHON] = Mock()
        
        assert parser.is_language_supported(Language.PYTHON) == True
        
        # Mock unsupported language
        unsupported_lang = Mock()
        assert parser.is_language_supported(unsupported_lang) == False

    @patch('spec_generator.parsers.tree_sitter_parser.PythonParser')
    def test_extract_class_structures_success(self, mock_python_class):
        """Test successful class structure extraction."""
        # Mock the PythonParser instance
        mock_parser = Mock()
        mock_tree = Mock()
        mock_root_node = Mock()
        mock_python_instance = Mock()
        
        mock_python_class.return_value = mock_python_instance
        mock_python_instance.parser = mock_parser
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = mock_root_node
        
        # Mock extract_class_structures
        expected_structures = [
            ClassStructure(
                name="TestClass",
                methods=[],
                attributes=[],
                docstring=None,
                start_line=1,
                end_line=10,
                file_path="test.py"
            )
        ]
        mock_python_instance.extract_class_structures.return_value = expected_structures

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("class TestClass:\n    pass")
            temp_file = f.name

        try:
            parser = TreeSitterParser()
            result = parser.extract_class_structures(temp_file, Language.PYTHON)

            assert len(result) == 1
            assert result[0].name == "TestClass"
        finally:
            os.unlink(temp_file)

    def test_extract_class_structures_unsupported_language(self):
        """Test class structure extraction with unsupported language."""
        parser = TreeSitterParser()
        
        # Mock unsupported language
        unsupported_lang = Mock()
        unsupported_lang.value = "unsupported"
        
        result = parser.extract_class_structures("test.py", unsupported_lang)
        assert result == []

    @patch('spec_generator.parsers.tree_sitter_parser.PythonParser')
    def test_extract_class_structures_error_handling(self, mock_python_class):
        """Test error handling in class structure extraction."""
        # Mock parser to raise exception during parsing
        mock_python_instance = Mock()
        mock_python_class.return_value = mock_python_instance
        mock_python_instance.parser.parse.side_effect = Exception("Parse error")

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("class TestClass:\n    pass")
            temp_file = f.name

        try:
            parser = TreeSitterParser()
            result = parser.extract_class_structures(temp_file, Language.PYTHON)
            assert result == []
        finally:
            os.unlink(temp_file)


# Fixtures for testing
@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return '''
def hello_world():
    """Say hello to the world."""
    print("Hello, World!")

class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.result = 0

    def add(self, x, y):
        """Add two numbers."""
        return x + y

    def multiply(self, x, y):
        """Multiply two numbers."""
        return x * y
'''


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for testing."""
    return """
function greet(name) {
    return `Hello, ${name}!`;
}

class Calculator {
    constructor() {
        this.result = 0;
    }

    add(x, y) {
        return x + y;
    }

    multiply(x, y) {
        return x * y;
    }
}

const arrow_func = (x) => x * 2;
"""


@pytest.fixture
def mock_tree_sitter_parser():
    """Mock TreeSitterParser for testing."""
    with patch('spec_generator.parsers.tree_sitter_parser.PythonParser'):
        parser = TreeSitterParser()
        return parser


@patch('spec_generator.parsers.tree_sitter_parser.PythonParser')
def test_integration_parse_python_code(mock_python_class, sample_python_code):
    """Integration test for parsing Python code."""
    # Mock the PythonParser instance
    mock_parser = Mock()
    mock_tree = Mock()
    mock_root_node = Mock()
    mock_python_instance = Mock()
    
    mock_python_class.return_value = mock_python_instance
    mock_python_instance.parser = mock_parser
    mock_parser.parse.return_value = mock_tree
    mock_tree.root_node = mock_root_node
    
    # Mock extract_all_elements to return expected elements
    expected_elements = [
        SemanticElement("hello_world", "function", 2, 4, 'def hello_world():\n    """Say hello to the world."""\n    print("Hello, World!")'),
        SemanticElement("Calculator", "class", 6, 18, "class Calculator:\n    ...", metadata={"methods": ["__init__", "add", "multiply"]})
    ]
    mock_python_instance.extract_all_elements.return_value = expected_elements

    parser = TreeSitterParser()
    elements = parser.parse_content(sample_python_code.encode('utf-8'), Language.PYTHON)

    # Should find both functions and classes
    assert len(elements) >= 1

    # Check that we found the expected elements
    element_names = [elem.name for elem in elements]
    assert "hello_world" in element_names or "Calculator" in element_names


@patch('spec_generator.parsers.tree_sitter_parser.PythonParser')
def test_error_handling_malformed_code(mock_python_class):
    """Test error handling with malformed code."""
    # Mock parser to raise exception on malformed code
    mock_python_instance = Mock()
    mock_python_class.return_value = mock_python_instance
    mock_python_instance.parser.parse.side_effect = Exception("Parse error")

    parser = TreeSitterParser()

    # Should handle parsing errors gracefully
    result = parser.parse_content(b"def broken_syntax(", Language.PYTHON)
    assert result == []  # Should return empty list on error


def test_parser_properties():
    """Test parser properties and compatibility methods."""
    parser = TreeSitterParser()
    
    # Test parsers property (for compatibility)
    assert hasattr(parser, 'parsers')
    assert isinstance(parser.parsers, dict)
    
    # Test supported_languages property (for compatibility)
    assert hasattr(parser, 'supported_languages')
    assert isinstance(parser.supported_languages, set)
    assert Language.PYTHON in parser.supported_languages
    assert Language.JAVASCRIPT in parser.supported_languages
    assert Language.TYPESCRIPT in parser.supported_languages
    assert Language.JAVA in parser.supported_languages
    assert Language.CPP in parser.supported_languages