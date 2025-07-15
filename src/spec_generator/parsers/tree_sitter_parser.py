"""
Tree-sitter parser wrapper for extracting semantic elements from code.

This module provides a unified interface for parsing code using Tree-sitter
and extracting functions, classes, and other semantic elements.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import tree_sitter

from ..models import Language

logger = logging.getLogger(__name__)


class SemanticElement:
    """Represents a semantic element extracted from code."""

    def __init__(
        self,
        name: str,
        element_type: str,
        content: str,
        start_line: int,
        end_line: int,
        node: tree_sitter.Node,
        doc_comment: Optional[str] = None,
        parameters: Optional[list[str]] = None,
        return_type: Optional[str] = None,
    ):
        self.name = name
        self.element_type = element_type  # function, class, method, variable, etc.
        self.content = content
        self.start_line = start_line
        self.end_line = end_line
        self.node = node
        self.doc_comment = doc_comment
        self.parameters = parameters or []
        self.return_type = return_type

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "type": self.element_type,
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "doc_comment": self.doc_comment,
            "parameters": self.parameters,
            "return_type": self.return_type,
        }


class LanguageParser(ABC):
    """Abstract base class for language-specific parsers."""

    def __init__(self, language: Language):
        self.language = language
        try:
            self.parser = tree_sitter.Parser()
            self.ts_language = self._get_language(language)
            if self.ts_language:
                self.parser.set_language(self.ts_language)
            logger.info(f"Initialized TreeSitter parser for {language.value}")
        except Exception as e:
            logger.error(f"Failed to initialize parser for {language.value}: {e}")
            # Create a mock parser for testing purposes
            self.parser = None
            self.ts_language = None
            logger.warning(f"Using mock parser for {language.value}")

    def _get_language(self, language: Language):
        """Get Tree-sitter language object (placeholder implementation)."""
        # This is a placeholder - in a real implementation, you would load
        # the actual Tree-sitter language libraries
        logger.warning(f"Mock language loading for {language.value}")
        return None

    @abstractmethod
    def extract_functions(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
        """Extract function definitions from the AST."""
        pass

    @abstractmethod
    def extract_classes(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
        """Extract class definitions from the AST."""
        pass

    def extract_all_elements(
        self, root_node: tree_sitter.Node
    ) -> list[SemanticElement]:
        """Extract all semantic elements from the AST."""
        elements = []
        elements.extend(self.extract_functions(root_node))
        elements.extend(self.extract_classes(root_node))
        return elements

    def _get_node_text(self, node: tree_sitter.Node) -> str:
        """Get text content of a node."""
        return node.text.decode("utf-8")

    def _get_node_location(self, node: tree_sitter.Node) -> tuple:
        """Get start and end line numbers for a node."""
        start_line = node.start_point[0] + 1  # Convert to 1-based indexing
        end_line = node.end_point[0] + 1
        return start_line, end_line


class PythonParser(LanguageParser):
    """Parser for Python code."""

    def __init__(self):
        super().__init__(Language.PYTHON)

    def extract_functions(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
        """Extract Python function definitions."""
        query_code = """
        (function_definition
            name: (identifier) @function.name
            parameters: (parameters)? @function.params
            body: (block) @function.body) @function.def
        """

        query = self.ts_language.query(query_code)
        captures = query.captures(root_node)

        functions = []
        current_function = {}

        for node, capture_name in captures:
            if capture_name == "function.def":
                if current_function:
                    functions.append(self._create_function_element(current_function))
                current_function = {"node": node}
            elif capture_name == "function.name":
                current_function["name"] = self._get_node_text(node)
            elif capture_name == "function.params":
                current_function["params"] = self._extract_python_parameters(node)
            elif capture_name == "function.body":
                current_function["body"] = node

        # Add the last function
        if current_function:
            functions.append(self._create_function_element(current_function))

        return functions

    def extract_classes(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
        """Extract Python class definitions."""
        query_code = """
        (class_definition
            name: (identifier) @class.name
            body: (block) @class.body) @class.def
        """

        query = self.ts_language.query(query_code)
        captures = query.captures(root_node)

        classes = []
        current_class = {}

        for node, capture_name in captures:
            if capture_name == "class.def":
                if current_class:
                    classes.append(self._create_class_element(current_class))
                current_class = {"node": node}
            elif capture_name == "class.name":
                current_class["name"] = self._get_node_text(node)
            elif capture_name == "class.body":
                current_class["body"] = node

        # Add the last class
        if current_class:
            classes.append(self._create_class_element(current_class))

        return classes

    def _create_function_element(self, func_data: dict) -> SemanticElement:
        """Create a SemanticElement for a Python function."""
        node = func_data["node"]
        name = func_data.get("name", "unknown")
        start_line, end_line = self._get_node_location(node)
        content = self._get_node_text(node)
        doc_comment = self._extract_python_docstring(func_data.get("body"))
        parameters = func_data.get("params", [])

        return SemanticElement(
            name=name,
            element_type="function",
            content=content,
            start_line=start_line,
            end_line=end_line,
            node=node,
            doc_comment=doc_comment,
            parameters=parameters,
        )

    def _create_class_element(self, class_data: dict) -> SemanticElement:
        """Create a SemanticElement for a Python class."""
        node = class_data["node"]
        name = class_data.get("name", "unknown")
        start_line, end_line = self._get_node_location(node)
        content = self._get_node_text(node)
        doc_comment = self._extract_python_docstring(class_data.get("body"))

        return SemanticElement(
            name=name,
            element_type="class",
            content=content,
            start_line=start_line,
            end_line=end_line,
            node=node,
            doc_comment=doc_comment,
        )

    def _extract_python_parameters(self, params_node: tree_sitter.Node) -> list[str]:
        """Extract parameter names from Python function parameters."""
        if not params_node:
            return []

        parameters = []
        for child in params_node.children:
            if child.type == "identifier":
                parameters.append(self._get_node_text(child))
            elif child.type == "typed_parameter":
                # Handle typed parameters like (name: type)
                for subchild in child.children:
                    if subchild.type == "identifier":
                        parameters.append(self._get_node_text(subchild))
                        break

        return parameters

    def _extract_python_docstring(
        self, body_node: Optional[tree_sitter.Node]
    ) -> Optional[str]:
        """Extract docstring from Python function/class body."""
        if not body_node:
            return None

        # Look for the first string expression in the body
        for child in body_node.children:
            if child.type == "expression_statement":
                for subchild in child.children:
                    if subchild.type == "string":
                        # Remove quotes and return the docstring
                        text = self._get_node_text(subchild)
                        return text.strip("\"'")

        return None


class JavaScriptParser(LanguageParser):
    """Parser for JavaScript/TypeScript code."""

    def __init__(self, language: Language = Language.JAVASCRIPT):
        super().__init__(language)

    def extract_functions(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
        """Extract JavaScript function definitions."""
        query_code = """
        [
            (function_declaration
                name: (identifier) @function.name
                parameters: (formal_parameters) @function.params
                body: (statement_block) @function.body) @function.def
            (arrow_function
                parameters: (formal_parameters) @function.params
                body: (_) @function.body) @function.def
        ]
        """

        query = self.ts_language.query(query_code)
        captures = query.captures(root_node)

        functions = []
        current_function = {}

        for node, capture_name in captures:
            if capture_name == "function.def":
                if current_function:
                    functions.append(self._create_js_function_element(current_function))
                current_function = {"node": node}
            elif capture_name == "function.name":
                current_function["name"] = self._get_node_text(node)
            elif capture_name == "function.params":
                current_function["params"] = self._extract_js_parameters(node)
            elif capture_name == "function.body":
                current_function["body"] = node

        # Add the last function
        if current_function:
            functions.append(self._create_js_function_element(current_function))

        return functions

    def extract_classes(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
        """Extract JavaScript class definitions."""
        query_code = """
        (class_declaration
            name: (identifier) @class.name
            body: (class_body) @class.body) @class.def
        """

        query = self.ts_language.query(query_code)
        captures = query.captures(root_node)

        classes = []
        current_class = {}

        for node, capture_name in captures:
            if capture_name == "class.def":
                if current_class:
                    classes.append(self._create_js_class_element(current_class))
                current_class = {"node": node}
            elif capture_name == "class.name":
                current_class["name"] = self._get_node_text(node)
            elif capture_name == "class.body":
                current_class["body"] = node

        # Add the last class
        if current_class:
            classes.append(self._create_js_class_element(current_class))

        return classes

    def _create_js_function_element(self, func_data: dict) -> SemanticElement:
        """Create a SemanticElement for a JavaScript function."""
        node = func_data["node"]
        name = func_data.get("name", "anonymous")
        start_line, end_line = self._get_node_location(node)
        content = self._get_node_text(node)
        parameters = func_data.get("params", [])

        return SemanticElement(
            name=name,
            element_type="function",
            content=content,
            start_line=start_line,
            end_line=end_line,
            node=node,
            parameters=parameters,
        )

    def _create_js_class_element(self, class_data: dict) -> SemanticElement:
        """Create a SemanticElement for a JavaScript class."""
        node = class_data["node"]
        name = class_data.get("name", "unknown")
        start_line, end_line = self._get_node_location(node)
        content = self._get_node_text(node)

        return SemanticElement(
            name=name,
            element_type="class",
            content=content,
            start_line=start_line,
            end_line=end_line,
            node=node,
        )

    def _extract_js_parameters(self, params_node: tree_sitter.Node) -> list[str]:
        """Extract parameter names from JavaScript function parameters."""
        if not params_node:
            return []

        parameters = []
        for child in params_node.children:
            if child.type == "identifier":
                parameters.append(self._get_node_text(child))
            elif child.type == "required_parameter":
                # Handle TypeScript typed parameters
                for subchild in child.children:
                    if subchild.type == "identifier":
                        parameters.append(self._get_node_text(subchild))
                        break

        return parameters


class TreeSitterParser:
    """Main Tree-sitter parser that coordinates language-specific parsers."""

    def __init__(self):
        self._parsers: dict[Language, LanguageParser] = {}
        self._initialize_parsers()

    def _initialize_parsers(self) -> None:
        """Initialize language-specific parsers."""
        try:
            self._parsers[Language.PYTHON] = PythonParser()
            logger.info("Initialized Python parser")
        except Exception as e:
            logger.warning(f"Failed to initialize Python parser: {e}")

        try:
            self._parsers[Language.JAVASCRIPT] = JavaScriptParser(Language.JAVASCRIPT)
            logger.info("Initialized JavaScript parser")
        except Exception as e:
            logger.warning(f"Failed to initialize JavaScript parser: {e}")

        try:
            self._parsers[Language.TYPESCRIPT] = JavaScriptParser(Language.TYPESCRIPT)
            logger.info("Initialized TypeScript parser")
        except Exception as e:
            logger.warning(f"Failed to initialize TypeScript parser: {e}")

    def parse_file(self, file_path: str, language: Language) -> list[SemanticElement]:
        """
        Parse a file and extract semantic elements.

        Args:
            file_path: Path to the file to parse.
            language: Programming language of the file.

        Returns:
            List of semantic elements found in the file.

        Raises:
            ValueError: If language is not supported.
            FileNotFoundError: If file does not exist.
        """
        if language not in self._parsers:
            raise ValueError(f"Language {language.value} is not supported")

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            return self.parse_content(content, language)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return []

    def parse_content(
        self, content: bytes, language: Language
    ) -> list[SemanticElement]:
        """
        Parse content and extract semantic elements.

        Args:
            content: Content to parse as bytes.
            language: Programming language of the content.

        Returns:
            List of semantic elements found in the content.
        """
        if language not in self._parsers:
            logger.warning(f"Language {language.value} is not supported")
            return []

        try:
            parser = self._parsers[language]
            tree = parser.parser.parse(content)
            elements = parser.extract_all_elements(tree.root_node)

            logger.debug(f"Extracted {len(elements)} elements for {language.value}")
            return elements
        except Exception as e:
            logger.error(f"Error parsing {language.value} content: {e}")
            return []

    def get_supported_languages(self) -> list[Language]:
        """Get list of supported languages."""
        return list(self._parsers.keys())

    def is_language_supported(self, language: Language) -> bool:
        """Check if a language is supported."""
        return language in self._parsers
