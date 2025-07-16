"""
Specification Updater for incremental specification updates.

This module provides the SpecificationUpdater that can merge semantic changes
into existing specification documents while preserving structure and content.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..models import (
    ProcessingStats,
    SemanticChange,
    SpecificationConfig,
    SpecificationOutput,
)
from ..templates.japanese_spec import (
    JapaneseSpecificationTemplate,
)
from ..templates.prompts import PromptTemplates
from .generator import LLMProvider, SpecificationGenerator

logger = logging.getLogger(__name__)


class DocumentSection:
    """Represents a section in a specification document."""

    def __init__(
        self, title: str, content: str, level: int, start_line: int, end_line: int
    ):
        self.title = title
        self.content = content
        self.level = level  # Header level (1-6)
        self.start_line = start_line
        self.end_line = end_line
        self.subsections: list[DocumentSection] = []
        self.updated = False

    def add_subsection(self, subsection: "DocumentSection"):
        """Add a subsection to this section."""
        self.subsections.append(subsection)

    def find_subsection(self, title_pattern: str) -> Optional["DocumentSection"]:
        """Find subsection by title pattern."""
        for subsection in self.subsections:
            if re.search(title_pattern, subsection.title, re.IGNORECASE):
                return subsection
            # Recursive search
            found = subsection.find_subsection(title_pattern)
            if found:
                return found
        return None

    def to_markdown(self) -> str:
        """Convert section back to markdown."""
        header = "#" * self.level + " " + self.title + "\n\n"
        content = self.content

        # Add subsections
        for subsection in self.subsections:
            content += "\n" + subsection.to_markdown()

        return header + content


class DocumentParser:
    """Parses specification documents into structured sections."""

    def __init__(self):
        self.sections: list[DocumentSection] = []

    def parse_document(self, content: str) -> list[DocumentSection]:
        """Parse markdown document into sections."""
        lines = content.split("\n")
        self.sections = []
        current_sections = []  # Stack for nested sections

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for headers
            if line.startswith("#"):
                header_match = re.match(r"^(#{1,6})\s+(.+)", line)
                if header_match:
                    level = len(header_match.group(1))
                    title = header_match.group(2).strip()

                    # Find content until next header of same or higher level
                    content_lines = []
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j]
                        if next_line.startswith("#"):
                            next_header_match = re.match(r"^(#{1,6})", next_line)
                            if next_header_match:
                                next_level = len(next_header_match.group(1))
                                if next_level <= level:
                                    break
                        content_lines.append(next_line)
                        j += 1

                    content = "\n".join(content_lines).strip()
                    section = DocumentSection(title, content, level, i, j - 1)

                    # Handle nesting
                    while current_sections and current_sections[-1].level >= level:
                        current_sections.pop()

                    if current_sections:
                        current_sections[-1].add_subsection(section)
                    else:
                        self.sections.append(section)

                    current_sections.append(section)
                    i = j - 1

            i += 1

        return self.sections


class ChangeAnalyzer:
    """Analyzes semantic changes and determines update strategies."""

    def __init__(self):
        self.change_patterns = {
            "function_added": r"関数|メソッド|function",
            "class_added": r"クラス|class",
            "module_added": r"モジュール|module",
            "api_changed": r"API|インターフェース|interface",
            "data_structure_changed": r"データ構造|data structure",
            "architecture_changed": r"アーキテクチャ|architecture|構成",
        }

    def analyze_changes(self, changes: list[SemanticChange]) -> dict[str, Any]:
        """Analyze changes and categorize them."""
        analysis = {
            "total_changes": len(changes),
            "by_type": {},
            "by_impact": {"low": [], "medium": [], "high": []},
            "affected_sections": set(),
            "update_strategy": {},
            "requires_full_regeneration": False,
        }

        for change in changes:
            # Count by type
            change_type = change.change_type
            analysis["by_type"][change_type] = (
                analysis["by_type"].get(change_type, 0) + 1
            )

            # Categorize by impact
            if change.impact_score < 3.0:
                analysis["by_impact"]["low"].append(change)
            elif change.impact_score < 7.0:
                analysis["by_impact"]["medium"].append(change)
            else:
                analysis["by_impact"]["high"].append(change)

            # Determine affected sections
            affected_sections = self._determine_affected_sections(change)
            analysis["affected_sections"].update(affected_sections)

            # Determine update strategy for this change
            strategy = self._determine_update_strategy(change)
            if change.element_name not in analysis["update_strategy"]:
                analysis["update_strategy"][change.element_name] = []
            analysis["update_strategy"][change.element_name].append(strategy)

        # Check if full regeneration is needed
        high_impact_count = len(analysis["by_impact"]["high"])
        total_changes = analysis["total_changes"]

        if high_impact_count > 5 or total_changes > 20:
            analysis["requires_full_regeneration"] = True

        return analysis

    def _determine_affected_sections(self, change: SemanticChange) -> set[str]:
        """Determine which document sections are affected by a change."""
        affected = set()

        # Always affects detailed design
        affected.add("詳細設計")

        # Specific sections based on element type
        if change.element_type == "function":
            affected.add("モジュール設計")
            affected.add("処理設計")
        elif change.element_type == "class":
            affected.add("モジュール設計")
            affected.add("データ設計")

        # High impact changes affect architecture
        if change.impact_score > 7.0:
            affected.add("システム構成")
            affected.add("非機能要件")

        return affected

    def _determine_update_strategy(self, change: SemanticChange) -> str:
        """Determine update strategy for a specific change."""
        if change.change_type == "added":
            return "add_section"
        elif change.change_type == "removed":
            return "remove_section"
        elif change.change_type == "modified":
            if change.impact_score > 5.0:
                return "replace_section"
            else:
                return "update_section"
        else:
            return "update_section"


class SpecificationUpdater:
    """
    Updates existing specification documents with semantic changes.

    Provides incremental updates that preserve document structure while
    incorporating new changes detected through semantic diff analysis.
    """

    def __init__(self, config: SpecificationConfig):
        self.config = config
        self.llm_provider = LLMProvider(config)
        self.generator = SpecificationGenerator(config)
        self.parser = DocumentParser()
        self.analyzer = ChangeAnalyzer()
        self.template = JapaneseSpecificationTemplate("更新された仕様書")

        logger.info("SpecificationUpdater initialized")

    async def update_specification(
        self,
        existing_spec_path: Path,
        changes: list[SemanticChange],
        output_path: Optional[Path] = None,
    ) -> SpecificationOutput:
        """
        Update existing specification with semantic changes.

        Args:
            existing_spec_path: Path to existing specification document.
            changes: List of semantic changes to incorporate.
            output_path: Optional output path for updated specification.

        Returns:
            SpecificationOutput with updated document.
        """
        try:
            logger.info(f"Updating specification with {len(changes)} changes")

            # Read existing specification
            existing_content = self._read_existing_specification(existing_spec_path)

            # Analyze changes
            change_analysis = self.analyzer.analyze_changes(changes)

            # Check if full regeneration is needed
            if change_analysis["requires_full_regeneration"]:
                logger.info("Full regeneration required due to extensive changes")
                return await self._full_regeneration(changes, output_path)

            # Parse existing document
            sections = self.parser.parse_document(existing_content)

            # Apply incremental updates
            updated_sections = await self._apply_incremental_updates(
                sections, changes, change_analysis
            )

            # Reconstruct document
            updated_content = self._reconstruct_document(updated_sections, changes)

            # Create output
            output = self._create_update_output(
                updated_content, changes, existing_spec_path
            )

            # Save if path provided
            if output_path:
                await self._save_updated_specification(output, output_path)

            logger.info("Specification update completed")
            return output

        except Exception as e:
            logger.error(f"Specification update failed: {e}")
            raise

    def _read_existing_specification(self, spec_path: Path) -> str:
        """Read existing specification document."""
        try:
            with open(spec_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read existing specification: {e}")
            raise

    async def _apply_incremental_updates(
        self,
        sections: list[DocumentSection],
        changes: list[SemanticChange],
        analysis: dict[str, Any],
    ) -> list[DocumentSection]:
        """Apply incremental updates to document sections."""
        updated_sections = sections.copy()

        # Group changes by affected sections
        section_changes = {}
        for change in changes:
            affected_sections = self.analyzer._determine_affected_sections(change)
            for section_name in affected_sections:
                if section_name not in section_changes:
                    section_changes[section_name] = []
                section_changes[section_name].append(change)

        # Update each affected section
        for section_name, section_change_list in section_changes.items():
            section = self._find_section_by_name(updated_sections, section_name)
            if section:
                await self._update_section(section, section_change_list)

        return updated_sections

    def _find_section_by_name(
        self, sections: list[DocumentSection], name: str
    ) -> Optional[DocumentSection]:
        """Find section by name pattern."""
        for section in sections:
            if re.search(name, section.title, re.IGNORECASE):
                return section
            # Search subsections recursively
            found = section.find_subsection(name)
            if found:
                return found
        return None

    async def _update_section(
        self, section: DocumentSection, changes: list[SemanticChange]
    ):
        """Update a specific section with changes."""
        try:
            # Create change summary for this section
            change_summary = self._create_section_change_summary(changes)

            # Generate update prompt using template
            update_prompt = PromptTemplates.SECTION_UPDATE_PROMPT.format(
                section_content=section.content, change_summary=change_summary
            )

            # Generate updated content
            updated_content = await self.llm_provider.generate(update_prompt)

            # Update section
            section.content = updated_content.strip()
            section.updated = True

            logger.debug(f"Updated section: {section.title}")

        except Exception as e:
            logger.warning(f"Failed to update section {section.title}: {e}")

    def _create_section_change_summary(self, changes: list[SemanticChange]) -> str:
        """Create summary of changes for a section."""
        summary_parts = []

        for change in changes:
            change_desc = f"- **{change.element_name}** ({change.element_type}): {change.change_type}"
            if change.impact_score > 5.0:
                change_desc += f" (高影響度: {change.impact_score:.1f})"
            summary_parts.append(change_desc)

        return "\n".join(summary_parts)

    def _reconstruct_document(
        self, sections: list[DocumentSection], changes: list[SemanticChange]
    ) -> str:
        """Reconstruct document from updated sections."""
        document_parts = []

        # Add document header with update information
        document_parts.append(self._create_update_header(changes))

        # Add sections
        for section in sections:
            document_parts.append(section.to_markdown())

        # Add change history
        document_parts.append(self._create_change_history_section(changes))

        return "\n\n".join(document_parts)

    def _create_update_header(self, changes: list[SemanticChange]) -> str:
        """Create header for updated document."""
        update_date = datetime.now().strftime("%Y年%m月%d日")
        change_count = len(changes)

        return f"""# 更新された仕様書

