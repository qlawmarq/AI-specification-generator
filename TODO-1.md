# TODO - 動作確認で発見された問題点

## 概要

2025 年 07 月 17 日にこのツールの動作確認を実施した結果、以下の問題が発見されました。

## 発見された問題

### 1. コマンドタイムアウトエラー

**症状**: `generate`コマンドが 2 分でタイムアウトする
**再現手順**:

```bash
uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test-spec.md
```

**詳細**:

- エラーメッセージ: "Command timed out after 2m 0.0s"
- LLM 生成エラー: "LLM generation failed" および "Analysis failed for chunk"
- 仕様書は部分的に生成されるが、途中で切れている（378 行で終了）
  **影響**: 長い処理時間に加え、完全な仕様書が生成されない

### 2. 生成時間の問題

**症状**: `generate`コマンドが非常に長い時間かかる（タイムアウトに至る場合も）
**再現手順**:

```bash
uv run python -m spec_generator.cli generate samples/Python/test_sample.py --output test-spec.md
```

**詳細**:

- 処理時間: 95.21 秒
- 対象ファイル: samples/Python/test_sample.py (267 行)
- チャンク数: 14 個
- 使用モデル: gemini-2.5-flash

**影響**: 小さなファイルでも 1 分以上かかるため、実用性に問題がある
