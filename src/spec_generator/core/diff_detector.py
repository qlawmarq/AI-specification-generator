"""
Semantic Diff Detector for analyzing code changes using Tree-sitter AST comparison.

This module provides semantic analysis of code changes by comparing AST structures
between different versions of files, calculating impact scores, and identifying
affected components.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from ..models import Language, SemanticChange, SpecificationConfig
from ..parsers import ASTAnalyzer, SemanticElement, TreeSitterParser
from ..utils.git_utils import GitError, GitOperations

logger = logging.getLogger(__name__)


class ChangeType:
    """Constants for change types."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    RENAMED = "renamed"
    MOVED = "moved"


class ElementComparison:
    """Comparison result between two semantic elements."""

    def __init__(
        self,
        old_element: Optional[SemanticElement],
        new_element: Optional[SemanticElement],
        change_type: str,
        similarity_score: float = 0.0,
    ):
        self.old_element = old_element
        self.new_element = new_element
        self.change_type = change_type
        self.similarity_score = similarity_score
        self.impact_score = 0.0
        self.affected_dependencies: set[str] = set()

    def calculate_impact_score(self) -> float:
        """Calculate impact score based on change characteristics."""
        base_score = 1.0

        # Increase impact based on element type
        element = self.new_element or self.old_element
        if element:
            if element.element_type == "class":
                base_score *= 3.0  # Classes have higher impact
            elif element.element_type == "function":
                base_score *= 2.0  # Functions have medium impact

        # Increase impact for breaking changes
        if self.change_type == ChangeType.REMOVED:
            base_score *= 2.5  # Removals are breaking
        elif self.change_type == ChangeType.MODIFIED:
            # Impact based on how much changed
            base_score *= 1.0 + (1.0 - self.similarity_score)

        # Consider element size
        if element:
            lines = element.end_line - element.start_line
            if lines > 100:  # Large elements have higher impact
                base_score *= 1.5
            elif lines > 50:
                base_score *= 1.2

        # Cap at 10.0
        self.impact_score = min(base_score, 10.0)
        return self.impact_score


