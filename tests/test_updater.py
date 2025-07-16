"""
Unit tests for spec_generator.core.updater module.

Tests for SpecificationUpdater and related document management functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from spec_generator.core.updater import (
    ChangeAnalyzer,
    DocumentParser,
    DocumentSection,
    SpecificationUpdater,
)
from spec_generator.models import (
    ProcessingStats,
    SemanticChange,
    SpecificationConfig,
    SpecificationOutput,
)


class TestDocumentSection:
    """Test DocumentSection functionality."""

    def test_section_creation(self):
        """Test creating a document section."""
        section = DocumentSection(
            title="Test Section",
            content="This is test content",
            level=2,
            start_line=0,
            end_line=5,
        )

        assert section.title == "Test Section"
        assert section.content == "This is test content"
        assert section.level == 2
        assert section.start_line == 0
        assert section.end_line == 5
        assert section.subsections == []
        assert section.updated is False

    def test_add_subsection(self):
        """Test adding subsections."""
        parent = DocumentSection("Parent", "Content", 1, 0, 10)
        child = DocumentSection("Child", "Child content", 2, 5, 8)

        parent.add_subsection(child)

        assert len(parent.subsections) == 1
        assert parent.subsections[0] == child

    def test_find_subsection(self):
        """Test finding subsections by title pattern."""
        parent = DocumentSection("Parent", "Content", 1, 0, 20)
        child1 = DocumentSection("Implementation Details", "Details", 2, 5, 10)
        child2 = DocumentSection("API Reference", "API docs", 2, 11, 15)
        grandchild = DocumentSection("Core Functions", "Functions", 3, 16, 18)

        parent.add_subsection(child1)
        parent.add_subsection(child2)
        child2.add_subsection(grandchild)

        # Test direct match
        found = parent.find_subsection("Implementation")
        assert found == child1

        # Test recursive match
        found = parent.find_subsection("Core Functions")
        assert found == grandchild

        # Test no match
        found = parent.find_subsection("Nonexistent")
        assert found is None

    def test_to_markdown(self):
        """Test converting section to markdown."""
        section = DocumentSection("Test Section", "Content here", 2, 0, 5)
        child = DocumentSection("Subsection", "Sub content", 3, 2, 4)
        section.add_subsection(child)

        markdown = section.to_markdown()

        assert "## Test Section" in markdown
        assert "Content here" in markdown
        assert "### Subsection" in markdown
        assert "Sub content" in markdown


class TestDocumentParser:
    """Test DocumentParser functionality."""

    def test_parse_simple_document(self):
        """Test parsing a simple markdown document."""
        content = """# Main Title

This is the introduction.

## Section One

Content for section one.

### Subsection

More detailed content.

## Section Two

Content for section two.
"""

        parser = DocumentParser()
        sections = parser.parse_document(content)

        assert len(sections) == 1  # Only top-level section
        main_section = sections[0]
        assert main_section.title == "Main Title"
        assert main_section.level == 1
        assert len(main_section.subsections) == 2

        section_one = main_section.subsections[0]
        assert section_one.title == "Section One"
        assert section_one.level == 2
        assert len(section_one.subsections) == 1

        subsection = section_one.subsections[0]
        assert subsection.title == "Subsection"
        assert subsection.level == 3

    def test_parse_document_with_content(self):
        """Test parsing document and extracting content."""
        content = """## Overview

This is the overview section.

It has multiple paragraphs.

## Details

Detailed information here.
"""

        parser = DocumentParser()
        sections = parser.parse_document(content)

        assert len(sections) == 2
        overview = sections[0]
        assert "multiple paragraphs" in overview.content

        details = sections[1]
        assert "Detailed information" in details.content


class TestChangeAnalyzer:
    """Test ChangeAnalyzer functionality."""

    def test_analyze_changes_basic(self):
        """Test basic change analysis."""
        changes = [
            SemanticChange(
                change_type="added",
                element_type="function",
                element_name="new_function",
                file_path=Path("test.py"),
                impact_score=3.0,
                description="Added new function",
            ),
            SemanticChange(
                change_type="modified",
                element_type="class",
                element_name="TestClass",
                file_path=Path("test.py"),
                impact_score=7.5,
                description="Modified class",
            ),
        ]

        analyzer = ChangeAnalyzer()
        analysis = analyzer.analyze_changes(changes)

        assert analysis["total_changes"] == 2
        assert analysis["by_type"]["added"] == 1
        assert analysis["by_type"]["modified"] == 1
        assert len(analysis["by_impact"]["low"]) == 1
        assert len(analysis["by_impact"]["high"]) == 1

    def test_analyze_changes_full_regeneration_trigger(self):
        """Test when analysis triggers full regeneration."""
        # Create many high-impact changes
        changes = []
        for i in range(10):
            changes.append(
                SemanticChange(
                    change_type="modified",
                    element_type="class",
                    element_name=f"Class{i}",
                    file_path=Path("test.py"),
                    impact_score=8.0,
                    description=f"High impact change {i}",
                )
            )

        analyzer = ChangeAnalyzer()
        analysis = analyzer.analyze_changes(changes)

        assert analysis["requires_full_regeneration"] is True

    def test_determine_affected_sections(self):
        """Test determining affected sections."""
        change = SemanticChange(
            change_type="added",
            element_type="function",
            element_name="test_function",
            file_path=Path("test.py"),
            impact_score=8.5,
            description="High impact function",
        )

        analyzer = ChangeAnalyzer()
        sections = analyzer._determine_affected_sections(change)

        assert "詳細設計" in sections
        assert "モジュール設計" in sections
        assert "処理設計" in sections
        assert "システム構成" in sections  # Due to high impact


class TestSpecificationUpdater:
    """Test SpecificationUpdater functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.config = SpecificationConfig(openai_api_key="test-key", chunk_size=1000)
        self.updater = SpecificationUpdater(self.config)

    @pytest.mark.asyncio
    async def test_update_specification_basic(self):
        """Test basic specification update."""
        # Create a temporary specification file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """# Test Specification

