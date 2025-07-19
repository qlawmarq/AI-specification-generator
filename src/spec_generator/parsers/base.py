"""
Base classes for tree-sitter based code parsing.

This module provides the foundation classes used by all language-specific parsers.
"""

import importlib
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import tree_sitter

from ..models import ClassStructure, Language

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
        }

        try:
            module_name = language_map[language]
            # PATTERN: Dynamic import with error handling
            module = importlib.import_module(module_name)

            # CRITICAL: Handle different API structures for different languages
            # Reason: tree-sitter-typescript uses language_typescript() instead of
            # language()
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

    @abstractmethod
    def extract_class_structures(
        self, root_node: tree_sitter.Node, file_path: str
    ) -> list[ClassStructure]:
        """Extract complete class structures with method relationships."""
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