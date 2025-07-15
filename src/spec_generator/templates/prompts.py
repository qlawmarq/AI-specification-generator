"""
LangChain prompt templates for Japanese specification generation.

This module defines prompt templates for progressive prompting strategy,
including analysis prompts and Japanese specification generation prompts.
"""

from typing import Any

from langchain.prompts import PromptTemplate


class PromptTemplates:
    """Collection of prompt templates for specification generation."""

    # Code Analysis Prompt (Stage 1)
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
      "complexity": "複雑度（low/medium/high）"
    }}
  ],
  "classes": [
    {{
      "name": "クラス名",
      "purpose": "役割",
      "methods": ["メソッド名のリスト"],
      "attributes": ["属性名のリスト"],
      "design_pattern": "使用されているデザインパターン"
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

分析は技術的に正確で、日本のIT業界の標準的な表現を使用してください。"""
    )

    # Japanese Specification Generation Prompt (Stage 2)
    JAPANESE_SPEC_PROMPT = PromptTemplate(
        input_variables=["analysis_results", "document_title", "project_overview", "technical_requirements"],
        template="""あなたは日本のIT業界で活躍する技術文書作成のエキスパートです。
以下の分析結果を基に、日本のIT業界標準フォーマットでの詳細設計書を作成してください。

## プロジェクト概要:
{project_overview}

## 技術要件:
{technical_requirements}

## コード分析結果:
{analysis_results}

## 作成する文書:
{document_title}

## 出力形式:
以下の構造に従って、詳細設計書をMarkdown形式で作成してください：

# {document_title}

## 1. 概要
### 1.1 文書の目的
### 1.2 システム概要
### 1.3 対象読者

## 2. システム構成
### 2.1 全体アーキテクチャ
### 2.2 主要コンポーネント
### 2.3 技術スタック

## 3. 詳細設計
### 3.1 モジュール設計
#### 3.1.1 [モジュール名]
- **目的**: モジュールの役割と責務
- **主要機能**: 提供する機能の一覧
- **インターフェース**: 外部とのやり取り
- **内部構造**: クラス・関数の構成

### 3.2 データ設計
#### 3.2.1 データ構造
#### 3.2.2 データフロー

### 3.3 処理設計
#### 3.3.1 主要処理フロー
#### 3.3.2 例外処理方式
#### 3.3.3 エラーハンドリング

## 4. 非機能要件
### 4.1 性能要件
### 4.2 セキュリティ要件
### 4.3 可用性要件
### 4.4 保守性要件

## 5. 運用設計
### 5.1 デプロイメント方式
### 5.2 監視・ログ
### 5.3 バックアップ・復旧

## 6. 付録
### 6.1 用語集
### 6.2 参考資料

## 作成時の注意事項:
1. 日本のIT業界で標準的に使用される用語を使用する
2. 技術的な詳細は正確に記述する
3. 図表は必要に応じてマークダウン形式で挿入する
4. コード例は適切にフォーマットする
5. 可読性を重視し、適切な見出し構造を使用する
6. 業務システムの設計書として十分な詳細度を保つ

それでは、詳細設計書を作成してください。"""
    )

    # Module Summary Prompt
    MODULE_SUMMARY_PROMPT = PromptTemplate(
        input_variables=["module_analyses", "module_name"],
        template="""以下は{module_name}モジュールの各ファイルの分析結果です。
これらを統合して、モジュール全体の概要を作成してください。

## ファイル別分析結果:
{module_analyses}

## 出力要件:
以下の形式でモジュールサマリーを作成してください：

### {module_name} モジュール概要

**主要責務**: モジュールの主な責任

**提供機能**:
- 機能1: 説明
- 機能2: 説明

**内部構成**:
- ファイル1: 役割
- ファイル2: 役割

**外部依存関係**:
- 依存関係1: 用途
- 依存関係2: 用途

**設計パターン**:
使用されている主要な設計パターンとその適用理由

**技術的特徴**:
- 特徴1
- 特徴2

**注意点・制約事項**:
実装上の注意点や制約事項があれば記載

日本のIT業界標準の表現を使用し、技術的に正確な情報を提供してください。"""
    )

    # API Documentation Prompt
    API_DOC_PROMPT = PromptTemplate(
        input_variables=["function_analysis", "class_analysis"],
        template="""以下の関数・クラス分析結果からAPI仕様書を作成してください。

## 関数分析結果:
{function_analysis}

## クラス分析結果:
{class_analysis}

## 出力形式:
Markdown形式でAPI仕様書を作成してください：

# API仕様書

## 関数一覧

### 関数名
**概要**: 関数の概要説明

**パラメータ**:
| パラメータ名 | 型 | 必須 | 説明 |
|-------------|---|-----|------|
| param1 | string | Yes | パラメータの説明 |

**戻り値**:
| 型 | 説明 |
|----|------|
| return_type | 戻り値の説明 |

**使用例**:
```python
# 使用例のコード
```

**例外**:
- Exception1: 発生条件
- Exception2: 発生条件

## クラス一覧

### クラス名
**概要**: クラスの概要説明

**コンストラクタ**:
パラメータと初期化処理の説明

**メソッド**:
各メソッドの詳細仕様

**属性**:
クラス属性の説明

**使用例**:
```python
# 使用例のコード
```

日本のIT業界標準のAPI仕様書フォーマットに従って作成してください。"""
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

更新された仕様書を出力してください。"""
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

更新されたセクション内容を出力してください："""
    )

    # System Overview Prompt (for generator.py)
    SYSTEM_OVERVIEW_PROMPT = PromptTemplate(
        input_variables=["module_count", "function_count", "class_count"],
        template="""このシステムは{module_count}個のモジュールで構成され、
{function_count}個の関数と{class_count}個のクラスを含んでいます。
各モジュールは明確な責務を持ち、適切に分離された設計となっています。"""
    )

    # Document Section Prompt (for japanese_spec.py)
    DOCUMENT_SECTION_PROMPT = PromptTemplate(
        input_variables=["architecture_overview", "component_list", "tech_list"],
        template="""## 2. システム構成

### 2.1 全体アーキテクチャ

{architecture_overview}

### 2.2 主要コンポーネント

{component_list}

### 2.3 技術スタック

{tech_list}"""
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
            params = ", ".join(func.get("parameters", []))
            formatted.append(
                f"- **{func.get('name', 'unknown')}**({params}): {func.get('purpose', '目的不明')}"
            )

        return "\n".join(formatted)

    @staticmethod
    def format_class_list(classes: list) -> str:
        """Format class list for Japanese prompts."""
        if not classes:
            return "クラスは定義されていません。"

        formatted = []
        for cls in classes:
            methods = ", ".join(cls.get("methods", []))
            formatted.append(
                f"- **{cls.get('name', 'unknown')}**: {cls.get('purpose', '目的不明')}\n"
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
            formatted.append(f"- **{dep.get('name', 'unknown')}** ({dep_type}): {usage}")

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
            summary_parts.append(JapanesePromptHelper.format_dependency_list(dependencies))

        # Data flow
        if data_flow := analysis_data.get("data_flow"):
            summary_parts.append(f"**データフロー**: {data_flow}")

        # Error handling
        if error_handling := analysis_data.get("error_handling"):
            summary_parts.append(f"**エラーハンドリング**: {error_handling}")

        return "\n\n".join(summary_parts)


# Commonly used Japanese IT terms for consistency
JAPANESE_TERMS = {
    # Architecture terms
    "architecture": "アーキテクチャ",
    "component": "コンポーネント",
    "module": "モジュール",
    "interface": "インターフェース",
    "framework": "フレームワーク",

    # Design terms
    "design_pattern": "デザインパターン",
    "specification": "仕様書",
    "requirement": "要件",
    "implementation": "実装",
    "configuration": "設定",

    # Technical terms
    "database": "データベース",
    "api": "API",
    "service": "サービス",
    "function": "関数",
    "class": "クラス",
    "method": "メソッド",
    "parameter": "パラメータ",
    "return_value": "戻り値",
    "exception": "例外",
    "error_handling": "エラーハンドリング",

    # Process terms
    "process": "プロセス",
    "workflow": "ワークフロー",
    "deployment": "デプロイメント",
    "monitoring": "監視",
    "logging": "ログ",
    "backup": "バックアップ",
    "recovery": "復旧",

    # Quality terms
    "performance": "性能",
    "security": "セキュリティ",
    "availability": "可用性",
    "maintainability": "保守性",
    "scalability": "拡張性",
    "reliability": "信頼性",
}
