"""
Comprehensive tests for table formatting functionality.

This module tests table cell content constraints, method list truncation,
character handling, and integration with the generation pipeline.
"""

import pytest
from pydantic import ValidationError

from src.spec_generator.models import TableFormattingSettings
from src.spec_generator.templates.table_formatters import (
    TableFormatter,
    TableCellContent,
    ClassMethodTableRow,
)
from src.spec_generator.templates.specification import SpecificationTemplate


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
            truncation_suffix="…",
            preserve_japanese=False
        )
        assert settings.max_cell_length == 60
        assert settings.max_methods_per_cell == 3
        assert settings.method_separator == " | "
        assert settings.truncation_suffix == "…"
        assert settings.preserve_japanese is False

    def test_validation_constraints(self):
        """Test that settings validation works correctly."""
        # This should not raise an exception
        TableFormattingSettings(max_cell_length=10, max_methods_per_cell=1)
        
        # Test edge case
        settings = TableFormattingSettings(max_cell_length=1)
        assert settings.max_cell_length == 1


class TestTableCellContent:
    """Test the table cell content validation model."""

    def test_normal_content(self):
        """Test normal content that fits within limits."""
        content = TableCellContent(content="Normal content")
        assert content.content == "Normal content"

    def test_long_content_truncation(self):
        """Test that long content is properly truncated."""
        long_content = "This is a very long piece of content that exceeds the maximum length limit for table cells"
        content = TableCellContent(content=long_content)
        assert len(content.content) <= 80
        assert content.content.endswith("...")

    def test_content_with_japanese(self):
        """Test content with Japanese characters."""
        japanese_content = "日本語のテキスト内容"
        content = TableCellContent(content=japanese_content)
        assert content.content == japanese_content

    def test_empty_content(self):
        """Test empty content handling."""
        content = TableCellContent(content="")
        assert content.content == ""

    def test_content_exactly_at_limit(self):
        """Test content that is exactly at the length limit."""
        content_80_chars = "x" * 80
        content = TableCellContent(content=content_80_chars)
        assert content.content == content_80_chars
        assert len(content.content) == 80


class TestClassMethodTableRow:
    """Test the class method table row model."""

    def test_normal_row_creation(self):
        """Test normal table row creation."""
        row = ClassMethodTableRow(
            class_name="Calculator",
            role="数値計算機能",
            main_methods=["add", "subtract", "multiply"],
            remarks="基本的な計算クラス"
        )
        assert row.class_name == "Calculator"
        assert row.role == "数値計算機能"
        assert row.main_methods == ["add", "subtract", "multiply"]
        assert row.remarks == "基本的な計算クラス"

    def test_long_class_name_truncation(self):
        """Test that long class names are truncated."""
        long_name = "VeryLongClassNameThatExceedsLimit"
        row = ClassMethodTableRow(
            class_name=long_name,
            role="Test role",
            main_methods=["test"],
            remarks="Test"
        )
        assert len(row.class_name) <= 30
        assert row.class_name.endswith("...")

    def test_long_role_truncation(self):
        """Test that long role descriptions are truncated."""
        long_role = "This is a very long role description that exceeds the maximum length"
        row = ClassMethodTableRow(
            class_name="Test",
            role=long_role,
            main_methods=["test"],
            remarks="Test"
        )
        assert len(row.role) <= 50
        assert row.role.endswith("...")

    def test_method_list_truncation(self):
        """Test that method lists are truncated to maximum count."""
        many_methods = [f"method{i}" for i in range(10)]
        row = ClassMethodTableRow(
            class_name="Test",
            role="Test role",
            main_methods=many_methods,
            remarks="Test"
        )
        assert len(row.main_methods) <= 5
        assert row.original_method_count == 10

    def test_table_row_output(self):
        """Test markdown table row output format."""
        row = ClassMethodTableRow(
            class_name="Calculator",
            role="数値計算",
            main_methods=["add", "subtract"],
            remarks="基本クラス"
        )
        output = row.to_table_row()
        assert output.startswith("| Calculator |")
        assert "数値計算" in output
        assert "add, subtract" in output
        assert "基本クラス" in output
        assert output.endswith(" |")


class TestTableFormatter:
    """Test the table formatter utility class."""

    def test_initialization_with_default_settings(self):
        """Test formatter initialization with default settings."""
        formatter = TableFormatter()
        assert formatter.settings.max_cell_length == 80
        assert formatter.settings.max_methods_per_cell == 5

    def test_initialization_with_custom_settings(self):
        """Test formatter initialization with custom settings."""
        custom_settings = TableFormattingSettings(max_cell_length=60)
        formatter = TableFormatter(custom_settings)
        assert formatter.settings.max_cell_length == 60

    def test_create_table_row(self):
        """Test table row creation with various inputs."""
        formatter = TableFormatter()
        
        # Normal case
        result = formatter.create_table_row(
            class_name="Calculator",
            role="数値計算機能",
            methods=["add", "subtract", "multiply"],
            remarks="基本的な計算機能"
        )
        
        assert "Calculator" in result
        assert "数値計算機能" in result
        assert "add, subtract, multiply" in result
        assert "基本的な計算機能" in result
        assert result.startswith("|")
        assert result.endswith("|")

    def test_create_table_row_with_long_inputs(self):
        """Test table row creation with inputs that need truncation."""
        formatter = TableFormatter()
        
        result = formatter.create_table_row(
            class_name="VeryLongClassNameThatExceedsTheLimit",
            role="This is a very long role description that should be truncated",
            methods=[f"veryLongMethodName{i}" for i in range(10)],
            remarks="Very long remarks that should be truncated"
        )
        
        # Should not raise an exception and should return a valid row
        assert "|" in result
        assert result.count("|") >= 4  # Should have at least 4 separators

    def test_create_table_row_error_handling(self):
        """Test error handling in table row creation."""
        formatter = TableFormatter()
        
        # Test with potentially problematic input
        result = formatter.create_table_row(
            class_name="",
            role="",
            methods=[],
            remarks=""
        )
        
        # Should return a valid row even with empty inputs
        assert "|" in result


