"""
Japanese specification document templates.

This module provides templates and utilities for generating Japanese IT industry
standard specification documents with proper formatting and structure.
"""

from datetime import datetime
from typing import Any

from .prompts import PromptTemplates


class JapaneseSpecificationTemplate:
    """Template for Japanese IT industry specification documents."""

    def __init__(self, project_name: str, version: str = "1.0"):
        self.project_name = project_name
        self.version = version
        self.creation_date = datetime.now().strftime("%Y年%m月%d日")

    def generate_header(self, document_type: str = "詳細設計書") -> str:
        """Generate document header in Japanese format."""
        return f"""# {self.project_name} {document_type}

**文書バージョン**: {self.version}
**作成日**: {self.creation_date}
**最終更新日**: {self.creation_date}

---
"""

    def generate_toc(self, sections: list[str]) -> str:
        """Generate table of contents."""
        toc_lines = ["## 目次\n"]

        for i, section in enumerate(sections, 1):
            toc_lines.append(f"{i}. [{section}](#{self._to_anchor(section)})")

        toc_lines.append("\n---\n")
        return "\n".join(toc_lines)

    def _to_anchor(self, text: str) -> str:
        """Convert section text to markdown anchor."""
        # Simple conversion - in real implementation, should handle Japanese properly
        return text.lower().replace(" ", "-").replace(".", "")

    def generate_overview_section(
        self, purpose: str, target_audience: str, system_overview: str
    ) -> str:
        """Generate overview section."""
        return f"""## 1. 概要

### 1.1 文書の目的

{purpose}

### 1.2 システム概要

{system_overview}

### 1.3 対象読者

{target_audience}

### 1.4 前提条件

本文書は以下の前提条件の下で作成されています：

- システムの基本設計が完了していること
- 要件定義書が承認されていること
- 開発チームが技術仕様を理解していること

"""

    def generate_architecture_section(
        self,
        architecture_overview: str,
        components: list[dict[str, str]],
        tech_stack: list[str],
    ) -> str:
        """Generate system architecture section."""
        component_list = []
        for comp in components:
            component_list.append(
                f"- **{comp.get('name', 'Unknown')}**: {comp.get('description', 'No description')}"
            )

        tech_list = []
        for tech in tech_stack:
            tech_list.append(f"- {tech}")

        return PromptTemplates.DOCUMENT_SECTION_PROMPT.format(
            architecture_overview=architecture_overview,
            component_list=chr(10).join(component_list),
            tech_list=chr(10).join(tech_list),
        )

    def generate_module_section(
        self, module_name: str, module_data: dict[str, Any]
    ) -> str:
        """Generate detailed module section."""
        # Extract module information
        purpose = module_data.get("purpose", "目的が定義されていません")
        functions = module_data.get("functions", [])
        classes = module_data.get("classes", [])
        dependencies = module_data.get("dependencies", [])

        # Format functions
        function_list = []
        for func in functions:
            params = ", ".join(func.get("inputs", []))
            function_list.append(
                f"""
#### {func.get('name', 'unknown')}

**目的**: {func.get('purpose', '未定義')}
**パラメータ**: {params}
**戻り値**: {func.get('outputs', '未定義')}
**複雑度**: {func.get('complexity', '未評価')}

**処理概要**:
{func.get('business_logic', 'ビジネスロジックが定義されていません')}
"""
            )

        # Format classes
        class_list = []
        for cls in classes:
            methods = ", ".join(cls.get("methods", []))
            attributes = ", ".join(cls.get("attributes", []))
            class_list.append(
                f"""
#### {cls.get('name', 'unknown')}

**目的**: {cls.get('purpose', '未定義')}
**メソッド**: {methods}
**属性**: {attributes}
**デザインパターン**: {cls.get('design_pattern', '適用なし')}
"""
            )

        # Format dependencies
        dep_list = []
        for dep in dependencies:
            dep_type = "内部" if dep.get("type") == "internal" else "外部"
            dep_list.append(
                f"- **{dep.get('name')}** ({dep_type}): {dep.get('usage', '用途不明')}"
            )

        return f"""### 3.1.{len(function_list) + len(class_list)} {module_name}

#### 概要
{purpose}

#### 主要機能
{"".join(function_list)}

#### クラス設計
{"".join(class_list)}

#### 依存関係
{chr(10).join(dep_list) if dep_list else "依存関係はありません"}

"""

    def generate_data_design_section(
        self, data_structures: list[dict[str, Any]]
    ) -> str:
        """Generate data design section."""
        structures = []
        for struct in data_structures:
            fields = []
            for field in struct.get("fields", []):
                fields.append(
                    f"| {field.get('name')} | {field.get('type')} | {field.get('description')} |"
                )

            field_table = (
                "| フィールド名 | 型 | 説明 |\n|-------------|---|------|\n"
                + "\n".join(fields)
            )

            structures.append(
                f"""
#### {struct.get('name', 'Unknown')}

**用途**: {struct.get('purpose', '未定義')}

{field_table}
"""
            )

        return f"""### 3.2 データ設計

#### 3.2.1 データ構造
{"".join(structures)}

#### 3.2.2 データフロー

データは以下の流れで処理されます：

1. 入力データの受信・検証
2. ビジネスロジックによる処理
3. データ変換・加工
4. 出力データの生成
5. 結果の返却・保存

"""

    def generate_processing_section(
        self, main_flows: list[str], error_handling: str
    ) -> str:
        """Generate processing design section."""
        flow_list = []
        for i, flow in enumerate(main_flows, 1):
            flow_list.append(f"{i}. {flow}")

        return f"""### 3.3 処理設計

#### 3.3.1 主要処理フロー

{chr(10).join(flow_list)}

#### 3.3.2 例外処理方式

{error_handling}

#### 3.3.3 エラーハンドリング

システムでは以下のエラーハンドリング戦略を採用します：

- **予期される例外**: try-catch文による適切な処理
- **予期されない例外**: ログ出力と安全な縮退処理
- **システム例外**: 監視システムへの通知と復旧処理
- **ユーザーエラー**: 分かりやすいエラーメッセージの表示

"""

    def generate_nonfunctional_section(
        self, performance: str, security: str, availability: str, maintainability: str
    ) -> str:
        """Generate non-functional requirements section."""
        return f"""## 4. 非機能要件

### 4.1 性能要件

{performance}

### 4.2 セキュリティ要件

{security}

### 4.3 可用性要件

{availability}

### 4.4 保守性要件

{maintainability}

"""

    def generate_operations_section(
        self, deployment: str, monitoring: str, backup: str
    ) -> str:
        """Generate operations section."""
        return f"""## 5. 運用設計

### 5.1 デプロイメント方式

{deployment}

### 5.2 監視・ログ

{monitoring}

### 5.3 バックアップ・復旧

{backup}

"""

    def generate_appendix_section(
        self, terms: dict[str, str], references: list[str]
    ) -> str:
        """Generate appendix section."""
        term_list = []
        for term, definition in terms.items():
            term_list.append(f"**{term}**: {definition}")

        ref_list = []
        for ref in references:
            ref_list.append(f"- {ref}")

        return f"""## 6. 付録

### 6.1 用語集

{chr(10).join(term_list)}

### 6.2 参考資料

{chr(10).join(ref_list)}

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
        """Generate complete specification document."""
        sections = []

        # Header
        sections.append(
            self.generate_header(document_data.get("document_type", "詳細設計書"))
        )

        # Table of Contents
        toc_sections = [
            "概要",
            "システム構成",
            "詳細設計",
            "非機能要件",
            "運用設計",
            "付録",
        ]
        sections.append(self.generate_toc(toc_sections))

        # Overview
        if overview := document_data.get("overview"):
            sections.append(
                self.generate_overview_section(
                    overview.get("purpose", ""),
                    overview.get("target_audience", "開発チーム、運用チーム"),
                    overview.get("system_overview", ""),
                )
            )

        # Architecture
        if architecture := document_data.get("architecture"):
            sections.append(
                self.generate_architecture_section(
                    architecture.get("overview", ""),
                    architecture.get("components", []),
                    architecture.get("tech_stack", []),
                )
            )

        # Detailed Design
        sections.append("## 3. 詳細設計\n")

        # Modules
        if modules := document_data.get("modules"):
            sections.append("### 3.1 モジュール設計\n")
            for module_name, module_data in modules.items():
                sections.append(self.generate_module_section(module_name, module_data))

        # Data Design
        if data_design := document_data.get("data_design"):
            sections.append(
                self.generate_data_design_section(data_design.get("structures", []))
            )

        # Processing Design
        if processing := document_data.get("processing"):
            sections.append(
                self.generate_processing_section(
                    processing.get("main_flows", []),
                    processing.get(
                        "error_handling", "標準的なエラーハンドリングを実装"
                    ),
                )
            )

        # Non-functional Requirements
        if nonfunctional := document_data.get("nonfunctional"):
            sections.append(
                self.generate_nonfunctional_section(
                    nonfunctional.get("performance", "性能要件が定義されていません"),
                    nonfunctional.get(
                        "security", "セキュリティ要件が定義されていません"
                    ),
                    nonfunctional.get("availability", "可用性要件が定義されていません"),
                    nonfunctional.get(
                        "maintainability", "保守性要件が定義されていません"
                    ),
                )
            )

        # Operations
        if operations := document_data.get("operations"):
            sections.append(
                self.generate_operations_section(
                    operations.get(
                        "deployment", "デプロイメント方式が定義されていません"
                    ),
                    operations.get("monitoring", "監視方式が定義されていません"),
                    operations.get("backup", "バックアップ方式が定義されていません"),
                )
            )

        # Appendix
        sections.append(
            self.generate_appendix_section(
                document_data.get("terms", {}), document_data.get("references", [])
            )
        )

        # Change History
        sections.append(
            self.generate_change_history_section(
                document_data.get("change_history", [])
            )
        )

        return "\n".join(sections)


class SpecificationFormatter:
    """Utility class for formatting specification content."""

    @staticmethod
    def format_code_block(code: str, language: str = "") -> str:
        """Format code as markdown code block."""
        return f"```{language}\n{code}\n```"

    @staticmethod
    def format_table(headers: list[str], rows: list[list[str]]) -> str:
        """Format data as markdown table."""
        table_lines = []

        # Header
        table_lines.append("| " + " | ".join(headers) + " |")
        table_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # Rows
        for row in rows:
            table_lines.append("| " + " | ".join(row) + " |")

        return "\n".join(table_lines)

    @staticmethod
    def format_list(items: list[str], ordered: bool = False) -> str:
        """Format items as markdown list."""
        if ordered:
            return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))
        else:
            return "\n".join(f"- {item}" for item in items)

    @staticmethod
    def format_section_header(title: str, level: int = 1) -> str:
        """Format section header."""
        return f"{'#' * level} {title}\n"

    @staticmethod
    def format_emphasis(text: str, bold: bool = False) -> str:
        """Format emphasized text."""
        if bold:
            return f"**{text}**"
        else:
            return f"*{text}*"


# Standard Japanese IT terminology
STANDARD_SECTIONS = {
    "overview": "概要",
    "purpose": "目的",
    "scope": "範囲",
    "architecture": "アーキテクチャ",
    "design": "設計",
    "implementation": "実装",
    "testing": "テスト",
    "deployment": "デプロイメント",
    "operations": "運用",
    "maintenance": "保守",
    "appendix": "付録",
}

STANDARD_SUBSECTIONS = {
    "system_overview": "システム概要",
    "target_audience": "対象読者",
    "prerequisites": "前提条件",
    "constraints": "制約事項",
    "assumptions": "前提条件",
    "risks": "リスク",
    "mitigation": "対策",
    "schedule": "スケジュール",
    "resources": "リソース",
    "deliverables": "成果物",
}
