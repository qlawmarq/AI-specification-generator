"""
Tree-sitter parser wrapper for extracting semantic elements from code.

This module provides a unified interface for parsing code using Tree-sitter
and extracting functions, classes, and other semantic elements.
"""

import logging

from ..models import ClassStructure, Language
from .base import LanguageParser, SemanticElement
from .languages import CParser, CppParser, JavaParser, JavaScriptParser, PythonParser

logger = logging.getLogger(__name__)


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

        try:
            self._parsers[Language.JAVA] = JavaParser()
            logger.info("Initialized Java parser")
        except Exception as e:
            logger.warning(f"Failed to initialize Java parser: {e}")

        # C parser temporarily disabled due to version compatibility issues
        # try:
        #     self._parsers[Language.C] = CParser()
        #     logger.info("Initialized C parser")
        # except Exception as e:
        #     logger.warning(f"Failed to initialize C parser: {e}")

        try:
            self._parsers[Language.CPP] = CppParser()
            logger.info("Initialized C++ parser")
        except Exception as e:
            logger.warning(f"Failed to initialize C++ parser: {e}")

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

    def extract_class_structures(
        self, file_path: str, language: Language
    ) -> list[ClassStructure]:
        """Extract complete class structures from a file."""
        if language not in self._parsers:
            logger.warning(f"Language {language.value} is not supported")
            return []

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            parser = self._parsers[language]
            tree = parser.parser.parse(content)
            class_structures = parser.extract_class_structures(
                tree.root_node, file_path
            )

            logger.debug(
                f"Extracted {len(class_structures)} class structures from {file_path}"
            )
            return class_structures
        except Exception as e:
            logger.error(f"Error extracting class structures from {file_path}: {e}")
            return []