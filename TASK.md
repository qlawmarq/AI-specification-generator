# 詳細設計書生成テンプレートのリファクタリング

本プロジェクトはコードベースから詳細設計書を生成するプロジェクトです。

以下のようなアーキテクチャです。

```
CLI Layer (Typer + Rich)
    ↓
Core Processing (AsyncGenerator + Streaming)
    ↓
Semantic Analysis (Tree-sitter + AST)
    ↓
LLM Generation (LangChain + Progressive Prompting)
    ↓
Japanese Templates (IT Industry Standards)
    ↓
Output Generation (Markdown + Metadata)
```

## 課題・修正したい点

- 現在の設計書のテンプレートのコードは膨大かつ冗長で、使われていない要素や変数を多く含んでしまっている。
  - `src/spec_generator/templates/japanese_spec.py`
  - `src/spec_generator/templates/prompts.py`
- そのため、よりシンプルで可読性の高いコードにリファクタリングしたい。
- AST によるパースの処理など既存処理には影響を与えないようにリファクタリングしたい。
- 処理を増やすことは望ましくありません。不要な処理を削除し、長期的な保守性を考慮してリファクタリングしてください。

以下があるべき生成物のテンプレートです:

```md
## 1. 概要

- システム概要
- 対象範囲（ファイル）
- 前提条件・制約事項（もし必要な場合）

## 2. アーキテクチャ設計

- システム構成図
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
- データフロー図

## 6. 処理設計

### 6.1 主要処理フロー

- シーケンス図での表現
- 処理ステップの詳細説明

【注意事項】

- 日本語で記述してください
- 図表は Mermaid 記法で作成してください
- 実装の詳細まで踏み込んで説明してください
- 保守性・拡張性の観点も含めてください
- クラス図は Mermaid classDiagram で作成
- シーケンス図は Mermaid sequenceDiagram で作成
- フローチャートは Mermaid flowchart で作成
- 必要に応じて ER 図も含める
```

## 関連するコード

- `src/spec_generator/templates/japanese_spec.py`
- `src/spec_generator/templates/prompts.py`
- `src/spec_generator/core/generator.py`
- `src/spec_generator/core/updater.py`

## テスト

必ず CLI を実行し、アウトプットを確認してください。（単体テストより前にアウトプットを確認すること）
