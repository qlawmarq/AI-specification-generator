# TODO - 動作確認で発見された問題点

## 概要

2025 年 07 月 17 日にこのツールの動作確認を実施した結果、以下の問題が発見されました。

## 発見された問題

### 1. LangChain の非推奨警告

**症状**: `BaseChatModel.predict`の廃止予定警告が発生
**再現手順**: 上記と同じ`generate`コマンドを実行
**詳細**:

```
LangChainDeprecationWarning: The method `BaseChatModel.predict` was deprecated in langchain-core 0.1.7 and will be removed in 1.0. Use :meth:`~invoke` instead.
```

**影響**: 将来的なバージョンアップで動作しなくなる可能性

### 2. Google Generative AI パラメータ警告

**症状**: `http_async_client`パラメータの警告が発生
**再現手順**: 上記と同じ`generate`コマンドを実行
**詳細**:

```
WARNING - Unexpected argument 'http_async_client' provided to ChatGoogleGenerativeAI
```

**影響**: 設定が正しく反映されていない可能性