**最終更新日**: {update_date}
**更新内容**: {change_count}件の変更を反映

---"""

    def _create_change_history_section(self, changes: list[SemanticChange]) -> str:
        """Create change history section."""
        update_date = datetime.now().strftime("%Y-%m-%d")

        change_rows = []
        for change in changes:
            impact_level = (
                "高"
                if change.impact_score > 7.0
                else "中" if change.impact_score > 3.0 else "低"
            )
            change_rows.append(
                f"| {update_date} | {change.element_name} | {change.change_type} | {impact_level} |"
            )

        return f"""## 変更履歴

| 日付 | 要素名 | 変更種別 | 影響度 |
|------|--------|----------|--------|
{chr(10).join(change_rows)}

---"""

    async def _full_regeneration(
        self, changes: list[SemanticChange], output_path: Optional[Path]
    ) -> SpecificationOutput:
        """Perform full regeneration when incremental update is not suitable."""
        logger.info("Performing full specification regeneration")

        # This would require re-analyzing the entire codebase
        # For now, return a placeholder indicating full regeneration is needed
        placeholder_content = f"""# 仕様書全体の再生成が必要

**理由**: 変更が広範囲にわたるため、仕様書全体の再生成が推奨されます。

**変更数**: {len(changes)}件
**高影響度変更**: {sum(1 for c in changes if c.impact_score > 7.0)}件

