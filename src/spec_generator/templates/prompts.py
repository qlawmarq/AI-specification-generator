"""
LangChain prompt templates for Japanese specification generation.

This module defines prompt templates for progressive prompting strategy,
including analysis prompts and Japanese specification generation prompts.
"""

from typing import Any

from langchain.prompts import PromptTemplate


class PromptTemplates:
    """Collection of prompt templates for specification generation."""

    # Code Analysis Prompt (Stage 1) - Enhanced for Class Structure Recognition
    ANALYSIS_PROMPT = PromptTemplate(
        input_variables=["code_content", "file_path", "language", "ast_info"],
        template="""あなたは熟練したソフトウェアアーキテクトです。
以下のコードを分析し、機能と責務を特定してください。

## ファイル: {file_path}
## 言語: {language}

## AST情報:
{ast_info}

## コード内容:
```{language}
{code_content}
```

## 重要な指示:
- 同じクラスのメソッドは必ず同じクラス名で関連付けてください
- "不明" や "推測" ではなく、実際のクラス名を使用してください
- メソッドとクラスの関係を明確に示してください
- クラスが存在する場合は、そのクラス内のメソッドをすべて "methods" 配列に含めてください

## 分析項目:
1. 主要機能（各関数・クラスの役割）
2. データフロー
3. 外部依存関係
4. ビジネスロジック
5. エラーハンドリング方式

## 出力形式:
JSON形式で構造化して出力してください:
```json
{{
  "overview": "ファイル全体の概要",
  "main_purpose": "このファイルの主な目的",
  "functions": [
    {{
      "name": "関数名",
      "purpose": "役割",
      "inputs": ["入力パラメータ"],
      "outputs": "戻り値",
      "business_logic": "ビジネスロジック",
      "complexity": "複雑度（low/medium/high）",
      "parent_class": "所属するクラス名（クラスメソッドの場合）"
    }}
  ],
  "classes": [
    {{
      "name": "実際のクラス名",
      "purpose": "役割",
      "methods": ["メソッド名のリスト"],
      "attributes": ["属性名のリスト"],
      "design_pattern": "使用されているデザインパターン",
      "method_details": [
        {{
          "name": "メソッド名",
          "purpose": "メソッドの役割",
          "complexity": "複雑度（low/medium/high）"
        }}
      ]
    }}
  ],
  "dependencies": [
    {{
      "name": "依存関係名",
      "type": "internal/external",
      "usage": "使用目的"
    }}
  ],
  "data_flow": "データの流れの説明",
  "error_handling": "エラーハンドリング方式",
  "performance_considerations": "パフォーマンスに関する考慮事項",
  "security_considerations": "セキュリティに関する考慮事項"
}}
```

分析は技術的に正確で、日本のIT業界の標準的な表現を使用してください。""",
    )

    # Japanese Specification Generation Prompt (Stage 2)
    JAPANESE_SPEC_PROMPT = PromptTemplate(
        input_variables=[
            "analysis_results",
            "document_title",
            "project_overview",
            "technical_requirements",
        ],
        template="""あなたは日本のIT業界で活躍する技術文書作成のエキスパートです。
以下の分析結果を基に、簡潔で実用的な詳細設計書を作成してください。

## プロジェクト概要:
{project_overview}

## 技術要件:
{technical_requirements}

## コード分析結果:
{analysis_results}

## 作成する文書:
{document_title}

## 出力形式:
以下の6つのセクションに従って、詳細設計書をMarkdown形式で作成してください：

# {document_title}

## 1. 概要

- システム概要
- 対象範囲（ファイル）
- 前提条件・制約事項（もし必要な場合）

## 2. アーキテクチャ設計

- システム構成図（Mermaid classDiagramで作成）
- 処理フロー概要
- 主要コンポーネント間の関係
- 関連するファイルや処理・呼び出されるメソッド・呼び出し元のメソッド

## 3. クラス・メソッド設計

### 3.1 クラス・メソッド一覧表

| クラス名 | 役割 | 主要メソッド | 備考 |
| -------- | ---- | ------------ | ---- |

### 3.2 クラス・メソッド詳細仕様

各クラス・メソッドについて以下を記載：

- クラス概要
- 属性一覧（型、初期値、説明）
- メソッド仕様（引数、戻り値、処理概要、例外）
- 継承・実装関係

## 4. インターフェース設計

- API 仕様
- 入出力データ形式
- エラーレスポンス仕様

## 5. データ設計

- データ構造
- データベーステーブル設計（該当する場合）
- データフロー図（Mermaid flowchartで作成）

## 6. 処理設計

### 6.1 主要処理フロー

- シーケンス図での表現（Mermaid sequenceDiagramで作成）
- 処理ステップの詳細説明

## 【重要な注意事項】:
1. 日本語で記述してください
2. 図表は Mermaid 記法で作成してください
3. 実装の詳細まで踏み込んで説明してください
4. 保守性・拡張性の観点も含めてください
5. クラス図は Mermaid classDiagram で作成
6. シーケンス図は Mermaid sequenceDiagram で作成
7. フローチャートは Mermaid flowchart で作成
8. 必要に応じて ER 図も含める
9. 簡潔で実用的な内容にし、冗長な記述は避ける
10. 各セクションは必須項目のみに絞り込む

それでは、詳細設計書を作成してください。""",
    )

    # Update Specification Prompt
    UPDATE_SPEC_PROMPT = PromptTemplate(
        input_variables=["existing_spec", "changes", "change_summary"],
        template="""既存の仕様書を変更内容に基づいて更新してください。

## 既存仕様書:
{existing_spec}

## 変更概要:
{change_summary}

## 詳細変更内容:
{changes}

## 更新要件:
1. 変更された部分のみを更新する
2. 既存の文書構造を保持する
3. 変更履歴を記録する
4. 整合性を保つ

## 出力形式:
更新された仕様書をMarkdown形式で出力し、変更箇所がわかるように以下の形式で変更履歴を追加してください：

### 変更履歴
| 日付 | 変更箇所 | 変更内容 | 変更理由 |
|------|----------|----------|----------|
| YYYY-MM-DD | セクション名 | 変更の説明 | 変更理由 |

更新された仕様書を出力してください。""",
    )

    # Section Update Prompt (for updater.py)
    SECTION_UPDATE_PROMPT = PromptTemplate(
        input_variables=["section_content", "change_summary"],
        template="""以下のセクションを変更内容に基づいて更新してください。

## 現在のセクション内容:
{section_content}

## 変更内容:
{change_summary}

## 更新要件:
1. 既存の構造を保持する
2. 変更された部分のみを更新する
3. 日本語の技術文書として適切な表現を使用する
4. マークダウン形式で出力する

更新されたセクション内容を出力してください：""",
    )

    # System Overview Prompt (for generator.py)
    SYSTEM_OVERVIEW_PROMPT = PromptTemplate(
        input_variables=["module_count", "function_count", "class_count"],
        template="""このシステムは{module_count}個のモジュールで構成され、
{function_count}個の関数と{class_count}個のクラスを含んでいます。
各モジュールは明確な責務を持ち、適切に分離された設計となっています。""",
    )

    # Class Structure Analysis Prompt (for class-aware analysis)
    CLASS_STRUCTURE_PROMPT = PromptTemplate(
        input_variables=["class_name", "class_methods", "class_content"],
        template="""あなたは日本のITエンジニアです。以下のクラス構造を分析し、正確なクラス情報を提供してください。

## クラス名: {class_name}
## メソッド一覧: {class_methods}

## クラス内容:
```python
{class_content}
```

## 重要な指示:
- このクラスのすべてのメソッドは「{class_name}」クラスに所属するものとして記録してください
- メソッドの親クラスを明確に示してください
- 「不明」や「推測」という表現は使用しないでください

## 出力形式:
以下のJSON形式で回答してください:
{{
  "class_name": "{class_name}",
  "purpose": "クラスの役割説明",
  "methods": [
    {{
      "name": "メソッド名",
      "purpose": "メソッドの役割",
      "parent_class": "{class_name}"
    }}
  ],
  "complexity": "複雑度（low/medium/high）"
}}
""",
    )


