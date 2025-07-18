"""
Document section generators for specification templates.

This module contains methods for generating specific sections
of specification documents.
"""

from typing import Any


class DocumentSectionGenerator:
    """Generator for individual document sections."""

    def __init__(self, table_formatter):
        self.table_formatter = table_formatter

    def generate_overview_section(self, document_data: dict[str, Any]) -> str:
        """Generate overview section."""
        overview = document_data.get("overview", {})
        system_overview = overview.get(
            "system_overview", "システム概要が定義されていません"
        )

        # Extract target files from modules
        target_files = []
        if modules := document_data.get("modules"):
            for module_name in modules.keys():
                target_files.append(f"- {module_name}")

        target_files_str = (
            "\n".join(target_files)
            if target_files
            else "- 対象ファイルが定義されていません"
        )

        constraints = overview.get("constraints", "特になし")

        return f"""## 1. 概要

- **システム概要**: {system_overview}
- **対象範囲（ファイル）**:
{target_files_str}
- **前提条件・制約事項（もし必要な場合）**: {constraints}"""

    def generate_architecture_section(self, document_data: dict[str, Any]) -> str:
        """Generate architecture section with Mermaid diagrams."""
        architecture = document_data.get("architecture", {})
        modules = document_data.get("modules", {})

        # Generate Mermaid class diagram
        mermaid_diagram = "```mermaid\nclassDiagram\n"
        for _module_name, module_data in modules.items():
            classes = module_data.get("classes", [])
            for cls in classes:
                class_name = cls.get("name", "UnknownClass")
                methods = cls.get("methods", [])
                mermaid_diagram += f"    class {class_name} {{\n"
                for method in methods[:3]:  # Limit to first 3 methods
                    mermaid_diagram += f"        +{method}()\n"
                mermaid_diagram += "    }\n"
        mermaid_diagram += "```"

        # Component relationships
        component_relationships = []
        for module_name, module_data in modules.items():
            dependencies = module_data.get("dependencies", [])
            for dep in dependencies:
                if dep.get("type") == "internal":
                    dep_name = dep.get("name")
                    dep_usage = dep.get("usage", "依存関係")
                    component_relationships.append(
                        f"- **{module_name}** → **{dep_name}**: {dep_usage}"
                    )

        relationships_str = (
            "\n".join(component_relationships)
            if component_relationships
            else "- 主要コンポーネント間の関係が定義されていません"
        )

        return f"""## 2. アーキテクチャ設計

### システム構成図
{mermaid_diagram}

### 処理フロー概要
{architecture.get("overview", "システム全体の処理フローを記述")}

### 主要コンポーネント間の関係
{relationships_str}

### 関連するファイルや処理・呼び出されるメソッド・呼び出し元のメソッド
{self._generate_method_relationships(modules)}"""

    def generate_class_method_section(self, document_data: dict[str, Any]) -> str:
        """Generate class and method design section with table constraints."""
        modules = document_data.get("modules", {})

        # Generate class/method table using formatter
        table_rows = []
        detailed_specs = []

        for _module_name, module_data in modules.items():
            # Functions
            functions = module_data.get("functions", [])
            for func in functions:
                func_name = func.get("name", "unknown")
                purpose = func.get("purpose", "未定義")
                inputs = func.get("inputs", [])
                complexity = func.get("complexity", "medium")
                
                # Use table formatter for proper constraints
                formatted_row = self.table_formatter.create_table_row(
                    class_name=f"{func_name} (関数)",
                    role=purpose,
                    methods=inputs,  # For functions, show inputs as "methods"
                    remarks=f"複雑度: {complexity}"
                )
                table_rows.append(formatted_row)

            # Classes
            classes = module_data.get("classes", [])
            for cls in classes:
                cls_name = cls.get("name", "unknown")
                purpose = cls.get("purpose", "未定義")
                methods = cls.get("methods", [])
                pattern = cls.get("design_pattern", "なし")
                
                # Use table formatter for proper constraints
                formatted_row = self.table_formatter.create_table_row(
                    class_name=cls_name,
                    role=purpose,
                    methods=methods,
                    remarks=f"パターン: {pattern}"
                )
                table_rows.append(formatted_row)

                # Add detailed specification
                attributes = ", ".join(cls.get("attributes", []))
                # Truncate attributes if too long
                if len(attributes) > 100:
                    attributes = attributes[:97] + "..."
                    
                detailed_specs.append(
                    f"""
#### {cls_name}

**クラス概要**: {purpose}

**属性一覧**: {attributes if attributes else "属性が定義されていません"}

**メソッド仕様**:
{self._format_method_specs(cls.get("methods", []))}

**継承・実装関係**: {cls.get("inheritance", "なし")}"""
                )

        table_content = (
            "\n".join(table_rows)
            if table_rows
            else "| 未定義 | 未定義 | 未定義 | 未定義 |"
        )
        detailed_content = (
            "\n".join(detailed_specs)
            if detailed_specs
            else "詳細仕様が定義されていません"
        )

        return f"""## 3. クラス・メソッド設計

### 3.1 クラス・メソッド一覧表

| クラス名 | 役割 | 主要メソッド | 備考 |
| -------- | ---- | ------------ | ---- |
{table_content}

### 3.2 クラス・メソッド詳細仕様
{detailed_content}"""

    def generate_interface_section(self, document_data: dict[str, Any]) -> str:
        """Generate interface design section."""
        modules = document_data.get("modules", {})

        # Extract API-like functions
        api_specs = []
        for _module_name, module_data in modules.items():
            functions = module_data.get("functions", [])
            for func in functions:
                func_name = func.get("name", "").lower()
                func_purpose = func.get("purpose", "").lower()
                if "api" in func_name or "interface" in func_purpose:
                    inputs = func.get("inputs", [])
                    outputs = func.get("outputs", "未定義")
                    api_specs.append(
                        f"""
### {func.get("name", "未定義")}

**入力データ形式**: {", ".join(inputs) if inputs else "パラメータなし"}
**出力データ形式**: {outputs}
**エラーレスポンス仕様**: 標準的なエラーハンドリングを適用"""
                    )

        api_content = (
            "\n".join(api_specs)
            if api_specs
            else """
### 標準的なインターフェース

**入力データ形式**: 各関数の仕様に従う
**出力データ形式**: 各関数の戻り値仕様に従う
**エラーレスポンス仕様**: 例外処理による標準的なエラーハンドリング"""
        )

        return f"""## 4. インターフェース設計
{api_content}"""

    def generate_data_design_section(self, document_data: dict[str, Any]) -> str:
        """Generate data design section."""
        modules = document_data.get("modules", {})

        # Extract data structures
        data_structures = []
        for _module_name, module_data in modules.items():
            classes = module_data.get("classes", [])
            for cls in classes:
                attributes = cls.get("attributes", [])
                if attributes:
                    attr_list = "\n".join(
                        [f"- {attr}: データ型未定義" for attr in attributes]
                    )
                    data_structures.append(
                        f"""
### {cls.get("name", "未定義")}
**用途**: {cls.get("purpose", "データ構造")}
**フィールド**:
{attr_list}"""
                    )

        structures_content = (
            "\n".join(data_structures)
            if data_structures
            else "データ構造が定義されていません"
        )

        # Generate Mermaid ER diagram if applicable
        er_diagram = ""
        if data_structures:
            er_diagram = """
### データフロー図
```mermaid
flowchart TD
    A[入力データ] --> B[データ処理]
    B --> C[出力データ]
    B --> D[データ保存]
```"""

        return f"""## 5. データ設計

### データ構造
{structures_content}

### データベーステーブル設計（該当する場合）
現在のシステムではデータベーステーブルは使用されていません
{er_diagram}"""

    def generate_processing_section(self, document_data: dict[str, Any]) -> str:
        """Generate processing design section with Mermaid sequence diagrams."""
        modules = document_data.get("modules", {})

        # Generate sequence diagram
        sequence_diagram = (
            "```mermaid\n"
            "sequenceDiagram\n"
            "    participant User\n"
            "    participant System\n"
        )

        # Add main processing flow
        main_functions = []
        for _module_name, module_data in modules.items():
            functions = module_data.get("functions", [])
            main_functions.extend([f.get("name", "unknown") for f in functions[:2]])

        step_num = 1
        for func in main_functions[:4]:  # Limit to 4 steps
            sequence_diagram += f"    User->>System: {step_num}. {func}を実行\n"
            sequence_diagram += f"    System-->>User: {step_num}. 処理結果を返却\n"
            step_num += 1

        sequence_diagram += "```"

        # Processing steps
        processing_steps = []
        for i, func in enumerate(main_functions[:5], 1):
            processing_steps.append(f"{i}. **{func}**: 主要な処理ロジックを実行")

        steps_content = (
            "\n".join(processing_steps)
            if processing_steps
            else "1. システムの主要処理を実行"
        )

        return f"""## 6. 処理設計

### 6.1 主要処理フロー

#### シーケンス図での表現
{sequence_diagram}

#### 処理ステップの詳細説明
{steps_content}"""

    def _generate_method_relationships(self, modules: dict[str, Any]) -> str:
        """Generate method relationship descriptions."""
        relationships = []
        for module_name, module_data in modules.items():
            functions = module_data.get("functions", [])
            for func in functions[:3]:  # Limit to first 3 functions
                func_name = func.get("name", "unknown")
                func_purpose = func.get("purpose", "処理を実行")
                relationships.append(
                    f"- **{func_name}** (in {module_name}): {func_purpose}"
                )

        return (
            "\n".join(relationships)
            if relationships
            else "- メソッド関係が定義されていません"
        )

    def _format_method_specs(self, methods: list[str]) -> str:
        """Format method specifications."""
        if not methods:
            return "メソッドが定義されていません"

        specs = []
        for method in methods[:3]:  # Limit to first 3 methods
            specs.append(f"- **{method}**: 処理概要、引数、戻り値、例外を記述")

        return "\n".join(specs)