完全な仕様書を生成するには、`generate` コマンドを使用してください。

## 検出された変更

{self._create_section_change_summary(changes)}
"""

        return SpecificationOutput(
            title="仕様書再生成要求",
            content=placeholder_content,
            language="ja",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            source_files=[],
            processing_stats=ProcessingStats(),
            metadata={"requires_full_regeneration": True, "change_count": len(changes)},
        )

    def _create_update_output(
        self, content: str, changes: list[SemanticChange], source_path: Path
    ) -> SpecificationOutput:
        """Create SpecificationOutput for updated document."""
        stats = ProcessingStats()
        stats.files_processed = 1
        stats.chunks_created = len(changes)

        return SpecificationOutput(
            title="更新された仕様書",
            content=content,
            language="ja",
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            source_files=[source_path],
            processing_stats=stats,
            metadata={
                "update_type": "incremental",
                "change_count": len(changes),
                "source_document": str(source_path),
            },
        )

    async def _save_updated_specification(
        self, output: SpecificationOutput, output_path: Path
    ):
        """Save updated specification to file."""
        try:
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write specification
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output.content)

            # Log metadata information instead of writing to file
            logger.info(f"Updated specification saved to {output_path}")
            logger.info(f"Title: {output.title}")
            logger.info(f"Created at: {output.created_at}")
            logger.info(f"Processing stats: Files processed: {output.processing_stats.files_processed}, "
                       f"Lines processed: {output.processing_stats.lines_processed}, "
                       f"Chunks created: {output.processing_stats.chunks_created}, "
                       f"Processing time: {output.processing_stats.processing_time_seconds:.2f}s")
            if output.metadata:
                logger.info(f"Update metadata: {output.metadata}")

        except Exception as e:
            logger.error(f"Failed to save updated specification: {e}")
            raise

    def merge_specifications(
        self, base_spec_path: Path, update_spec_path: Path, output_path: Path
    ) -> None:
        """Merge two specification documents."""
        try:
            # Read both specifications
            with open(base_spec_path, encoding="utf-8") as f:
                base_content = f.read()

            with open(update_spec_path, encoding="utf-8") as f:
                update_content = f.read()

            # Parse both documents
            base_sections = self.parser.parse_document(base_content)
            update_sections = self.parser.parse_document(update_content)

            # Merge sections (simplified approach)
            merged_sections = self._merge_sections(base_sections, update_sections)

            # Reconstruct document
            merged_content = self._reconstruct_merged_document(merged_sections)

            # Write merged document
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(merged_content)

            logger.info(f"Specifications merged and saved to {output_path}")

        except Exception as e:
            logger.error(f"Failed to merge specifications: {e}")
            raise

    def _merge_sections(
        self,
        base_sections: list[DocumentSection],
        update_sections: list[DocumentSection],
    ) -> list[DocumentSection]:
        """Merge sections from two documents."""
        merged = base_sections.copy()

        for update_section in update_sections:
            # Find corresponding section in base
            base_section = self._find_section_by_name(merged, update_section.title)

            if base_section:
                # Update existing section
                base_section.content = update_section.content
                base_section.updated = True
            else:
                # Add new section
                merged.append(update_section)

        return merged

    def _reconstruct_merged_document(self, sections: list[DocumentSection]) -> str:
        """Reconstruct merged document."""
        document_parts = []

        # Add header
        merge_date = datetime.now().strftime("%Y年%m月%d日")
        document_parts.append(
            f"""# 統合された仕様書

**統合日**: {merge_date}

---"""
        )

        # Add sections
        for section in sections:
            document_parts.append(section.to_markdown())

        return "\n\n".join(document_parts)