class TestJapaneseSpecificationTemplateIntegration:
    """Test integration with the Japanese specification template."""

    def test_table_integration_with_generator(self):
        """Test table formatting integration with specification generation."""
        from src.spec_generator.models import SpecificationConfig
        
        config = SpecificationConfig()
        template = SpecificationTemplate("テストプロジェクト", config=config)
        
        # Test document data
        document_data = {
            "modules": {
                "calculator": {
                    "classes": [
                        {
                            "name": "Calculator",
                            "purpose": "数値計算機能",
                            "methods": ["add", "subtract", "multiply", "divide"],
                            "design_pattern": "Singleton"
                        }
                    ],
                    "functions": [
                        {
                            "name": "helper_function",
                            "purpose": "補助機能",
                            "inputs": ["param1", "param2"],
                            "complexity": "low"
                        }
                    ]
                }
            }
        }
        
        result = template.section_generator.generate_class_method_section(document_data)
        
        # Verify table structure
        assert "| クラス名 | 役割 | 主要メソッド | 備考 |" in result
        assert "Calculator" in result
        assert "数値計算機能" in result
        assert "add, subtract, multiply, divide" in result

    def test_fallback_behavior(self):
        """Test fallback behavior when no data is available."""
        from src.spec_generator.models import SpecificationConfig
        
        config = SpecificationConfig()
        template = SpecificationTemplate("テストプロジェクト", config=config)
        
        # Empty document data
        document_data = {"modules": {}}
        
        result = template.section_generator.generate_class_method_section(document_data)
        
        # Should contain fallback content
        assert "| 未定義 | 未定義 | 未定義 | 未定義 |" in result


@pytest.fixture
def sample_complex_document_data():
    """Provide complex document data for integration testing."""
    return {
        "modules": {
            "calculator_module": {
                "classes": [
                    {
                        "name": "AdvancedCalculator",
                        "purpose": "高度な数値計算機能を提供する計算機クラス",
                        "methods": [
                            "add", "subtract", "multiply", "divide",
                            "power", "sqrt", "log", "sin", "cos", "tan"
                        ],
                        "attributes": ["history", "precision", "mode"],
                        "design_pattern": "Singleton",
                        "inheritance": "BaseCalculator"
                    }
                ],
                "functions": [
                    {
                        "name": "utility_helper_function_with_very_long_name",
                        "purpose": "補助的な計算処理を行うためのユーティリティ関数",
                        "inputs": ["data", "options", "config"],
                        "complexity": "medium"
                    }
                ]
            }
        }
    }


def test_complex_integration_scenario(sample_complex_document_data):
    """Test complete integration with complex real-world data."""
    from src.spec_generator.models import SpecificationConfig
    
    config = SpecificationConfig()
    template = SpecificationTemplate("test", config=config)
    
    result = template.section_generator.generate_class_method_section(sample_complex_document_data)
    
    # Verify content is properly formatted
    assert "AdvancedCalculator" in result
    assert "高度な数値計算機能" in result
    assert "| クラス名 | 役割 | 主要メソッド | 備考 |" in result
    
    # Verify method truncation works
    # The class has 10 methods, should be truncated to 5 max
    methods_section = result[result.find("add"):result.find("Singleton")]
    method_count = methods_section.count(",") + 1  # Count commas + 1
    assert method_count <= 6  # 5 methods + potential truncation indicator
    
    # Verify detailed specifications are included
    assert "#### AdvancedCalculator" in result
    assert "クラス概要" in result
    assert "属性一覧" in result


def test_specification_generation_end_to_end():
    """Test complete specification generation with table formatting."""
    from src.spec_generator.models import SpecificationConfig
    
    config = SpecificationConfig()
    template = SpecificationTemplate("統合テストプロジェクト", config=config)
    
    # Comprehensive test data
    document_data = {
        "document_type": "詳細設計書",
        "overview": {
            "system_overview": "テスト用システムの概要",
            "constraints": "特定の制約事項"
        },
        "modules": {
            "core_module": {
                "classes": [
                    {
                        "name": "CoreProcessor",
                        "purpose": "中核処理機能",
                        "methods": ["initialize", "process", "finalize"],
                        "attributes": ["status", "config"],
                        "design_pattern": "Strategy"
                    }
                ],
                "functions": [
                    {
                        "name": "main_process",
                        "purpose": "メイン処理機能",
                        "inputs": ["input_data"],
                        "complexity": "high"
                    }
                ]
            }
        },
        "change_history": [
            {
                "date": "2024-01-01",
                "version": "1.0",
                "description": "初版作成",
                "author": "テスト実行者"
            }
        ]
    }
    
    # Generate complete document
    result = template.generate_complete_document(document_data)
    
    # Verify document structure
    assert "統合テストプロジェクト 詳細設計書" in result
    assert "## 1. 概要" in result
    assert "## 3. クラス・メソッド設計" in result
    assert "### 変更履歴" in result
    
    # Verify table formatting is applied
    assert "| クラス名 | 役割 | 主要メソッド | 備考 |" in result
    assert "CoreProcessor" in result
    assert "中核処理機能" in result