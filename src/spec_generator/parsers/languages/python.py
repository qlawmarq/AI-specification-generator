"""Python language parser implementation."""

import logging
from typing import Optional

import tree_sitter

from ...models import ClassStructure, Language
from ..base import LanguageParser, SemanticElement

logger = logging.getLogger(__name__)


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

    def extract_class_structures(
        self, root_node: tree_sitter.Node, file_path: str
    ) -> list[ClassStructure]:
        """Extract complete class structures with method relationships."""
        class_query = """
        (class_definition
            name: (identifier) @class.name
            body: (block) @class.body) @class.def
        """

        query = self.ts_language.query(class_query)
        captures = query.captures(root_node)

        class_structures = []
        class_defs = captures.get("class.def", [])

        for class_node in class_defs:
            class_name = None
            class_body = None

            # Extract class name
            name_nodes = captures.get("class.name", [])
            for name_node in name_nodes:
                if self._is_node_within(name_node, class_node):
                    class_name = self._get_node_text(name_node)
                    break

            # Extract class body
            body_nodes = captures.get("class.body", [])
            for body_node in body_nodes:
                if self._is_node_within(body_node, class_node):
                    class_body = body_node
                    break

            if class_name and class_body:
                # Extract methods within this class
                class_methods = self._extract_methods_in_range(
                    class_node.start_point[0] + 1,
                    class_node.end_point[0] + 1,
                    root_node
                )

                # Extract class docstring
                docstring = self._extract_python_docstring(class_body)

                # Create ClassStructure
                class_structure = ClassStructure(
                    name=class_name,
                    methods=class_methods,
                    attributes=[],  # TODO: Extract attributes
                    docstring=docstring,
                    start_line=class_node.start_point[0] + 1,
                    end_line=class_node.end_point[0] + 1,
                    file_path=file_path
                )

                class_structures.append(class_structure)

        return class_structures

    def _extract_methods_in_range(
        self, start_line: int, end_line: int, root_node: tree_sitter.Node
    ) -> list[SemanticElement]:
        """Extract methods within a specific line range (for class methods)."""
        method_query = """
        (function_definition
            name: (identifier) @method.name
            parameters: (parameters)? @method.params
            body: (block) @method.body) @method.def
        """

        query = self.ts_language.query(method_query)
        captures = query.captures(root_node)

        methods = []
        method_defs = captures.get("method.def", [])

        for method_node in method_defs:
            method_start = method_node.start_point[0] + 1
            method_end = method_node.end_point[0] + 1

            # Check if method is within the class range
            if method_start >= start_line and method_end <= end_line:
                method_data = {"node": method_node}

                # Extract method name
                name_nodes = captures.get("method.name", [])
                for name_node in name_nodes:
                    if self._is_node_within(name_node, method_node):
                        method_data["name"] = self._get_node_text(name_node)
                        break

                # Extract method parameters
                param_nodes = captures.get("method.params", [])
                for param_node in param_nodes:
                    if self._is_node_within(param_node, method_node):
                        method_data["params"] = self._extract_python_parameters(
                            param_node
                        )
                        break

                # Extract method body
                body_nodes = captures.get("method.body", [])
                for body_node in body_nodes:
                    if self._is_node_within(body_node, method_node):
                        method_data["body"] = body_node
                        break

                methods.append(self._create_function_element(method_data))

        return methods