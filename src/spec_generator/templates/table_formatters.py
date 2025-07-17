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

    def format_method_list(self, methods: list[str]) -> str:
        """Format method list with length constraints.

        Args:
            methods: List of method names to format

        Returns:
            Formatted method string with length constraints
        """
        if not methods:
            return "未定義"

        # Take only the maximum allowed methods
        truncated = methods[:self.settings.max_methods_per_cell]
        result = self.settings.method_separator.join(truncated)

        # Check if content was truncated due to method count or length
        was_truncated_by_count = len(methods) > self.settings.max_methods_per_cell
        original_length = len(result)
        
        # Check if result exceeds maximum cell length
        if len(result) > self.settings.max_cell_length:
            # Try to truncate gracefully at word boundaries
            result = self._truncate_at_separator(result)

        # Add truncation suffix if content was truncated
        was_truncated_by_length = len(result) < original_length
        if was_truncated_by_count or was_truncated_by_length:
            if not result.endswith(self.settings.truncation_suffix):
                # Ensure we have space for the suffix
                max_content_length = (
                    self.settings.max_cell_length -
                    len(self.settings.truncation_suffix)
                )
                if len(result) > max_content_length:
                    result = result[:max_content_length]
                result += self.settings.truncation_suffix

        return result

    def format_class_name(self, name: str) -> str:
        """Format class name with length constraints.

        Args:
            name: Class name to format

        Returns:
            Formatted class name
        """
        if not name:
            return "未定義"

        max_length = 30  # Class name column limit
        if len(name) > max_length:
            return name[:max_length - 3] + "..."
        return name

    def format_role_description(self, role: str) -> str:
        """Format role description with length constraints.

        Args:
            role: Role description to format

        Returns:
            Formatted role description
        """
        if not role:
            return "未定義"

        max_length = 50  # Role column limit
        if len(role) > max_length:
            # Try to truncate at sentence boundaries
            return self._truncate_japanese_text(role, max_length)
        return role

    def format_remarks(self, remarks: str) -> str:
        """Format remarks with length constraints.

        Args:
            remarks: Remarks text to format

        Returns:
            Formatted remarks
        """
        if not remarks:
            return "なし"

        max_length = 40  # Remarks column limit
        if len(remarks) > max_length:
            return self._truncate_japanese_text(remarks, max_length)
        return remarks

    def truncate_content(self, content: str, max_length: Optional[int] = None) -> str:
        """Truncate content with character awareness.

        Args:
            content: Content to truncate
            max_length: Maximum length (uses default if not provided)

        Returns:
            Truncated content
        """
        if not content:
            return ""

        max_len = max_length or self.settings.max_cell_length
        if len(content) <= max_len:
            return content

        return self._truncate_japanese_text(content, max_len)

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
            # Use structured validation
            row = ClassMethodTableRow(
                class_name=self.format_class_name(class_name),
                role=self.format_role_description(role),
                main_methods=methods,
                remarks=self.format_remarks(remarks)
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

    def _is_japanese_char(self, char: str) -> bool:
        """Check if character is Japanese.

        Args:
            char: Character to check

        Returns:
            True if character is Japanese
        """
        # Basic character ranges
        return bool(re.match(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', char))

