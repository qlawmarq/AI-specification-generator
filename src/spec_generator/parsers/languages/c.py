"""C language parser implementation."""

import logging

import tree_sitter

from ...models import ClassStructure, Language
from ..base import LanguageParser, SemanticElement

logger = logging.getLogger(__name__)


class CParser(LanguageParser):
    """Parser for C code."""

    def __init__(self) -> None:
        super().__init__(Language.C)

    def extract_functions(self, root_node: tree_sitter.Node) -> list[SemanticElement]:
        """Extract C function definitions."""
        query_code = """
        (function_definition
            declarator: (function_declarator
                declarator: (identifier) @function.name
                parameters: (parameter_list) @function.params)
            body: (compound_statement) @function.body) @function.def
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
                    function_data["params"] = self._extract_c_parameters(param_node)
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
        """Extract C struct definitions (C doesn't have classes)."""
        query_code = """
        (struct_specifier
            name: (type_identifier) @struct.name
            body: (field_declaration_list) @struct.body) @struct.def
        """

        query = self.ts_language.query(query_code)
        captures = query.captures(root_node)

        structs = []
        struct_defs = captures.get("struct.def", [])

        for struct_node in struct_defs:
            struct_data = {"node": struct_node}

            # Extract struct name
            name_nodes = captures.get("struct.name", [])
            for name_node in name_nodes:
                if self._is_node_within(name_node, struct_node):
                    struct_data["name"] = self._get_node_text(name_node)
                    break

            # Extract struct body
            body_nodes = captures.get("struct.body", [])
            for body_node in body_nodes:
                if self._is_node_within(body_node, struct_node):
                    struct_data["body"] = body_node
                    break

            structs.append(self._create_struct_element(struct_data))

        return structs

    def _create_function_element(self, func_data: dict) -> SemanticElement:
        """Create a SemanticElement for a C function."""
        node = func_data["node"]
        name = func_data.get("name", "unknown")
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

    def _create_struct_element(self, struct_data: dict) -> SemanticElement:
        """Create a SemanticElement for a C struct."""
        node = struct_data["node"]
        name = struct_data.get("name", "unknown")
        start_line, end_line = self._get_node_location(node)
        content = self._get_node_text(node)

        return SemanticElement(
            name=name,
            element_type="struct",  # Use "struct" instead of "class" for C
            start_line=start_line,
            end_line=end_line,
            content=content,
            node=node,
        )

    def _extract_c_parameters(self, params_node: tree_sitter.Node) -> list[str]:
        """Extract parameter names from C function parameters."""
        if not params_node:
            return []

        parameters = []
        for child in params_node.children:
            if child.type == "parameter_declaration":
                # C parameters have type and name
                for subchild in child.children:
                    if subchild.type == "identifier":
                        parameters.append(self._get_node_text(subchild))

        return parameters

    def extract_class_structures(
        self, root_node: tree_sitter.Node, file_path: str
    ) -> list[ClassStructure]:
        """Extract struct structures (C doesn't have classes)."""
        # For C, we treat structs as "classes" for compatibility
        struct_query = """
        (struct_specifier
            name: (type_identifier) @struct.name
            body: (field_declaration_list) @struct.body) @struct.def
        """

        query = self.ts_language.query(struct_query)
        captures = query.captures(root_node)

        struct_structures = []
        struct_defs = captures.get("struct.def", [])

        for struct_node in struct_defs:
            struct_name = None
            struct_body = None

            # Extract struct name
            name_nodes = captures.get("struct.name", [])
            for name_node in name_nodes:
                if self._is_node_within(name_node, struct_node):
                    struct_name = self._get_node_text(name_node)
                    break

            # Extract struct body
            body_nodes = captures.get("struct.body", [])
            for body_node in body_nodes:
                if self._is_node_within(body_node, struct_node):
                    struct_body = body_node
                    break

            if struct_name and struct_body:
                # Create ClassStructure (representing struct)
                struct_structure = ClassStructure(
                    name=struct_name,
                    methods=[],  # C structs don't have methods
                    attributes=[],  # TODO: Extract fields
                    docstring=None,
                    start_line=struct_node.start_point[0] + 1,
                    end_line=struct_node.end_point[0] + 1,
                    file_path=file_path
                )

                struct_structures.append(struct_structure)

        return struct_structures