## 詳細設計

### モジュール設計

Current module design.

## 非機能要件

Current requirements.
"""
            )
            spec_path = Path(f.name)

        try:
            changes = [
                SemanticChange(
                    change_type="added",
                    element_type="function",
                    element_name="new_function",
                    file_path=Path("test.py"),
                    impact_score=3.0,
                    description="Added new function",
                )
            ]

            with patch.object(
                self.updater.llm_provider, "generate", new_callable=AsyncMock
            ) as mock_generate:
                mock_generate.return_value = "Updated section content"

                output = await self.updater.update_specification(spec_path, changes)

                assert isinstance(output, SpecificationOutput)
                assert output.title == "更新された仕様書"
                assert (
                    "Updated section content" in output.content
                    or "更新された仕様書" in output.content
                )
                assert output.metadata["update_type"] == "incremental"
                assert output.metadata["change_count"] == 1

        finally:
            spec_path.unlink()

    @pytest.mark.asyncio
    async def test_update_specification_full_regeneration(self):
        """Test specification update that triggers full regeneration."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Specification\n\nSimple content.")
            spec_path = Path(f.name)

        try:
            # Create many changes to trigger full regeneration
            changes = []
            for i in range(25):  # Exceeds threshold
                changes.append(
                    SemanticChange(
                        change_type="modified",
                        element_type="class",
                        element_name=f"Class{i}",
                        file_path=Path("test.py"),
                        impact_score=8.0,
                        description=f"High impact change {i}",
                    )
                )

            output = await self.updater.update_specification(spec_path, changes)

            assert output.title == "仕様書再生成要求"
            assert output.metadata["requires_full_regeneration"] is True
            assert "仕様書全体の再生成が必要" in output.content

        finally:
            spec_path.unlink()

    @pytest.mark.asyncio
    async def test_save_updated_specification(self):
        """Test saving updated specification."""
        output = SpecificationOutput(
            title="Test Output",
            content="# Test Content",
            language="ja",
            created_at="2024-01-01 12:00:00",
            source_files=[Path("test.py")],
            processing_stats=ProcessingStats(),
            metadata={"test": "data"},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_spec.md"

            await self.updater._save_updated_specification(output, output_path)

            # Check specification file
            assert output_path.exists()
            content = output_path.read_text()
            assert "# Test Content" in content

            # Note: update_metadata.json files are no longer generated (refactored to use logging)

    def test_merge_specifications(self):
        """Test merging two specification documents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create base specification
            base_spec = temp_path / "base.md"
            base_spec.write_text(
                """# Base Specification

## Section A

Base content A.

## Section B

Base content B.
"""
            )

            # Create update specification
            update_spec = temp_path / "update.md"
            update_spec.write_text(
                """# Update Specification

## Section A

Updated content A.

## Section C

New content C.
"""
            )

            # Create output path
            merged_spec = temp_path / "merged.md"

            # Perform merge
            self.updater.merge_specifications(base_spec, update_spec, merged_spec)

            # Verify merge
            assert merged_spec.exists()
            content = merged_spec.read_text()
            assert "統合された仕様書" in content
            assert "Updated content A" in content or "New content C" in content

    def test_create_change_summary(self):
        """Test creating change summary."""
        changes = [
            SemanticChange(
                change_type="added",
                element_type="function",
                element_name="func1",
                file_path=Path("test.py"),
                impact_score=3.0,
                description="Added function",
            ),
            SemanticChange(
                change_type="modified",
                element_type="class",
                element_name="class1",
                file_path=Path("test.py"),
                impact_score=6.0,
                description="Modified class",
            ),
        ]

        summary = self.updater._create_section_change_summary(changes)

        assert "func1" in summary
        assert "class1" in summary
        assert "function" in summary
        assert "class" in summary
        assert "高影響度" in summary  # Should be present for the class change

    def test_create_update_header(self):
        """Test creating update header."""
        changes = [
            SemanticChange(
                change_type="added",
                element_type="function",
                element_name="test_func",
                file_path=Path("test.py"),
                impact_score=3.0,
                description="Test change",
            )
        ]

        header = self.updater._create_update_header(changes)

        assert "更新された仕様書" in header
        assert "最終更新日" in header
        assert "1件の変更" in header

    def test_create_change_history_section(self):
        """Test creating change history section."""
        changes = [
            SemanticChange(
                change_type="added",
                element_type="function",
                element_name="test_func",
                file_path=Path("test.py"),
                impact_score=3.0,
                description="Test change",
            ),
            SemanticChange(
                change_type="modified",
                element_type="class",
                element_name="TestClass",
                file_path=Path("test.py"),
                impact_score=8.0,
                description="High impact change",
            ),
        ]

        history = self.updater._create_change_history_section(changes)

        assert "変更履歴" in history
        assert "test_func" in history
        assert "TestClass" in history
        assert "高" in history  # High impact indicator
        assert "低" in history  # Low impact indicator


# Integration tests
class TestUpdaterIntegration:
    """Integration tests for SpecificationUpdater."""

    def setup_method(self):
        """Setup for each test method."""
        self.config = SpecificationConfig(openai_api_key="test-key", chunk_size=1000)

    @pytest.mark.asyncio
    async def test_full_update_workflow(self):
        """Test complete update workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create existing specification
            existing_spec = temp_path / "existing.md"
            existing_spec.write_text(
                """# システム仕様書

## 1. 概要

システムの概要です。

## 3. 詳細設計

### 3.1 モジュール設計

現在のモジュール設計。

## 4. 非機能要件

性能要件と可用性要件。
"""
            )

            # Create changes
            changes = [
                SemanticChange(
                    change_type="added",
                    element_type="function",
                    element_name="process_data",
                    file_path=Path("processor.py"),
                    impact_score=4.0,
                    description="データ処理関数を追加",
                ),
                SemanticChange(
                    change_type="modified",
                    element_type="class",
                    element_name="DataManager",
                    file_path=Path("manager.py"),
                    impact_score=6.5,
                    description="データ管理クラスを改修",
                ),
            ]

            # Create updater with mocked LLM
            updater = SpecificationUpdater(self.config)

            with patch.object(
                updater.llm_provider, "generate", new_callable=AsyncMock
            ) as mock_generate:
                mock_generate.return_value = """更新されたセクション内容:

- process_data関数が追加されました
- DataManagerクラスが改修されました
- 新しい機能による処理能力の向上
"""

                output_path = temp_path / "updated_spec.md"

                # Perform update
                result = await updater.update_specification(
                    existing_spec, changes, output_path
                )

                # Verify result
                assert isinstance(result, SpecificationOutput)
                assert result.metadata["update_type"] == "incremental"
                assert result.metadata["change_count"] == 2

                # Verify output file
                assert output_path.exists()
                content = output_path.read_text()
                assert "更新された仕様書" in content

                # Note: update_metadata.json files are no longer generated (refactored to use logging)


# Fixtures
@pytest.fixture
def sample_specification_content():
    """Sample specification document content."""
    return """# システム仕様書

**文書バージョン**: 1.0
**作成日**: 2024年1月1日

## 1. 概要

### 1.1 システム概要

システムの概要説明。

## 2. システム構成

### 2.1 全体アーキテクチャ

アーキテクチャの説明。

## 3. 詳細設計

### 3.1 モジュール設計

#### 3.1.1 data_processor

データ処理モジュール。

### 3.2 データ設計

データベース設計。

## 4. 非機能要件

### 4.1 性能要件

応答時間とスループット。
"""


@pytest.fixture
def sample_changes():
    """Sample semantic changes."""
    return [
        SemanticChange(
            change_type="added",
            element_type="function",
            element_name="validate_input",
            file_path=Path("validator.py"),
            impact_score=3.5,
            description="入力検証関数を追加",
        ),
        SemanticChange(
            change_type="modified",
            element_type="class",
            element_name="DatabaseConnection",
            file_path=Path("db.py"),
            impact_score=7.0,
            description="データベース接続クラスを改修",
        ),
        SemanticChange(
            change_type="removed",
            element_type="function",
            element_name="deprecated_function",
            file_path=Path("utils.py"),
            impact_score=2.0,
            description="非推奨関数を削除",
        ),
    ]


def test_document_parser_with_sample_spec(sample_specification_content):
    """Test document parser with realistic specification content."""
    parser = DocumentParser()
    sections = parser.parse_document(sample_specification_content)

    assert len(sections) == 1  # Main document
    main_section = sections[0]
    assert main_section.title == "システム仕様書"
    assert len(main_section.subsections) >= 3  # At least 3 main sections


def test_change_analyzer_with_sample_changes(sample_changes):
    """Test change analyzer with realistic changes."""
    analyzer = ChangeAnalyzer()
    analysis = analyzer.analyze_changes(sample_changes)

    assert analysis["total_changes"] == 3
    assert analysis["by_type"]["added"] == 1
    assert analysis["by_type"]["modified"] == 1
    assert analysis["by_type"]["removed"] == 1
    assert not analysis["requires_full_regeneration"]
