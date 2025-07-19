"""
Table formatting utilities for specification generation.

This module provides utilities for formatting table content with proper length
constraints to ensure readable markdown table output.
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ..models import TableFormattingSettings


class TableCellContent(BaseModel):
    """Validated table cell content with length constraints."""

    content: str = Field(..., description="Table cell content")

    @field_validator('content')
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Validate and truncate content if needed."""
        if len(v) > 80:
            return v[:77] + "..."
        return v


class ClassMethodTableRow(BaseModel):
    """Structured row for class/method table with validation."""

    class_name: str = Field(..., description="Class or function name")
    role: str = Field(..., description="Purpose/role description")
    main_methods: list[str] = Field(
        ..., description="List of main methods"
    )
    remarks: str = Field(..., description="Additional remarks")
    original_method_count: int = Field(default=0, description="Original method count before truncation")

    @field_validator('class_name')
    @classmethod
    def validate_class_name(cls, v: str) -> str:
        """Validate class name length."""
        if len(v) > 30:
            return v[:27] + "..."
        return v

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role description length."""
        if len(v) > 50:
            return v[:47] + "..."
        return v

    @field_validator('remarks')
    @classmethod
    def validate_remarks(cls, v: str) -> str:
        """Validate remarks length."""
        if len(v) > 40:
            return v[:37] + "..."
        return v

    @field_validator('main_methods')
    @classmethod
    def validate_main_methods(cls, v: list[str]) -> list[str]:
        """Validate method list length."""
        if len(v) > 5:
            return v[:5]
        return v
        
    def __init__(self, **data):
        """Initialize and store original method count."""
        if 'main_methods' in data:
            data['original_method_count'] = len(data['main_methods'])
        super().__init__(**data)

    def to_table_row(self) -> str:
        """Convert to markdown table row with proper formatting."""
        methods_str = ", ".join(self.main_methods[:5])
        if self.original_method_count > 5:
            methods_str += "..."

        # Ensure methods cell doesn't exceed length
        if len(methods_str) > 80:
            methods_str = methods_str[:77] + "..."

        return f"| {self.class_name} | {self.role} | {methods_str} | {self.remarks} |"


class TableFormatter:
    """Utility class for formatting table content with length constraints."""

    def __init__(self, settings: Optional[TableFormattingSettings] = None):
        """Initialize table formatter with configuration settings."""
        self.settings = settings or TableFormattingSettings()






    def create_table_row(
        self,
        class_name: str,
        role: str,
        methods: list[str],
        remarks: str
    ) -> str:
        """Create a properly formatted table row.

        Args:
            class_name: Class or function name
            role: Purpose/role description
            methods: List of method names
            remarks: Additional remarks

        Returns:
            Formatted markdown table row
        """
        try:
            # Use structured validation directly
            row = ClassMethodTableRow(
                class_name=class_name,
                role=role,
                main_methods=methods,
                remarks=remarks
            )
            return row.to_table_row()
        except Exception:
            # Fallback to safe defaults
            return "| 解析エラー | 未定義 | 未定義 | エラー |"

    def _truncate_at_separator(self, text: str) -> str:
        """Truncate text at the last separator to avoid cutting method names.

        Args:
            text: Text to truncate

        Returns:
            Truncated text at separator boundary
        """
        max_length = (
            self.settings.max_cell_length -
            len(self.settings.truncation_suffix)
        )

        if len(text) <= max_length:
            return text

        # Find the last separator within the limit
        separator = self.settings.method_separator
        last_sep_index = text.rfind(separator, 0, max_length)

        if last_sep_index > 0:
            return text[:last_sep_index]
        else:
            # No separator found, just truncate
            return text[:max_length]

    def _truncate_japanese_text(self, text: str, max_length: int) -> str:
        """Truncate text while preserving character integrity.

        Args:
            text: text to truncate
            max_length: Maximum length

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text

        # Account for truncation suffix
        suffix = self.settings.truncation_suffix
        max_content_length = max_length - len(suffix)

        if max_content_length <= 0:
            return suffix

        # For text, try to break at word boundaries
        if self.settings.preserve_japanese:
            # Simple approach: break at punctuation if possible
            japanese_punct = r'[。、！？]'
            matches = list(re.finditer(japanese_punct, text[:max_content_length]))

            if matches and matches[-1].end() < max_content_length:
                return text[:matches[-1].end()] + suffix

        # Fallback: simple truncation
        return text[:max_content_length] + suffix


