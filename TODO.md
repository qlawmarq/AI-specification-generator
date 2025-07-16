# TODO - 動作確認で発見された問題点

## 概要
2025年07月17日にこのツールの動作確認を実施した結果、以下の問題が発見されました。

## 発見された問題

### 1. 生成時間の問題
**症状**: `generate`コマンドが約95秒（1分35秒）かかる
**再現手順**:
```bash
uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test-spec.md
```
**詳細**: 
- 処理時間: 95.21秒
- 対象ファイル: samples/Python/test_sample.py (232行)
- チャンク数: 14個
- 使用モデル: gemini-2.5-flash

**影響**: 小さなファイルでも1分以上かかるため、実用性に問題がある

### 2. LangChainの非推奨警告
**症状**: `BaseChatModel.predict`の廃止予定警告が発生
**再現手順**: 上記と同じ`generate`コマンドを実行
**詳細**: 
```
LangChainDeprecationWarning: The method `BaseChatModel.predict` was deprecated in langchain-core 0.1.7 and will be removed in 1.0. Use :meth:`~invoke` instead.
```
**影響**: 将来的なバージョンアップで動作しなくなる可能性

### 3. Google Generative AI パラメータ警告
**症状**: `http_async_client`パラメータの警告が発生
**再現手順**: 上記と同じ`generate`コマンドを実行
**詳細**: 
```
WARNING - Unexpected argument 'http_async_client' provided to ChatGoogleGenerativeAI
```
**影響**: 設定が正しく反映されていない可能性

### 4. update コマンドの生成品質問題
**症状**: `update`コマンドで生成される仕様書の品質が低い
**再現手順**:
1. samples/Python/test_sample.pyに`root`メソッドを追加
2. `uv run python -m spec_generator.cli update . --output spec-updates`を実行
**詳細**: 
- 生成された仕様書にクラス名が「不明」と表示される
- 正確な変更内容が反映されない
- 元の仕様書と比較して品質が大幅に低下

### 5. Gitファイル解析エラー
**症状**: 新しく追加されたファイルの解析時にGitエラーが発生
**再現手順**: 上記と同じ`update`コマンドを実行
**詳細**: 
```
ERROR - Failed to analyze tests/test_class_structure_recognition.py: Git command error: Git command failed: git show HEAD~1:tests/test_class_structure_recognition.py
Error: fatal: path 'tests/test_class_structure_recognition.py' exists on disk, but not in 'HEAD~1'
```
**影響**: 新しく追加されたファイルが正しく解析されない

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
- ✅ `install-parsers`コマンド: Tree-sitterパーサーのインストール
- ✅ `generate`コマンド: 仕様書の生成（時間はかかるが正常に完了）
- ✅ 日本語仕様書の品質: 適切な日本語IT用語を使用した高品質な仕様書

### 問題のある機能
- ❌ `update`コマンド: 生成される仕様書の品質が低い
- ⚠️ パフォーマンス: 小さなファイルでも処理時間が長い
- ⚠️ 警告メッセージ: 非推奨メソッドやパラメータの警告

## 検証環境
- OS: macOS (Darwin 24.5.0)
- Python: 3.13.1
- 実行方法: `uv run`
- 対象ファイル: samples/Python/test_sample.py (232行)
- 使用モデル: gemini-2.5-flash