"""Java language parser implementation."""

import logging
from typing import Optional

import tree_sitter

from ...models import ClassStructure, Language
from ..base import LanguageParser, SemanticElement

logger = logging.getLogger(__name__)


class JavaParser(LanguageParser):
    """Parser for Java code."""

    def __init__(self) -> None:
        super().__init__(Language.JAVA)

    def extract_functions(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
        """Extract Java method definitions."""
        query_code = """
        (method_declaration
            name: (identifier) @method.name
            parameters: (formal_parameters) @method.params
            body: (block) @method.body) @method.def
        """

        query = self.ts_language.query(query_code)
        captures = query.captures(root_node)

        functions = []
        method_defs = captures.get("method.def", [])

        for method_node in method_defs:
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
                    method_data["params"] = self._extract_java_parameters(param_node)
                    break

            # Extract method body
            body_nodes = captures.get("method.body", [])
            for body_node in body_nodes:
                if self._is_node_within(body_node, method_node):
                    method_data["body"] = body_node
                    break

            functions.append(self._create_method_element(method_data))

        return functions

    def extract_classes(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
        """Extract Java class definitions."""
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

            classes.append(self._create_class_element(class_data))

        return classes

    def _create_method_element(self, method_data: dict) -> SemanticElement:
        """Create a SemanticElement for a Java method."""
        node = method_data["node"]
        name = method_data.get("name", "unknown")
        start_line, end_line = self._get_node_location(node)
        content = self._get_node_text(node)
        parameters = method_data.get("params", [])
        doc_comment = self._extract_java_javadoc(node)

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
        """Create a SemanticElement for a Java class."""
        node = class_data["node"]
        name = class_data.get("name", "unknown")
        start_line, end_line = self._get_node_location(node)
        content = self._get_node_text(node)
        doc_comment = self._extract_java_javadoc(node)

        return SemanticElement(
            name=name,
            element_type="class",
            start_line=start_line,
            end_line=end_line,
            content=content,
            node=node,
            doc_comment=doc_comment,
        )

    def _extract_java_parameters(self, params_node: tree_sitter.Node) -> list[str]:
        """Extract parameter names from Java method parameters."""
        if not params_node:
            return []

        parameters = []
        for child in params_node.children:
            if child.type == "formal_parameter":
                # Java parameters have type and name
                for subchild in child.children:
                    if subchild.type == "identifier":
                        # Skip type identifiers, get the parameter name (usually last)
                        param_name = self._get_node_text(subchild)
                        if param_name not in parameters:
                            parameters.append(param_name)

        return parameters

    def _extract_java_javadoc(self, node: tree_sitter.Node) -> Optional[str]:
        """Extract Javadoc comment from Java element."""
        # Look for block comment before the node
        if node.prev_sibling and node.prev_sibling.type == "block_comment":
            comment_text = self._get_node_text(node.prev_sibling)
            if comment_text.startswith("/**"):
                # Remove /** and */ and clean up
                javadoc = comment_text[3:-2].strip()
                return javadoc

        return None

    def extract_class_structures(
        self, root_node: tree_sitter.Node, file_path: str
    ) -> list[ClassStructure]:
        """Extract complete class structures with method relationships."""
        class_query = """
        (class_declaration
            name: (identifier) @class.name
            body: (class_body) @class.body) @class.def
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

                # Extract class javadoc
                javadoc = self._extract_java_javadoc(class_node)

                # Create ClassStructure
                class_structure = ClassStructure(
                    name=class_name,
                    methods=class_methods,
                    attributes=[],  # TODO: Extract fields
                    docstring=javadoc,
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
        (method_declaration
            name: (identifier) @method.name
            parameters: (formal_parameters) @method.params
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
                        method_data["params"] = self._extract_java_parameters(
                            param_node
                        )
                        break

                # Extract method body
                body_nodes = captures.get("method.body", [])
                for body_node in body_nodes:
                    if self._is_node_within(body_node, method_node):
                        method_data["body"] = body_node
                        break

                methods.append(self._create_method_element(method_data))

        return methods