"""
AST analysis engine for extracting semantic information from code.

This module provides higher-level analysis capabilities on top of the
Tree-sitter parser to extract dependencies, relationships, and structural
information from codebases.
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from ..models import CodeChunk, Language
from .tree_sitter_parser import SemanticElement, TreeSitterParser

logger = logging.getLogger(__name__)


class DependencyInfo:
    """Information about dependencies in code."""

    def __init__(self, name: str, import_type: str, source: Optional[str] = None):
        self.name = name
        self.import_type = import_type  # module, function, class, variable
        self.source = source  # Source module/file

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "type": self.import_type,
            "source": self.source,
        }


class ModuleInfo:
    """Information about a code module/file."""

    def __init__(self, file_path: Path, language: Language):
        self.file_path = file_path
        self.language = language
        self.elements: list[SemanticElement] = []
        self.dependencies: list[DependencyInfo] = []
        self.exports: list[str] = []
        self.complexity_score: float = 0.0
        self.line_count: int = 0

    def add_element(self, element: SemanticElement) -> None:
        """Add a semantic element to this module."""
        self.elements.append(element)

    def get_functions(self) -> list[SemanticElement]:
        """Get all function elements in this module."""
        return [el for el in self.elements if el.element_type == "function"]

    def get_classes(self) -> list[SemanticElement]:
        """Get all class elements in this module."""
        return [el for el in self.elements if el.element_type == "class"]

    def calculate_complexity(self) -> float:
        """Calculate complexity score for this module."""
        # Simple complexity calculation based on element count and nesting
        function_count = len(self.get_functions())
        class_count = len(self.get_classes())

        # Base complexity
        complexity = function_count * 1.0 + class_count * 2.0

        # Add complexity for each element based on size
        for element in self.elements:
            lines = element.end_line - element.start_line
            if lines > 50:  # Large function/class
                complexity += 2.0
            elif lines > 20:  # Medium function/class
                complexity += 1.0

        self.complexity_score = complexity
        return complexity

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "file_path": str(self.file_path),
            "language": self.language.value,
            "elements": [el.to_dict() for el in self.elements],
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "exports": self.exports,
            "complexity_score": self.complexity_score,
            "line_count": self.line_count,
        }


class ASTAnalyzer:
    """AST analyzer for extracting semantic information from codebases."""

    def __init__(self):
        self.parser = TreeSitterParser()
        self.modules: dict[str, ModuleInfo] = {}
        self.dependency_graph: dict[str, set[str]] = defaultdict(set)

    def analyze_file(self, file_path: Path, language: Language) -> Optional[ModuleInfo]:
        """
        Analyze a single file and extract semantic information.

        Args:
            file_path: Path to the file to analyze.
            language: Programming language of the file.

        Returns:
            ModuleInfo containing analysis results, or None if analysis failed.
        """
        try:
            # Parse the file using Tree-sitter
            elements = self.parser.parse_file(str(file_path), language)

            # Create module info
            module_info = ModuleInfo(file_path, language)

            # Add elements to module
            for element in elements:
                module_info.add_element(element)

            # Extract dependencies
            module_info.dependencies = self._extract_dependencies(file_path, language)

            # Extract exports (for supported languages)
            module_info.exports = self._extract_exports(file_path, language)

            # Calculate complexity
            module_info.calculate_complexity()

            # Count lines
            module_info.line_count = self._count_lines(file_path)

            # Store in modules dict
            self.modules[str(file_path)] = module_info

            logger.debug(
                f"Analyzed {file_path}: {len(elements)} elements, "
                f"complexity {module_info.complexity_score:.1f}"
            )

            return module_info

        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            return None

    def analyze_directory(
        self,
        directory: Path,
        supported_languages: list[Language],
        exclude_patterns: list[str] = None,
    ) -> dict[str, ModuleInfo]:
        """
        Analyze all files in a directory.

        Args:
            directory: Directory to analyze.
            supported_languages: List of languages to analyze.
            exclude_patterns: Patterns to exclude from analysis.

        Returns:
            Dictionary mapping file paths to ModuleInfo objects.
        """
        exclude_patterns = exclude_patterns or []

        # Language to file extension mapping
        extension_map = {
            Language.PYTHON: [".py"],
            Language.JAVASCRIPT: [".js", ".jsx"],
            Language.TYPESCRIPT: [".ts", ".tsx"],
            Language.JAVA: [".java"],
            Language.CPP: [".cpp", ".cxx", ".cc", ".hpp", ".h"],
        }

        analyzed_modules = {}

        for language in supported_languages:
            extensions = extension_map.get(language, [])

            for ext in extensions:
                pattern = f"**/*{ext}"

                for file_path in directory.glob(pattern):
                    # Check if file should be excluded
                    if self._should_exclude_file(file_path, exclude_patterns):
                        continue

                    module_info = self.analyze_file(file_path, language)
                    if module_info:
                        analyzed_modules[str(file_path)] = module_info

        # Build dependency graph
        self._build_dependency_graph()

        logger.info(f"Analyzed {len(analyzed_modules)} files in {directory}")
        return analyzed_modules

    def get_module_dependencies(self, module_path: str) -> list[str]:
        """Get list of modules that the given module depends on."""
        return list(self.dependency_graph.get(module_path, set()))

    def get_module_dependents(self, module_path: str) -> list[str]:
        """Get list of modules that depend on the given module."""
        dependents = []
        for path, deps in self.dependency_graph.items():
            if module_path in deps:
                dependents.append(path)
        return dependents

    def get_complexity_report(self) -> dict[str, Any]:
        """Generate a complexity report for all analyzed modules."""
        if not self.modules:
            return {}

        complexities = [module.complexity_score for module in self.modules.values()]
        total_complexity = sum(complexities)
        avg_complexity = total_complexity / len(complexities) if complexities else 0
        max_complexity = max(complexities) if complexities else 0

        # Find most complex modules
        complex_modules = sorted(
            self.modules.items(), key=lambda x: x[1].complexity_score, reverse=True
        )[:10]

        return {
            "total_modules": len(self.modules),
            "total_complexity": total_complexity,
            "average_complexity": avg_complexity,
            "max_complexity": max_complexity,
            "most_complex_modules": [
                {"path": path, "complexity": module.complexity_score}
                for path, module in complex_modules
            ],
        }

    def create_code_chunks(
        self, chunk_size: int = 4000, chunk_overlap: int = 200
    ) -> list[CodeChunk]:
        """
        Create code chunks from analyzed modules.

        Args:
            chunk_size: Maximum size of each chunk in characters.
            chunk_overlap: Overlap between chunks in characters.

        Returns:
            List of CodeChunk objects.
        """
        chunks = []

        for _module_path, module_info in self.modules.items():
            # Create chunks for each semantic element
            for element in module_info.elements:
                chunk = CodeChunk(
                    content=element.content,
                    file_path=module_info.file_path,
                    language=module_info.language,
                    start_line=element.start_line,
                    end_line=element.end_line,
                    chunk_type=element.element_type,
                )
                chunks.append(chunk)

        return chunks

    def _extract_dependencies(
        self, file_path: Path, language: Language
    ) -> list[DependencyInfo]:
        """Extract dependencies from a file."""
        dependencies = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if language == Language.PYTHON:
                dependencies = self._extract_python_dependencies(content)
            elif language in [Language.JAVASCRIPT, Language.TYPESCRIPT]:
                dependencies = self._extract_js_dependencies(content)

        except Exception as e:
            logger.warning(f"Failed to extract dependencies from {file_path}: {e}")

        return dependencies

    def _extract_python_dependencies(self, content: str) -> list[DependencyInfo]:
        """Extract Python import statements."""
        dependencies = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("import "):
                # Handle: import module
                module = line[7:].split(".")[0].strip()
                dependencies.append(DependencyInfo(module, "module"))
            elif line.startswith("from "):
                # Handle: from module import something
                parts = line.split(" import ")
                if len(parts) == 2:
                    module = parts[0][5:].strip()
                    imported = parts[1].split(",")[0].strip()
                    dependencies.append(DependencyInfo(imported, "function", module))

        return dependencies

    def _extract_js_dependencies(self, content: str) -> list[DependencyInfo]:
        """Extract JavaScript/TypeScript import statements."""
        dependencies = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("import "):
                # Handle various import patterns
                if " from " in line:
                    # import { something } from 'module'
                    module_part = line.split(" from ")[-1].strip().strip("'\"")
                    dependencies.append(DependencyInfo(module_part, "module"))
            elif line.startswith("const ") and "require(" in line:
                # const module = require('module')
                start = line.find("require('") + 9
                end = line.find("')", start)
                if start > 8 and end > start:
                    module = line[start:end]
                    dependencies.append(DependencyInfo(module, "module"))

        return dependencies

    def _extract_exports(self, file_path: Path, language: Language) -> list[str]:
        """Extract exports from a file."""
        exports = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            if language == Language.PYTHON:
                # Look for __all__ definition
                if "__all__" in content:
                    # Simple extraction - could be improved
                    exports.append("__all__")
            elif language in [Language.JAVASCRIPT, Language.TYPESCRIPT]:
                # Look for export statements
                lines = content.split("\n")
                for line in lines:
                    line = line.strip()
                    if line.startswith("export "):
                        exports.append(line)

        except Exception as e:
            logger.warning(f"Failed to extract exports from {file_path}: {e}")

        return exports

    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    def _should_exclude_file(
        self, file_path: Path, exclude_patterns: list[str]
    ) -> bool:
        """Check if a file should be excluded based on patterns."""
        path_str = str(file_path)

        for pattern in exclude_patterns:
            # Simple pattern matching - could use fnmatch for more complex patterns
            if pattern.replace("*", "") in path_str:
                return True

        return False

    def _build_dependency_graph(self) -> None:
        """Build dependency graph from analyzed modules."""
        self.dependency_graph.clear()

        for module_path, module_info in self.modules.items():
            for dep in module_info.dependencies:
                # Try to resolve dependency to actual file path
                resolved_path = self._resolve_dependency(dep, module_info.file_path)
                if resolved_path:
                    self.dependency_graph[module_path].add(resolved_path)

    def _resolve_dependency(
        self, dependency: DependencyInfo, current_file: Path
    ) -> Optional[str]:
        """Resolve a dependency to an actual file path."""
        # Simple resolution - could be improved

        # Try common patterns
        for module_path in self.modules.keys():
            module_name = Path(module_path).stem
            if dependency.name == module_name or dependency.source == module_name:
                return module_path

        return None