class SemanticDiffDetector:
    """
    Detects semantic changes in code using Tree-sitter AST analysis.

    Compares code between different versions (commits) and identifies
    meaningful semantic changes like function additions, modifications,
    and deletions.
    """

    def __init__(self, config: SpecificationConfig, repo_path: Optional[Path] = None):
        self.config = config
        self.repo_path = repo_path or Path.cwd()
        self.git_ops = GitOperations(self.repo_path)
        self.parser = TreeSitterParser()
        self.ast_analyzer = ASTAnalyzer()

        # Cache for parsed content
        self._parse_cache: dict[str, list[SemanticElement]] = {}

        logger.info(f"SemanticDiffDetector initialized for {self.repo_path}")

    def detect_changes(
        self,
        base_commit: str = "HEAD~1",
        target_commit: str = "HEAD",
        include_untracked: bool = False,
    ) -> list[SemanticChange]:
        """
        Detect semantic changes between two commits.

        Args:
            base_commit: Base commit for comparison.
            target_commit: Target commit for comparison.
            include_untracked: Whether to include untracked files.

        Returns:
            List of SemanticChange objects.
        """
        try:
            logger.info(f"Detecting changes between {base_commit} and {target_commit}")

            # Get file status mapping for efficient categorization
            file_status_map = self.git_ops.get_file_status_map(
                base_commit, target_commit
            )

            # Get changed files
            changed_files = self.git_ops.get_changed_files(
                base_commit, target_commit, include_untracked
            )

            if not changed_files:
                logger.info("No changed files found")
                return []

            logger.info(f"Analyzing {len(changed_files)} changed files")

            all_changes = []

            for file_path in changed_files:
                try:
                    # Get file status for optimized processing
                    file_status = file_status_map.get(file_path, None)

                    file_changes = self._analyze_file_changes(
                        file_path, base_commit, target_commit, file_status
                    )
                    all_changes.extend(file_changes)
                except Exception as e:
                    logger.error(f"Failed to analyze {file_path}: {e}")
                    continue

            logger.info(f"Found {len(all_changes)} semantic changes")
            return all_changes

        except GitError as e:
            logger.error(f"Git error during change detection: {e}")
            raise
        except Exception as e:
            logger.error(f"Error detecting changes: {e}")
            raise

    def _analyze_file_changes(
        self,
        file_path: str,
        base_commit: str,
        target_commit: str,
        file_status: Optional[str] = None
    ) -> list[SemanticChange]:
        """Analyze changes in a single file with optimized content retrieval."""
        # Check if file is supported
        self.repo_path / file_path

        # Detect language
        language = None
        for lang in self.config.supported_languages:
            if self._is_language_file(file_path, lang):
                language = lang
                break

        if not language:
            logger.debug(f"Skipping unsupported file: {file_path}")
            return []

        # Optimize file content retrieval based on status
        if file_status == "A":  # New file - skip getting old content
            logger.debug(f"Processing new file: {file_path}")
            old_content = None
            new_content = self.git_ops.get_current_file_content(file_path)
        elif file_status == "D":  # Deleted file - skip getting new content
            logger.debug(f"Processing deleted file: {file_path}")
            old_content = self.git_ops.get_file_at_commit(file_path, base_commit)
            new_content = None
        else:  # Modified file or unknown status - use existing logic
            status_desc = 'modified' if file_status == 'M' else 'unknown status'
            logger.debug(f"Processing {status_desc} file: {file_path}")
            old_content = self.git_ops.get_file_at_commit(file_path, base_commit)
            new_content = self.git_ops.get_current_file_content(file_path)

        # Handle file creation/deletion
        if old_content is None and new_content is not None:
            return self._handle_file_creation(file_path, new_content, language)
        elif old_content is not None and new_content is None:
            return self._handle_file_deletion(file_path, old_content, language)
        elif old_content is None and new_content is None:
            return []  # Both versions missing

        # Parse both versions
        old_elements = self._parse_content(
            old_content or "", language, f"{file_path}@{base_commit}"
        )
        new_elements = self._parse_content(
            new_content or "", language, f"{file_path}@{target_commit}"
        )

        # Compare elements
        comparisons = self._compare_element_lists(old_elements, new_elements)

        # Convert to SemanticChange objects
        changes = []
        for comparison in comparisons:
            if comparison.change_type != "unchanged":
                change = self._create_semantic_change(file_path, language, comparison)
                if change:
                    changes.append(change)

        return changes

    def _parse_content(
        self, content: str, language: Language, cache_key: str
    ) -> list[SemanticElement]:
        """Parse content and cache results."""
        if cache_key in self._parse_cache:
            return self._parse_cache[cache_key]

        try:
            elements = self.parser.parse_content(content.encode("utf-8"), language)
            self._parse_cache[cache_key] = elements
            return elements
        except Exception as e:
            logger.warning(f"Failed to parse content for {cache_key}: {e}")
            return []

    def _compare_element_lists(
        self, old_elements: list[SemanticElement], new_elements: list[SemanticElement]
    ) -> list[ElementComparison]:
        """Compare two lists of semantic elements."""
        comparisons = []

        # Create mappings for efficient lookup
        old_by_signature = self._create_element_signature_map(old_elements)
        new_by_signature = self._create_element_signature_map(new_elements)

        # Track processed elements
        processed_new = set()

        # Compare old elements with new elements
        for old_sig, old_element in old_by_signature.items():
            if old_sig in new_by_signature:
                # Element exists in both versions
                new_element = new_by_signature[old_sig]
                processed_new.add(old_sig)

                similarity = self._calculate_similarity(old_element, new_element)

                if similarity < 0.95:  # Consider it modified if less than 95% similar
                    comparison = ElementComparison(
                        old_element, new_element, ChangeType.MODIFIED, similarity
                    )
                else:
                    comparison = ElementComparison(
                        old_element, new_element, "unchanged", similarity
                    )

                comparison.calculate_impact_score()
                comparisons.append(comparison)
            else:
                # Element was removed
                comparison = ElementComparison(old_element, None, ChangeType.REMOVED)
                comparison.calculate_impact_score()
                comparisons.append(comparison)

        # Find new elements
        for new_sig, new_element in new_by_signature.items():
            if new_sig not in processed_new:
                comparison = ElementComparison(None, new_element, ChangeType.ADDED)
                comparison.calculate_impact_score()
                comparisons.append(comparison)

        return comparisons

    def _create_element_signature_map(
        self, elements: list[SemanticElement]
    ) -> dict[str, SemanticElement]:
        """Create a signature-based mapping of elements."""
        signature_map = {}

        for element in elements:
            signature = self._create_element_signature(element)
            signature_map[signature] = element

        return signature_map

    def _create_element_signature(self, element: SemanticElement) -> str:
        """Create a unique signature for an element."""
        # Use name and type as primary signature
        base_signature = f"{element.element_type}:{element.name}"

        # Add parameter info for functions
        if element.parameters:
            params_str = ",".join(element.parameters)
            base_signature += f"({params_str})"

        return base_signature

    def _calculate_similarity(
        self, old_element: SemanticElement, new_element: SemanticElement
    ) -> float:
        """Calculate similarity between two elements."""
        if old_element.name != new_element.name:
            return 0.0

        if old_element.element_type != new_element.element_type:
            return 0.0

        # Compare content using simple text similarity
        old_content = old_element.content
        new_content = new_element.content

        # Use a simple similarity metric based on common lines
        old_lines = set(old_content.splitlines())
        new_lines = set(new_content.splitlines())

        if not old_lines and not new_lines:
            return 1.0

        common_lines = old_lines.intersection(new_lines)
        total_lines = old_lines.union(new_lines)

        similarity = len(common_lines) / len(total_lines) if total_lines else 1.0
        return similarity

    def _create_semantic_change(
        self, file_path: str, language: Language, comparison: ElementComparison
    ) -> Optional[SemanticChange]:
        """Create a SemanticChange from an ElementComparison."""
        element = comparison.new_element or comparison.old_element
        if not element:
            return None

        try:
            change = SemanticChange(
                file_path=Path(file_path),
                change_type=comparison.change_type,
                element_name=element.name,
                element_type=element.element_type,
                impact_score=comparison.impact_score,
                dependencies=list(comparison.affected_dependencies),
            )
            return change
        except Exception as e:
            logger.warning(f"Failed to create SemanticChange: {e}")
            return None

    def _handle_file_creation(
        self, file_path: str, content: str, language: Language
    ) -> list[SemanticChange]:
        """Handle creation of a new file."""
        elements = self._parse_content(content, language, f"{file_path}@new")

        changes = []
        for element in elements:
            change = SemanticChange(
                file_path=Path(file_path),
                change_type=ChangeType.ADDED,
                element_name=element.name,
                element_type=element.element_type,
                impact_score=2.0,  # New files have medium impact
                dependencies=[],
            )
            changes.append(change)

        return changes

    def _handle_file_deletion(
        self, file_path: str, content: str, language: Language
    ) -> list[SemanticChange]:
        """Handle deletion of a file."""
        elements = self._parse_content(content, language, f"{file_path}@deleted")

        changes = []
        for element in elements:
            change = SemanticChange(
                file_path=Path(file_path),
                change_type=ChangeType.REMOVED,
                element_name=element.name,
                element_type=element.element_type,
                impact_score=5.0,  # Deletions have high impact
                dependencies=[],
            )
            changes.append(change)

        return changes

    def _is_language_file(self, file_path: str, language: Language) -> bool:
        """Check if a file matches a specific language."""
        extension_map = {
            Language.PYTHON: [".py", ".pyw", ".pyi"],
            Language.JAVASCRIPT: [".js", ".jsx", ".mjs", ".cjs"],
            Language.TYPESCRIPT: [".ts", ".tsx", ".mts", ".cts"],
            Language.JAVA: [".java"],
            Language.CPP: [".cpp", ".cxx", ".cc", ".hpp", ".hxx", ".hh"],
            Language.C: [".c", ".h"],
        }

        extensions = extension_map.get(language, [])
        file_ext = Path(file_path).suffix.lower()
        return file_ext in extensions

    def get_change_summary(self, changes: list[SemanticChange]) -> dict[str, Any]:
        """Get a summary of changes."""
        if not changes:
            return {"total_changes": 0}

        summary = {
            "total_changes": len(changes),
            "by_type": {},
            "by_element_type": {},
            "by_file": {},
            "impact_distribution": {"low": 0, "medium": 0, "high": 0},
            "average_impact": 0.0,
            "max_impact": 0.0,
        }

        total_impact = 0.0

        for change in changes:
            # Count by change type
            summary["by_type"][change.change_type] = (
                summary["by_type"].get(change.change_type, 0) + 1
            )

            # Count by element type
            summary["by_element_type"][change.element_type] = (
                summary["by_element_type"].get(change.element_type, 0) + 1
            )

            # Count by file
            file_str = str(change.file_path)
            summary["by_file"][file_str] = summary["by_file"].get(file_str, 0) + 1

            # Impact distribution
            if change.impact_score < 3.0:
                summary["impact_distribution"]["low"] += 1
            elif change.impact_score < 7.0:
                summary["impact_distribution"]["medium"] += 1
            else:
                summary["impact_distribution"]["high"] += 1

            total_impact += change.impact_score
            summary["max_impact"] = max(summary["max_impact"], change.impact_score)

        summary["average_impact"] = total_impact / len(changes)

        return summary

    def clear_cache(self) -> None:
        """Clear the parse cache."""
        self._parse_cache.clear()
        logger.debug("Parse cache cleared")
