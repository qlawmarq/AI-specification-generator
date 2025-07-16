"""
Tree-sitter parser wrapper for extracting semantic elements from code.

This module provides a unified interface for parsing code using Tree-sitter
and extracting functions, classes, and other semantic elements.
"""

import importlib
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
        start_line: int,
        end_line: int,
        content: str,
        node: Optional[tree_sitter.Node] = None,
        doc_comment: Optional[str] = None,
        parameters: Optional[list[str]] = None,
        return_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        # Validate line numbers
        if end_line < start_line:
            raise ValueError("end_line must be greater than or equal to start_line")

        self.name = name
        self.element_type = element_type  # function, class, method, variable, etc.
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.node = node
        self.doc_comment = doc_comment
        self.parameters = parameters or []
        self.return_type = return_type
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "element_type": self.element_type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
            "doc_comment": self.doc_comment,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "metadata": self.metadata,
        }


class LanguageParser(ABC):
    """Abstract base class for language-specific parsers."""

    def __init__(self, language: Language):
        self.language = language
        try:
            # CRITICAL: Create actual parser instance
            self.parser = tree_sitter.Parser()
            self.ts_language = self._get_language(language)
            # CRITICAL: Set language before parsing
            self.parser.language = self.ts_language
            logger.info(f"Initialized TreeSitter parser for {language.value}")
        except Exception as e:
            logger.error(f"Failed to initialize parser for {language.value}: {e}")
            raise

    def _get_language(self, language: Language) -> tree_sitter.Language:
        """Get Tree-sitter language object."""
        # CRITICAL: Import actual language parsers
        language_map = {
            Language.PYTHON: "tree_sitter_python",
            Language.JAVASCRIPT: "tree_sitter_javascript",
            Language.TYPESCRIPT: "tree_sitter_typescript",
            Language.JAVA: "tree_sitter_java",
            Language.CPP: "tree_sitter_cpp",
            Language.C: "tree_sitter_c",
        }

        try:
            module_name = language_map[language]
            # PATTERN: Dynamic import with error handling
            module = importlib.import_module(module_name)

            # CRITICAL: Handle different API structures for different languages
            # Reason: tree-sitter-typescript uses language_typescript() instead of language()
            if language == Language.TYPESCRIPT:
                if hasattr(module, "language_typescript"):
                    return tree_sitter.Language(module.language_typescript())
                elif hasattr(module, "language"):
                    return tree_sitter.Language(module.language())
                else:
                    raise AttributeError(
                        f"Module {module_name} has no typescript language function"
                    )
            else:
                # CRITICAL: Use Language() constructor with language library
                return tree_sitter.Language(module.language())
        except ImportError as e:
            logger.error(f"Language parser not installed: {module_name}")
            raise ImportError(
                f"Language parser {module_name} not installed. "
                f"Please run: pip install {module_name}"
            ) from e
        except AttributeError as e:
            logger.error(f"Failed to load language {language.value}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load language {language.value}: {e}")
            raise

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
        if node.text is None:
            return ""
        return node.text.decode("utf-8")

    def _get_node_location(self, node: tree_sitter.Node) -> tuple[int, int]:
        """Get start and end line numbers for a node."""
        start_line = node.start_point[0] + 1  # Convert to 1-based indexing
        end_line = node.end_point[0] + 1
        return start_line, end_line

    def _is_node_within(
        self, child_node: tree_sitter.Node, parent_node: tree_sitter.Node
    ) -> bool:
        """Check if a node is within another node."""
        return (
            child_node.start_point >= parent_node.start_point
            and child_node.end_point <= parent_node.end_point
        )


class PythonParser(LanguageParser):
    """Parser for Python code."""

    def __init__(self) -> None:
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
        function_defs = captures.get("function.def", [])

        for function_node in function_defs:
            function_data = {"node": function_node}

            # Extract function name
            name_nodes = captures.get("function.name", [])
            for name_node in name_nodes:
                if self._is_node_within(name_node, function_node):
                    function_data["name"] = self._get_node_text(name_node)
                    break

            # Extract function parameters
            param_nodes = captures.get("function.params", [])
            for param_node in param_nodes:
                if self._is_node_within(param_node, function_node):
                    function_data["params"] = self._extract_python_parameters(
                        param_node
                    )
                    break

            # Extract function body
            body_nodes = captures.get("function.body", [])
            for body_node in body_nodes:
                if self._is_node_within(body_node, function_node):
                    function_data["body"] = body_node
                    break

            functions.append(self._create_function_element(function_data))

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
        class_defs = captures.get("class.def", [])

        for class_node in class_defs:
            class_data = {"node": class_node}

            # Extract class name
            name_nodes = captures.get("class.name", [])
            for name_node in name_nodes:
                if self._is_node_within(name_node, class_node):
                    class_data["name"] = self._get_node_text(name_node)
                    break

            # Extract class body
            body_nodes = captures.get("class.body", [])
            for body_node in body_nodes:
                if self._is_node_within(body_node, class_node):
                    class_data["body"] = body_node
                    break

            classes.append(self._create_class_element(class_data))

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
            start_line=start_line,
            end_line=end_line,
            content=content,
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
            start_line=start_line,
            end_line=end_line,
            content=content,
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
        function_defs = captures.get("function.def", [])

        for function_node in function_defs:
            function_data = {"node": function_node}

            # Extract function name
            name_nodes = captures.get("function.name", [])
            for name_node in name_nodes:
                if self._is_node_within(name_node, function_node):
                    function_data["name"] = self._get_node_text(name_node)
                    break

            # Extract function parameters
            param_nodes = captures.get("function.params", [])
            for param_node in param_nodes:
                if self._is_node_within(param_node, function_node):
                    function_data["params"] = self._extract_js_parameters(param_node)
                    break

            # Extract function body
            body_nodes = captures.get("function.body", [])
            for body_node in body_nodes:
                if self._is_node_within(body_node, function_node):
                    function_data["body"] = body_node
                    break

            functions.append(self._create_js_function_element(function_data))

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
        class_defs = captures.get("class.def", [])

        for class_node in class_defs:
            class_data = {"node": class_node}

            # Extract class name
            name_nodes = captures.get("class.name", [])
            for name_node in name_nodes:
                if self._is_node_within(name_node, class_node):
                    class_data["name"] = self._get_node_text(name_node)
                    break

            # Extract class body
            body_nodes = captures.get("class.body", [])
            for body_node in body_nodes:
                if self._is_node_within(body_node, class_node):
                    class_data["body"] = body_node
                    break

            classes.append(self._create_js_class_element(class_data))

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
            start_line=start_line,
            end_line=end_line,
            content=content,
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
            start_line=start_line,
            end_line=end_line,
            content=content,
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

    def __init__(self) -> None:
        self._parsers: dict[Language, LanguageParser] = {}
        self._initialize_parsers()

    @property
    def parsers(self) -> dict[Language, LanguageParser]:
        """Get the parsers dictionary (for compatibility with tests)."""
        return self._parsers

    @property
    def supported_languages(self) -> set[Language]:
        """Get set of supported languages (for compatibility with tests)."""
        return {
            Language.PYTHON,
            Language.JAVASCRIPT,
            Language.TYPESCRIPT,
            Language.JAVA,
            Language.CPP,
            Language.C,
        }

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
