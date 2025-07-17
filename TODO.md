# TODO - 動作確認で発見された問題点

## 概要
2025年07月17日にこのツールの動作確認を実施した結果、以下の問題が発見されました。

## 発見された問題

### 1. コマンドタイムアウトエラー
**症状**: `generate`コマンドが2分でタイムアウトする
**再現手順**:
```bash
uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test-spec.md
```
**詳細**: 
- エラーメッセージ: "Command timed out after 2m 0.0s"
- LLM生成エラー: "LLM generation failed" および "Analysis failed for chunk"
- 仕様書は部分的に生成されるが、途中で切れている（378行で終了）
**影響**: 長い処理時間に加え、完全な仕様書が生成されない

### 2. 生成時間の問題
**症状**: `generate`コマンドが非常に長い時間かかる（タイムアウトに至る場合も）
**再現手順**:
```bash
uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test-spec.md
```
**詳細**: 
- 処理時間: 95.21秒
- 対象ファイル: samples/Python/test_sample.py (267行)
- チャンク数: 14個
- 使用モデル: gemini-2.5-flash

**影響**: 小さなファイルでも1分以上かかるため、実用性に問題がある

### 3. LangChainの非推奨警告
**症状**: `BaseChatModel.predict`の廃止予定警告が発生
**再現手順**: 上記と同じ`generate`コマンドを実行
**詳細**: 
```
LangChainDeprecationWarning: The method `BaseChatModel.predict` was deprecated in langchain-core 0.1.7 and will be removed in 1.0. Use :meth:`~invoke` instead.
```
**影響**: 将来的なバージョンアップで動作しなくなる可能性

### 4. Google Generative AI パラメータ警告
**症状**: `http_async_client`パラメータの警告が発生
**再現手順**: 上記と同じ`generate`コマンドを実行
**詳細**: 
```
WARNING - Unexpected argument 'http_async_client' provided to ChatGoogleGenerativeAI
```
**影響**: 設定が正しく反映されていない可能性

### 5. update コマンドの生成品質問題
**症状**: `update`コマンドで生成される仕様書の品質が低い
**再現手順**:
1. samples/Python/test_sample.pyに`average`メソッドを追加
2. `uv run python -m spec_generator.cli update . --output spec-updates`を実行
**詳細**: 
- 生成された仕様書にクラス名が「不明」と表示される
- 正確な変更内容が反映されない
- 元の仕様書と比較して品質が大幅に低下

### 6. Gitファイル解析エラー
**症状**: 新しく追加されたファイルの解析時にGitエラーが発生
**再現手順**: 上記と同じ`update`コマンドを実行
**詳細**: 
```
ERROR - Failed to analyze tests/test_class_structure_recognition.py: Git command error: Git command failed: git show HEAD~1:tests/test_class_structure_recognition.py
Error: fatal: path 'tests/test_class_structure_recognition.py' exists on disk, but not in 'HEAD~1'
```
**影響**: 新しく追加されたファイルが正しく解析されない

### 7. updateコマンドのGit要件問題
**症状**: `update`コマンドはGitリポジトリでないと動作しない
**再現手順**:
```bash
uv run python -m spec_generator.cli update samples/Python --output spec-updates
```
**詳細**: 
- エラーメッセージ: "samples/Python is not a Git repository"
- ドキュメントではGit要件について明記されていない可能性
**影響**: 非Gitプロジェクトでは使用できない

## 推奨対応

### 優先度: 高
1. **生成時間の最適化**: チャンク処理の並列化や、より効率的なプロンプト設計を検討
2. **update コマンドの品質改善**: 差分検出ロジックと仕様書生成の品質向上

### 優先度: 中
3. **LangChainの非推奨メソッド対応**: `predict`から`invoke`への移行
4. **Gitファイル解析の改善**: 新規ファイルの適切な処理

### 優先度: 低
5. **Google Generative AI パラメータ警告の修正**: パラメータ設定の見直し

## 動作確認結果

### 正常に動作した機能
- ✅ `config-info`コマンド: 設定情報の表示
- ✅ `install-parsers`コマンド: Tree-sitterパーサーのインストール（未テスト）
- ⚠️ `generate`コマンド: 仕様書の生成（タイムアウトするが部分的に生成される）
- ✅ 日本語仕様書の品質: 適切な日本語IT用語を使用した高品質な仕様書（generateコマンドの場合）

### 問題のある機能
- ❌ `generate`コマンド: タイムアウトエラーで完全な仕様書が生成されない
- ❌ `update`コマンド: 生成される仕様書の品質が極めて低い
- ⚠️ パフォーマンス: 小さなファイルでも2分以上かかりタイムアウトする
- ⚠️ 警告メッセージ: 非推奨メソッドやパラメータの警告
- ⚠️ Git依存性: updateコマンドはGitリポジトリが必須

## 検証環境
- OS: macOS (Darwin 24.5.0)
- Python: 3.13.1
- 実行方法: `uv run`
- 対象ファイル: samples/Python/test_sample.py (267行)
- 使用モデル: gemini-2.5-flash