class JapanesePromptHelper:
    """Helper class for Japanese prompt formatting."""

    @staticmethod
    def format_function_list(functions: list) -> str:
        """Format function list for Japanese prompts."""
        if not functions:
            return "関数は定義されていません。"

        formatted = []
        for func in functions:
            # Reason: Ensure parameters are strings before joining to avoid type errors
            params_raw = func.get("parameters", [])
            params_str = [str(p) if not isinstance(p, str) else p for p in params_raw]
            params = ", ".join(params_str)
            formatted.append(
                f"- **{func.get('name', 'unknown')}**({params}): {func.get('purpose', '目的不明')}"
            )

        return "\n".join(formatted)

    @staticmethod
    def format_class_list(classes: list) -> str:
        """Format class list for Japanese prompts with enhanced class structure awareness."""
        if not classes:
            return "クラスは定義されていません。"

        formatted = []
        for cls in classes:
            # Reason: Ensure methods are strings before joining to avoid type errors
            methods_raw = cls.get("methods", [])
            methods_str = [str(m) if not isinstance(m, str) else m for m in methods_raw]
            methods = ", ".join(methods_str)

            # Enhanced formatting with class structure awareness
            class_name = cls.get('name', 'unknown')
            purpose = cls.get('purpose', '目的不明')

            # Add method details if available
            method_details = cls.get('method_details', [])
            if method_details:
                method_info = []
                for method in method_details:
                    method_name = method.get('name', 'unknown')
                    method_purpose = method.get('purpose', '目的不明')
                    method_info.append(f"    - {method_name}: {method_purpose}")
                method_details_str = "\n".join(method_info)

                formatted.append(
                    f"- **{class_name}**: {purpose}\n"
                    f"  - メソッド: {methods}\n"
                    f"  - メソッド詳細:\n{method_details_str}"
                )
            else:
                formatted.append(
                    f"- **{class_name}**: {purpose}\n"
                    f"  - メソッド: {methods}"
                )

        return "\n".join(formatted)

    @staticmethod
    def format_dependency_list(dependencies: list) -> str:
        """Format dependency list for Japanese prompts."""
        if not dependencies:
            return "外部依存関係はありません。"

        formatted = []
        for dep in dependencies:
            dep_type = dep.get("type", "unknown")
            usage = dep.get("usage", "用途不明")
            formatted.append(
                f"- **{dep.get('name', 'unknown')}** ({dep_type}): {usage}"
            )

        return "\n".join(formatted)

    @staticmethod
    def create_analysis_summary(analysis_data: dict[str, Any]) -> str:
        """Create a formatted analysis summary."""
        summary_parts = []

        # Overview
        if overview := analysis_data.get("overview"):
            summary_parts.append(f"**概要**: {overview}")

        # Functions
        if functions := analysis_data.get("functions"):
            summary_parts.append("**関数**:")
            summary_parts.append(JapanesePromptHelper.format_function_list(functions))

        # Classes
        if classes := analysis_data.get("classes"):
            summary_parts.append("**クラス**:")
            summary_parts.append(JapanesePromptHelper.format_class_list(classes))

        # Dependencies
        if dependencies := analysis_data.get("dependencies"):
            summary_parts.append("**依存関係**:")
            summary_parts.append(
                JapanesePromptHelper.format_dependency_list(dependencies)
            )

        # Data flow
        if data_flow := analysis_data.get("data_flow"):
            summary_parts.append(f"**データフロー**: {data_flow}")

        # Error handling
        if error_handling := analysis_data.get("error_handling"):
            summary_parts.append(f"**エラーハンドリング**: {error_handling}")

        return "\n\n".join(summary_parts)
