from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
from langchain.schema import Document

class SpecificationGenerator:
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.3,
            openai_api_key=api_key
        )
        
        # 段階的プロンプト設計
        self.analysis_prompt = PromptTemplate(
            input_variables=["code_content", "ast_info", "file_path"],
            template="""
あなたは熟練したソフトウェアアーキテクトです。
以下のコードを分析し、機能と責務を特定してください。

## ファイル: {file_path}

## AST情報:
{ast_info}

## コード内容:
{code_content}

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
  "functions": [
    {{
      "name": "関数名",
      "purpose": "役割",
      "inputs": ["入力パラメータ"],
      "outputs": "戻り値",
      "business_logic": "ビジネスロジック"
    }}
  ],
  "classes": [...],
  "dependencies": ["依存関係"],
  "data_flow": "データの流れ",
  "error_handling": "エラーハンドリング方式"
}}