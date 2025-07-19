"""JavaScript and TypeScript language parser implementation."""

import logging

import tree_sitter

from ...models import ClassStructure, Language
from ..base import LanguageParser, SemanticElement

logger = logging.getLogger(__name__)


class JavaScriptParser(LanguageParser):
    """Parser for JavaScript/TypeScript code."""

    def __init__(self, language: Language = Language.JAVASCRIPT):
        super().__init__(language)

    def extract_functions(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
        """Extract JavaScript/TypeScript function definitions."""
        # Use different queries based on language
        if self.language == Language.TYPESCRIPT:
            query_code = """
            [
                (function_declaration
                    name: (identifier) @function.name
                    parameters: (formal_parameters) @function.params
                    body: (statement_block) @function.body) @function.def
                (method_definition
                    name: (property_identifier) @function.name
                    parameters: (formal_parameters) @function.params
                    body: (statement_block) @function.body) @function.def
                (arrow_function
                    parameters: (formal_parameters) @function.params
                    body: (_) @function.body) @function.def
            ]
            """
        else:
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
        """Extract JavaScript/TypeScript class definitions."""
        # Use different queries based on language
        if self.language == Language.TYPESCRIPT:
            query_code = """
            (class_declaration
                name: (type_identifier) @class.name
                body: (class_body) @class.body) @class.def
            """
        else:
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
        """Extract parameter names from JavaScript/TypeScript function parameters."""
        if not params_node:
            return []

        parameters = []
        for child in params_node.children:
            if child.type == "identifier":
                parameters.append(self._get_node_text(child))
            elif child.type in ["required_parameter", "optional_parameter"]:
                # Handle TypeScript typed parameters (both required and optional)
                for subchild in child.children:
                    if subchild.type == "identifier":
                        parameters.append(self._get_node_text(subchild))
                        break
            elif child.type == "rest_parameter":
                # Handle rest parameters (...args)
                for subchild in child.children:
                    if subchild.type == "identifier":
                        parameters.append(f"...{self._get_node_text(subchild)}")
                        break

        return parameters

    def extract_class_structures(
        self, root_node: tree_sitter.Node, file_path: str
    ) -> list[ClassStructure]:
        """
        Extract complete class structures with method relationships for JavaScript/TypeScript.
        """
        # Use different queries based on language
        if self.language == Language.TYPESCRIPT:
            class_query = """
            (class_declaration
                name: (type_identifier) @class.name
                body: (class_body) @class.body) @class.def
            """
        else:
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
                class_methods = self._extract_js_methods_in_range(
                    class_node.start_point[0] + 1,
                    class_node.end_point[0] + 1,
                    root_node
                )

                # Create ClassStructure
                class_structure = ClassStructure(
                    name=class_name,
                    methods=class_methods,
                    attributes=[],  # TODO: Extract attributes
                    docstring=None,  # JavaScript doesn't have docstrings like Python
                    start_line=class_node.start_point[0] + 1,
                    end_line=class_node.end_point[0] + 1,
                    file_path=file_path
                )

                class_structures.append(class_structure)

        return class_structures

    def _extract_js_methods_in_range(
        self, start_line: int, end_line: int, root_node: tree_sitter.Node
    ) -> list[SemanticElement]:
        """
        Extract JavaScript/TypeScript methods within a specific line range (for class methods).
        """
        # Use different queries based on language
        if self.language == Language.TYPESCRIPT:
            method_query = """
            [
                (method_definition
                    name: (property_identifier) @method.name
                    parameters: (formal_parameters) @method.params
                    body: (statement_block) @method.body) @method.def
                (function_declaration
                    name: (identifier) @method.name
                    parameters: (formal_parameters) @method.params
                    body: (statement_block) @method.body) @method.def
            ]
            """
        else:
            method_query = """
            [
                (method_definition
                    name: (property_identifier) @method.name
                    parameters: (formal_parameters) @method.params
                    body: (statement_block) @method.body) @method.def
                (function_declaration
                    name: (identifier) @method.name
                    parameters: (formal_parameters) @method.params
                    body: (statement_block) @method.body) @method.def
            ]
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
                        method_data["params"] = self._extract_js_parameters(param_node)
                        break

                # Extract method body
                body_nodes = captures.get("method.body", [])
                for body_node in body_nodes:
                    if self._is_node_within(body_node, method_node):
                        method_data["body"] = body_node
                        break

                methods.append(self._create_js_function_element(method_data))

        return methods