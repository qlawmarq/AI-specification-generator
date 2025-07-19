"""
Specification document templates.

This module provides templates for generating IT industry
standard specification documents with proper formatting and structure.
"""

from datetime import datetime
from typing import Any

from .document_sections import DocumentSectionGenerator
from .table_formatters import TableFormatter
from ..models import TableFormattingSettings


class SpecificationTemplate:
    """Template for IT industry specification documents."""

    def __init__(self, project_name: str, version: str = "1.0", config=None):
        self.project_name = project_name
        self.version = version
        self.creation_date = datetime.now().strftime("%Y年%m月%d日")
        
        # Initialize table formatter with configuration
        if config and hasattr(config, 'table_formatting'):
            self.table_formatter = TableFormatter(config.table_formatting)
        else:
            self.table_formatter = TableFormatter(TableFormattingSettings())
            
        # Initialize section generator
        self.section_generator = DocumentSectionGenerator(self.table_formatter)

    def generate_header(self, document_type: str = "詳細設計書") -> str:
        """Generate document header in format."""
        return f"""# {self.project_name} {document_type}

**文書バージョン**: {self.version}
**作成日**: {self.creation_date}
**最終更新日**: {self.creation_date}

---
"""

    def generate_change_history_section(self, changes: list[dict[str, str]]) -> str:
        """Generate change history section."""
        if not changes:
            changes = [
                {
                    "date": self.creation_date,
                    "version": self.version,
                    "description": "初版作成",
                    "author": "システム",
                }
            ]

        change_rows = []
        for change in changes:
            change_rows.append(
                f"| {change.get('date')} | {change.get('version')} | "
                f"{change.get('description')} | {change.get('author')} |"
            )

        return f"""### 変更履歴

| 日付 | バージョン | 変更内容 | 作成者 |
|------|-----------|----------|--------|
{chr(10).join(change_rows)}

"""

    def generate_complete_document(self, document_data: dict[str, Any]) -> str:
        """Generate simplified specification document with 6-section structure."""
        sections = []

        # Header
        sections.append(
            self.generate_header(document_data.get("document_type", "詳細設計書"))
        )

        # Generate all sections using the section generator
        sections.append(self.section_generator.generate_overview_section(document_data))
        sections.append(self.section_generator.generate_architecture_section(document_data))
        sections.append(self.section_generator.generate_class_method_section(document_data))
        sections.append(self.section_generator.generate_interface_section(document_data))
        sections.append(self.section_generator.generate_data_design_section(document_data))
        sections.append(self.section_generator.generate_processing_section(document_data))

        # Change History (preserved for backward compatibility)
        sections.append(
            self.generate_change_history_section(
                document_data.get("change_history", [])
            )
        )

        return "\n\n".join(sections)
