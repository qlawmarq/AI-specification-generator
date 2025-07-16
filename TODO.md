# 動作確認で発見された問題とバグ

## 概要
このドキュメントは、AI仕様書ジェネレーターの動作確認中に発見された問題と、その再現手順をまとめています。

## 発見された問題

### 1. updateコマンドのセマンティック差分検出に関する問題

#### 問題の概要
`update` コマンドが新しく追加されたファイルの変更を正しく検出できない問題があります。

#### 問題の詳細
- `samples/Python/test_sample.py` ファイルに新しいメソッド (`square()`, `cube()`) を追加した後、`update` コマンドを実行しても「No semantic changes detected」と表示される
- ログには以下のエラーが記録される：
  ```
  Failed to analyze samples/Python/test_sample.py: Git command error: Git command failed: git show HEAD~1:samples/Python/test_sample.py
  Error: fatal: path 'samples/Python/test_sample.py' exists on disk, but not in 'HEAD~1'
  ```

#### 再現手順
1. `samples/Python/test_sample.py` にメソッドを追加
2. 変更をコミット: `git add samples/Python/test_sample.py && git commit -m "Add new methods"`
3. updateコマンドを実行: `uv run python -m spec_generator.cli update . --output spec-updates --existing-spec test-spec.md`
4. 結果：セマンティック変更が検出されない

#### 原因分析
- `SemanticDiffDetector` が新しく追加されたファイルを処理する際に、前のコミット (`HEAD~1`) にファイルが存在しないため、gitコマンドが失敗している
- 新規追加ファイルと既存ファイルの変更を区別して処理する仕組みが不足している

#### 期待される動作
- 新しく追加されたファイルの場合、前のコミットとの比較ではなく、ファイル全体を新規追加として扱うべき
- 追加されたメソッドやクラスをセマンティック変更として正しく検出し、仕様書の更新に反映するべき

#### 影響度
**中** - updateコマンドが新規追加されたコードに対して機能しないため、インクリメンタル更新の重要な機能が制限される

## その他の観察事項

### 1. 正常に動作した機能
- `config-info` コマンド：設定情報を正しく表示
- `install-parsers` コマンド：Tree-sitterパーサーを正常にインストール  
- `generate` コマンド：サンプルコードから日本語の詳細設計書を正常に生成（約69秒で完了）

### 2. 生成された仕様書の品質
- 生成された仕様書 (`test-spec.md`) は適切な日本語で記述されている
- クラス図、メソッドの説明、引数・戻り値の詳細が含まれている
- Mermaid図も含まれており、視覚的にわかりやすい構成

### 3. パフォーマンス
- 仕様書生成時間：約69秒（254行のPythonコード、11チャンク）
- 使用モデル：gemini-2.5-flash
- 処理中にLangChainの非推奨警告が表示されるが、機能には影響なし

## 修正の優先度

1. **高**: updateコマンドの新規ファイル対応（セマンティック差分検出の改善）
2. **低**: LangChainの非推奨警告の対応（機能に影響しないため）

## テスト環境

- Python実行環境: uv + virtual environment
- Git リポジトリ: feat/first_pr ブランチ
- LLMモデル: Google Gemini 2.5 Flash
- 設定: OpenAI API Key, Azure Endpoint が設定済み