"""
Comprehensive tests for table formatting functionality.

This module tests table cell content constraints, method list truncation,
Japanese character handling, and integration with the generation pipeline.
"""

import pytest
from pydantic import ValidationError

from src.spec_generator.models import TableFormattingSettings
from src.spec_generator.templates.table_formatters import (
    TableFormatter,
    TableCellContent,
    ClassMethodTableRow,
)
from src.spec_generator.templates.japanese_spec import JapaneseSpecificationTemplate


class TestTableFormattingSettings:
    """Test the table formatting configuration model."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = TableFormattingSettings()
        assert settings.max_cell_length == 80
        assert settings.max_methods_per_cell == 5
        assert settings.method_separator == ", "
        assert settings.truncation_suffix == "..."
        assert settings.preserve_japanese is True

    def test_custom_settings(self):
        """Test custom configuration values."""
        settings = TableFormattingSettings(
            max_cell_length=60,
            max_methods_per_cell=3,
            method_separator=" | ",
            truncation_suffix="...",
            preserve_japanese=False,
        )
        assert settings.max_cell_length == 60
        assert settings.max_methods_per_cell == 3
        assert settings.method_separator == " | "
        assert settings.preserve_japanese is False


class TestTableCellContent:
    """Test table cell content validation."""

    def test_valid_content(self):
        """Test valid content under length limit."""
        content = TableCellContent(content="Valid content")
        assert content.content == "Valid content"

    def test_content_truncation(self):
        """Test content is truncated when over limit."""
        long_content = "A" * 100  # 100 characters
        content = TableCellContent(content=long_content)
        assert len(content.content) <= 80
        assert content.content.endswith("...")

    def test_empty_content(self):
        """Test empty content is allowed."""
        content = TableCellContent(content="")
        assert content.content == ""


class TestClassMethodTableRow:
    """Test structured table row validation."""

    def test_valid_row(self):
        """Test valid table row creation."""
        row = ClassMethodTableRow(
            class_name="Calculator",
            role="数値計算機能",
            main_methods=["add", "subtract", "multiply"],
            remarks="パターン: なし",
        )
        assert row.class_name == "Calculator"
        assert row.role == "数値計算機能"
        assert row.main_methods == ["add", "subtract", "multiply"]
        assert row.remarks == "パターン: なし"

    def test_class_name_truncation(self):
        """Test class name is truncated when too long."""
        long_name = "VeryLongClassNameThatExceedsLimits"
        row = ClassMethodTableRow(
            class_name=long_name,
            role="役割",
            main_methods=["method1"],
            remarks="備考",
        )
        assert len(row.class_name) <= 30
        assert row.class_name.endswith("...")

    def test_role_truncation(self):
        """Test role description is truncated when too long."""
        long_role = "非常に長い役割の説明文で五十文字を確実に超える内容になっている詳細な機能説明テキストであり非常に長い文章"
        row = ClassMethodTableRow(
            class_name="TestClass",
            role=long_role,
            main_methods=["method1"],
            remarks="備考",
        )
        assert len(row.role) <= 50
        assert row.role.endswith("...")

    def test_methods_list_limit(self):
        """Test method list is limited to maximum count."""
        many_methods = [f"method{i}" for i in range(10)]
        row = ClassMethodTableRow(
            class_name="TestClass",
            role="役割",
            main_methods=many_methods,
            remarks="備考",
        )
        assert len(row.main_methods) <= 5

    def test_to_table_row(self):
        """Test conversion to markdown table row."""
        row = ClassMethodTableRow(
            class_name="Calculator",
            role="数値計算機能",
            main_methods=["add", "subtract", "multiply"],
            remarks="パターン: なし",
        )
        table_row = row.to_table_row()
        
        assert table_row.startswith("| Calculator |")
        assert "数値計算機能" in table_row
        assert "add, subtract, multiply" in table_row
        assert "パターン: なし" in table_row
        assert table_row.endswith(" |")

    def test_long_methods_truncation(self):
        """Test method list truncation in table row."""
        many_methods = [f"method{i}" for i in range(10)]
        row = ClassMethodTableRow(
            class_name="TestClass",
            role="役割",
            main_methods=many_methods,
            remarks="備考",
        )
        table_row = row.to_table_row()
        
        # Should contain only first 5 methods and truncation indicator
        assert "method0" in table_row
        assert "method4" in table_row
        assert "..." in table_row


class TestTableFormatter:
    """Test table formatter functionality."""

    def test_default_initialization(self):
        """Test formatter with default settings."""
        formatter = TableFormatter()
        assert formatter.settings.max_cell_length == 80
        assert formatter.settings.max_methods_per_cell == 5

    def test_custom_settings_initialization(self):
        """Test formatter with custom settings."""
        settings = TableFormattingSettings(max_cell_length=60, max_methods_per_cell=3)
        formatter = TableFormatter(settings)
        assert formatter.settings.max_cell_length == 60
        assert formatter.settings.max_methods_per_cell == 3

    def test_method_list_truncation(self):
        """Method lists are properly truncated to readable length."""
        formatter = TableFormatter(TableFormattingSettings(max_methods_per_cell=3))
        methods = ["add", "subtract", "multiply", "divide", "get_history"]
        result = formatter.format_method_list(methods)
        
        assert result == "add, subtract, multiply..."
        assert len(result) <= 80

    def test_empty_method_list(self):
        """Test handling of empty method list."""
        formatter = TableFormatter()
        result = formatter.format_method_list([])
        assert result == "未定義"

    def test_method_list_exact_limit(self):
        """Test method list exactly at the limit."""
        formatter = TableFormatter(TableFormattingSettings(max_methods_per_cell=3))
        methods = ["add", "subtract", "multiply"]
        result = formatter.format_method_list(methods)
        
        assert result == "add, subtract, multiply"
        assert "..." not in result

    def test_long_method_names(self):
        """Test handling of very long method names."""
        formatter = TableFormatter()
        methods = ["veryLongMethodNameThatExceedsNormalLimits"] * 3
        result = formatter.format_method_list(methods)
        
        assert len(result) <= 80
        assert result.endswith("...")

    def test_japanese_character_handling(self):
        """Japanese characters count correctly for length limits."""
        formatter = TableFormatter(TableFormattingSettings(max_cell_length=20))
        japanese_text = "数値計算機能と履歴管理機能と統計機能と詳細分析機能"  # Long Japanese text
        result = formatter.truncate_content(japanese_text)
        
        assert len(result) <= 20
        assert result.endswith("...")

    def test_format_class_name(self):
        """Test class name formatting."""
        formatter = TableFormatter()
        
        # Normal case
        assert formatter.format_class_name("Calculator") == "Calculator"
        
        # Empty case
        assert formatter.format_class_name("") == "未定義"
        
        # Long case
        long_name = "VeryLongClassNameThatExceedsLimits"
        result = formatter.format_class_name(long_name)
        assert len(result) <= 30
        assert result.endswith("...")

    def test_format_role_description(self):
        """Test role description formatting."""
        formatter = TableFormatter()
        
        # Normal case
        role = "数値計算機能"
        assert formatter.format_role_description(role) == role
        
        # Empty case
        assert formatter.format_role_description("") == "未定義"
        
        # Long case
        long_role = "非常に長い役割の説明文で五十文字を確実に超える内容になっている詳細な機能説明テキストであり非常に長い文章"
        result = formatter.format_role_description(long_role)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_format_remarks(self):
        """Test remarks formatting."""
        formatter = TableFormatter()
        
        # Normal case
        remarks = "パターン: なし"
        assert formatter.format_remarks(remarks) == remarks
        
        # Empty case
        assert formatter.format_remarks("") == "なし"
        
        # Long case
        long_remarks = "非常に長い備考欄の内容で四十文字を確実に超える詳細情報であり非常に長いテキストで更に長く"
        result = formatter.format_remarks(long_remarks)
        assert len(result) <= 40
        assert result.endswith("...")

    def test_create_table_row(self):
        """Test complete table row creation."""
        formatter = TableFormatter()
        
        result = formatter.create_table_row(
            class_name="Calculator",
            role="数値計算機能",
            methods=["add", "subtract", "multiply"],
            remarks="パターン: なし",
        )
        
        assert result.startswith("| Calculator |")
        assert "数値計算機能" in result
        assert "add, subtract, multiply" in result
        assert "パターン: なし" in result

    def test_create_table_row_with_errors(self):
        """Test table row creation with validation errors."""
        formatter = TableFormatter()
        
        # This should trigger the fallback mechanism
        result = formatter.create_table_row(
            class_name="",  # Empty name might cause issues
            role="",
            methods=[],
            remarks="",
        )
        
        # Should not raise an exception and should provide fallback
        assert isinstance(result, str)
        assert "|" in result  # Should be a table row


class TestJapaneseSpecificationTemplateIntegration:
    """Test integration with Japanese specification template."""

    def test_template_with_table_formatter(self):
        """Test template initialization with configuration."""
        from src.spec_generator.models import SpecificationConfig
        
        config = SpecificationConfig()
        template = JapaneseSpecificationTemplate("test", config=config)
        
        assert template.table_formatter is not None
        assert template.table_formatter.settings.max_cell_length == 80

    def test_table_integration_with_generator(self):
        """Table formatting integrates properly with specification generator."""
        from src.spec_generator.models import SpecificationConfig
        
        config = SpecificationConfig()
        template = JapaneseSpecificationTemplate("test", config=config)
        
        # Mock document data with many methods
        document_data = {
            "modules": {
                "test_module": {
                    "classes": [
                        {
                            "name": "Calculator",
                            "purpose": "数値計算機能",
                            "methods": [
                                "add",
                                "subtract",
                                "multiply",
                                "divide",
                                "power",
                                "sqrt",
                                "log",
                                "sin",
                                "cos",
                            ],
                            "design_pattern": "なし",
                        }
                    ],
                    "functions": [
                        {
                            "name": "helper_function",
                            "purpose": "補助機能",
                            "inputs": ["param1", "param2"],
                            "complexity": "low",
                        }
                    ],
                }
            }
        }

        result = template._generate_class_method_section(document_data)

        # Verify table is properly formatted
        lines = result.split("\n")
        table_lines = [line for line in lines if "Calculator" in line]
        
        assert len(table_lines) > 0
        table_line = table_lines[0]
        cells = table_line.split("|")

        # Each cell should be reasonably sized
        for cell in cells[1:-1]:  # Skip empty cells at start/end
            assert len(cell.strip()) <= 80

        # Methods cell should be truncated
        methods_cell = cells[3].strip() if len(cells) > 3 else ""
        assert "..." in methods_cell or len(methods_cell.split(", ")) <= 5

    def test_fallback_behavior(self):
        """Test fallback behavior when validation fails."""
        from src.spec_generator.models import SpecificationConfig
        
        config = SpecificationConfig()
        template = JapaneseSpecificationTemplate("test", config=config)
        
        # Document data that might cause issues
        document_data = {
            "modules": {
                "test_module": {
                    "classes": [
                        {
                            "name": None,  # Invalid data
                            "purpose": None,
                            "methods": None,
                            "design_pattern": None,
                        }
                    ]
                }
            }
        }

        # Should not raise exception
        result = template._generate_class_method_section(document_data)
        assert isinstance(result, str)
        assert "クラス・メソッド一覧表" in result


class TestPerformanceAndEdgeCases:
    """Test performance characteristics and edge cases."""

    def test_large_method_list_performance(self):
        """Test performance with very large method lists."""
        formatter = TableFormatter()
        large_methods = [f"method{i}" for i in range(100)]
        
        # Should complete quickly and not cause memory issues
        result = formatter.format_method_list(large_methods)
        assert len(result) <= 80
        assert result.endswith("...")

    def test_unicode_edge_cases(self):
        """Test various Unicode characters including emojis."""
        formatter = TableFormatter()
        
        # Mixed content with emojis and Japanese
        content = "機能📊データ分析🔍検索💾保存"
        result = formatter.truncate_content(content, 20)
        assert len(result) <= 20

    def test_special_characters_in_methods(self):
        """Test handling of special characters in method names."""
        formatter = TableFormatter()
        methods = ["__init__", "__str__", "__repr__", "get_data", "set_data"]
        result = formatter.format_method_list(methods)
        
        assert "__init__" in result
        assert len(result) <= 80

    def test_very_long_single_method_name(self):
        """Test handling of extremely long single method name."""
        formatter = TableFormatter()
        methods = ["extremelyLongMethodNameThatExceedsAllReasonableLimitsAndShouldBeTruncatedBecauseItIsWayTooLong"]
        result = formatter.format_method_list(methods)
        
        assert len(result) <= 80
        assert result.endswith("...")

    def test_mixed_language_content(self):
        """Test mixed Japanese and English content."""
        formatter = TableFormatter()
        content = "Calculate値計算ProcessデータHandleエラー処理"
        result = formatter.truncate_content(content, 30)
        
        assert len(result) <= 30
        if len(content) > 30:
            assert result.endswith("...")


# Integration test fixtures for complex scenarios
@pytest.fixture
def sample_complex_document_data():
    """Fixture providing complex document data for testing."""
    return {
        "modules": {
            "calculator_module": {
                "classes": [
                    {
                        "name": "AdvancedCalculator",
                        "purpose": "高度な数値計算機能を提供するクラス",
                        "methods": [
                            "add",
                            "subtract",
                            "multiply",
                            "divide",
                            "power",
                            "sqrt",
                            "logarithm",
                            "sine",
                            "cosine",
                            "tangent",
                            "factorial",
                            "fibonacci",
                        ],
                        "design_pattern": "Singleton",
                        "attributes": ["history", "precision", "mode"],
                    }
                ],
                "functions": [
                    {
                        "name": "utility_helper_function_with_very_long_name",
                        "purpose": "補助的な計算処理を行うためのユーティリティ関数",
                        "inputs": ["input1", "input2", "input3", "options", "config"],
                        "complexity": "high",
                    }
                ],
            }
        }
    }


def test_complex_integration_scenario(sample_complex_document_data):
    """Test complete integration with complex real-world data."""
    from src.spec_generator.models import SpecificationConfig
    
    config = SpecificationConfig()
    template = JapaneseSpecificationTemplate("test", config=config)
    
    result = template._generate_class_method_section(sample_complex_document_data)
    
    # Verify overall structure
    assert "クラス・メソッド一覧表" in result
    assert "AdvancedCalculator" in result
    
    # Verify proper table formatting
    lines = result.split("\n")
    table_content_lines = []
    capture = False
    
    for line in lines:
        if "| クラス名 |" in line:
            capture = True
            continue
        if capture and line.strip() and "|" in line:
            table_content_lines.append(line)
        elif capture and not line.strip():
            break
    
    # Each table row should be properly formatted
    for line in table_content_lines:
        if "|" in line:
            cells = line.split("|")
            for cell in cells[1:-1]:  # Skip empty start/end cells
                assert len(cell.strip()) <= 80, f"Cell too long: {cell.strip()}"