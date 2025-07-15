"""
Unit tests for spec_generator.parsers.tree_sitter_parser module.

Tests for TreeSitterParser and SemanticElement functionality.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from spec_generator.models import Language
from spec_generator.parsers.tree_sitter_parser import SemanticElement, TreeSitterParser


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

    def test_parser_initialization(self):
        """Test TreeSitterParser initialization."""
        parser = TreeSitterParser()

        assert parser.parsers == {}
        assert parser.supported_languages == {
            Language.PYTHON,
            Language.JAVASCRIPT,
            Language.TYPESCRIPT,
            Language.JAVA,
            Language.CPP,
            Language.C,
        }

    @patch("spec_generator.parsers.tree_sitter_parser.tree_sitter")
    def test_get_parser_python(self, mock_tree_sitter):
        """Test getting Python parser."""
        # Mock tree-sitter components
        mock_parser = Mock()
        mock_language = Mock()
        mock_tree_sitter.Parser.return_value = mock_parser

        # Mock the Python language import
        with patch("tree_sitter_python.language") as mock_python_lang:
            mock_python_lang.return_value = mock_language

            parser = TreeSitterParser()
            result = parser._get_parser(Language.PYTHON)

            assert result == mock_parser
            mock_parser.set_language.assert_called_once_with(mock_language)

    @patch("spec_generator.parsers.tree_sitter_parser.tree_sitter")
    def test_get_parser_unsupported_language(self, mock_tree_sitter):
        """Test handling of unsupported language."""
        parser = TreeSitterParser()

        # Create a mock language that's not in supported_languages
        unsupported_lang = Mock()
        unsupported_lang.value = "unsupported"

        with pytest.raises(ValueError, match="Unsupported language"):
            parser._get_parser(unsupported_lang)

    @patch("spec_generator.parsers.tree_sitter_parser.tree_sitter")
    def test_get_parser_import_error(self, mock_tree_sitter):
        """Test handling of import error for language parser."""
        parser = TreeSitterParser()

        # Mock ImportError when trying to import language
        with patch(
            "tree_sitter_python.language", side_effect=ImportError("Module not found")
        ):
            with pytest.raises(ImportError):
                parser._get_parser(Language.PYTHON)

    def test_parse_file_nonexistent(self):
        """Test parsing non-existent file."""
        parser = TreeSitterParser()
        non_existent_file = Path("non_existent_file.py")

        result = parser.parse_file(non_existent_file, Language.PYTHON)
        assert result == []

    @patch("spec_generator.parsers.tree_sitter_parser.Path.exists")
    @patch("spec_generator.parsers.tree_sitter_parser.Path.read_text")
    @patch.object(TreeSitterParser, "_get_parser")
    def test_parse_file_success(self, mock_get_parser, mock_read_text, mock_exists):
        """Test successful file parsing."""
        # Setup mocks
        mock_exists.return_value = True
        mock_read_text.return_value = "def hello(): pass"

        # Mock parser and tree
        mock_parser = Mock()
        mock_tree = Mock()
        mock_root = Mock()

        mock_get_parser.return_value = mock_parser
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = mock_root

        # Mock the query and extraction
        with (
            patch.object(TreeSitterParser, "_extract_functions") as mock_extract_funcs,
            patch.object(TreeSitterParser, "_extract_classes") as mock_extract_classes,
        ):

            mock_extract_funcs.return_value = [
                SemanticElement("hello", "function", 1, 1, "def hello(): pass")
            ]
            mock_extract_classes.return_value = []

            parser = TreeSitterParser()
            result = parser.parse_file(Path("test.py"), Language.PYTHON)

            assert len(result) == 1
            assert result[0].name == "hello"
            assert result[0].element_type == "function"

    @patch("spec_generator.parsers.tree_sitter_parser.Path.read_text")
    def test_parse_file_encoding_error(self, mock_read_text):
        """Test handling of encoding error during file reading."""
        mock_read_text.side_effect = UnicodeDecodeError(
            "utf-8", b"", 0, 1, "invalid start byte"
        )

        parser = TreeSitterParser()

        with patch(
            "spec_generator.parsers.tree_sitter_parser.Path.exists", return_value=True
        ):
            result = parser.parse_file(Path("test.py"), Language.PYTHON)
            assert result == []

    def test_extract_functions_python(self):
        """Test extracting Python functions from AST."""
        parser = TreeSitterParser()

        # Mock tree-sitter nodes for Python function
        mock_node = Mock()
        mock_node.start_point = (0, 0)  # line, column
        mock_node.end_point = (2, 4)
        mock_node.text = b"def test_func():\n    pass"

        # Mock child nodes for function name
        mock_name_node = Mock()
        mock_name_node.text = b"test_func"
        mock_node.child_by_field_name.return_value = mock_name_node

        source_code = "def test_func():\n    pass"
        elements = parser._extract_functions([mock_node], source_code, Language.PYTHON)

        assert len(elements) == 1
        assert elements[0].name == "test_func"
        assert elements[0].element_type == "function"
        assert elements[0].start_line == 1  # 1-indexed
        assert elements[0].end_line == 3

    def test_extract_classes_python(self):
        """Test extracting Python classes from AST."""
        parser = TreeSitterParser()

        # Mock tree-sitter nodes for Python class
        mock_node = Mock()
        mock_node.start_point = (0, 0)
        mock_node.end_point = (5, 0)
        mock_node.text = b"class TestClass:\n    def method(self): pass"

        # Mock child nodes for class name
        mock_name_node = Mock()
        mock_name_node.text = b"TestClass"
        mock_node.child_by_field_name.return_value = mock_name_node

        source_code = "class TestClass:\n    def method(self): pass"
        elements = parser._extract_classes([mock_node], source_code, Language.PYTHON)

        assert len(elements) == 1
        assert elements[0].name == "TestClass"
        assert elements[0].element_type == "class"
        assert elements[0].start_line == 1
        assert elements[0].end_line == 6

    def test_extract_functions_javascript(self):
        """Test extracting JavaScript functions from AST."""
        parser = TreeSitterParser()

        # Mock tree-sitter nodes for JavaScript function
        mock_node = Mock()
        mock_node.start_point = (0, 0)
        mock_node.end_point = (2, 1)
        mock_node.text = b"function testFunc() {\n  return true;\n}"

        # Mock child nodes for function name
        mock_name_node = Mock()
        mock_name_node.text = b"testFunc"
        mock_node.child_by_field_name.return_value = mock_name_node

        source_code = "function testFunc() {\n  return true;\n}"
        elements = parser._extract_functions(
            [mock_node], source_code, Language.JAVASCRIPT
        )

        assert len(elements) == 1
        assert elements[0].name == "testFunc"
        assert elements[0].element_type == "function"
        assert elements[0].start_line == 1
        assert elements[0].end_line == 3

    def test_extract_classes_javascript(self):
        """Test extracting JavaScript classes from AST."""
        parser = TreeSitterParser()

        # Mock tree-sitter nodes for JavaScript class
        mock_node = Mock()
        mock_node.start_point = (0, 0)
        mock_node.end_point = (4, 1)
        mock_node.text = b"class TestClass {\n  constructor() {}\n  method() {}\n}"

        # Mock child nodes for class name
        mock_name_node = Mock()
        mock_name_node.text = b"TestClass"
        mock_node.child_by_field_name.return_value = mock_name_node

        source_code = "class TestClass {\n  constructor() {}\n  method() {}\n}"
        elements = parser._extract_classes(
            [mock_node], source_code, Language.JAVASCRIPT
        )

        assert len(elements) == 1
        assert elements[0].name == "TestClass"
        assert elements[0].element_type == "class"
        assert elements[0].start_line == 1
        assert elements[0].end_line == 5

    def test_extract_functions_missing_name(self):
        """Test extracting functions when name node is missing."""
        parser = TreeSitterParser()

        # Mock node without name
        mock_node = Mock()
        mock_node.start_point = (0, 0)
        mock_node.end_point = (1, 0)
        mock_node.text = b"def (): pass"  # Anonymous function
        mock_node.child_by_field_name.return_value = None  # No name node

        source_code = "def (): pass"
        elements = parser._extract_functions([mock_node], source_code, Language.PYTHON)

        assert len(elements) == 1
        assert elements[0].name == "<anonymous>"
        assert elements[0].element_type == "function"

    def test_get_language_queries_python(self):
        """Test getting queries for Python language."""
        parser = TreeSitterParser()
        queries = parser._get_language_queries(Language.PYTHON)

        assert "function_query" in queries
        assert "class_query" in queries
        assert "function_definition" in queries["function_query"]
        assert "class_definition" in queries["class_query"]

    def test_get_language_queries_javascript(self):
        """Test getting queries for JavaScript language."""
        parser = TreeSitterParser()
        queries = parser._get_language_queries(Language.JAVASCRIPT)

        assert "function_query" in queries
        assert "class_query" in queries
        assert any("function" in q for q in queries["function_query"])

    def test_get_language_queries_unsupported(self):
        """Test getting queries for unsupported language returns empty."""
        parser = TreeSitterParser()

        # Mock unsupported language
        mock_lang = Mock()
        mock_lang.value = "unsupported"

        queries = parser._get_language_queries(mock_lang)
        assert queries == {"function_query": [], "class_query": []}

    @patch.object(TreeSitterParser, "_get_parser")
    def test_parse_content_directly(self, mock_get_parser):
        """Test parsing content directly without file."""
        # Setup mocks
        mock_parser = Mock()
        mock_tree = Mock()
        mock_root = Mock()

        mock_get_parser.return_value = mock_parser
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = mock_root

        # Mock queries
        with patch.object(TreeSitterParser, "_run_query") as mock_run_query:
            mock_run_query.side_effect = [[Mock()], []]  # Function nodes  # Class nodes

            with patch.object(
                TreeSitterParser, "_extract_functions"
            ) as mock_extract_funcs:
                mock_extract_funcs.return_value = [
                    SemanticElement("test", "function", 1, 1, "def test(): pass")
                ]

                parser = TreeSitterParser()
                result = parser.parse_content("def test(): pass", Language.PYTHON)

                assert len(result) == 1
                assert result[0].name == "test"

    def test_parser_caching(self):
        """Test that parsers are cached after first use."""
        with patch("spec_generator.parsers.tree_sitter_parser.tree_sitter") as mock_ts:
            mock_parser = Mock()
            mock_ts.Parser.return_value = mock_parser

            with patch("tree_sitter_python.language") as mock_lang:
                mock_lang.return_value = Mock()

                parser = TreeSitterParser()

                # First call should create parser
                parser1 = parser._get_parser(Language.PYTHON)

                # Second call should return cached parser
                parser2 = parser._get_parser(Language.PYTHON)

                assert parser1 is parser2
                assert mock_ts.Parser.call_count == 1  # Only called once


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
    with patch("spec_generator.parsers.tree_sitter_parser.tree_sitter"):
        parser = TreeSitterParser()
        return parser


def test_integration_parse_python_code(sample_python_code):
    """Integration test for parsing Python code."""
    # This test would require actual tree-sitter installation
    # For now, we'll mock the essential parts

    with (
        patch("spec_generator.parsers.tree_sitter_parser.tree_sitter") as mock_ts,
        patch("tree_sitter_python.language") as mock_lang,
    ):

        # Setup mocks
        mock_parser = Mock()
        mock_tree = Mock()
        mock_root = Mock()

        mock_ts.Parser.return_value = mock_parser
        mock_lang.return_value = Mock()
        mock_parser.parse.return_value = mock_tree
        mock_tree.root_node = mock_root

        # Mock query results
        def mock_query_side_effect(*args, **kwargs):
            query_text = args[0] if args else ""
            if "function_definition" in query_text:
                # Return mock function nodes
                mock_func_node = Mock()
                mock_func_node.start_point = (1, 0)
                mock_func_node.end_point = (3, 0)
                mock_func_node.text = b'def hello_world():\n    """Say hello to the world."""\n    print("Hello, World!")'

                mock_name_node = Mock()
                mock_name_node.text = b"hello_world"
                mock_func_node.child_by_field_name.return_value = mock_name_node

                return [(mock_func_node, "")]
            elif "class_definition" in query_text:
                # Return mock class nodes
                mock_class_node = Mock()
                mock_class_node.start_point = (5, 0)
                mock_class_node.end_point = (19, 0)
                mock_class_node.text = (
                    b'class Calculator:\n    """A simple calculator class."""\n    ...'
                )

                mock_name_node = Mock()
                mock_name_node.text = b"Calculator"
                mock_class_node.child_by_field_name.return_value = mock_name_node

                return [(mock_class_node, "")]
            return []

        with patch.object(
            TreeSitterParser, "_run_query", side_effect=mock_query_side_effect
        ):
            parser = TreeSitterParser()
            elements = parser.parse_content(sample_python_code, Language.PYTHON)

            # Should find both functions and classes
            assert len(elements) >= 1  # At least the function we mocked

            # Check that we found the expected elements
            element_names = [elem.name for elem in elements]
            assert "hello_world" in element_names or "Calculator" in element_names


def test_error_handling_malformed_code():
    """Test error handling with malformed code."""
    with (
        patch("spec_generator.parsers.tree_sitter_parser.tree_sitter") as mock_ts,
        patch("tree_sitter_python.language") as mock_lang,
    ):

        # Setup mocks to simulate parsing error
        mock_parser = Mock()
        mock_ts.Parser.return_value = mock_parser
        mock_lang.return_value = Mock()
        mock_parser.parse.side_effect = Exception("Parse error")

        parser = TreeSitterParser()

        # Should handle parsing errors gracefully
        result = parser.parse_content("def broken_syntax(", Language.PYTHON)
        assert result == []  # Should return empty list on error
