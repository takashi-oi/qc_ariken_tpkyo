# Cline Base URLとModel設定ガイド

## 概要

このドキュメントでは、Cline拡張機能でのBase URLとModelの設定方法について詳しく説明します。

## Base URL設定

### 1. ローカルOllama設定

```json
{
  "cline.baseUrl": "http://localhost:11434"
}
```

**説明**:
- `localhost:11434` - Ollamaのデフォルトエンドポイント
- ローカルマシンでOllamaを実行している場合の設定

### 2. リモートサーバー設定

```json
{
  "cline.baseUrl": "http://your-server-ip:11434"
}
```

**例**:
```json
{
  "cline.baseUrl": "http://192.168.1.100:11434"
}
```

### 3. カスタムポート設定

```json
{
  "cline.baseUrl": "http://localhost:8080"
}
```

### 4. HTTPS設定

```json
{
  "cline.baseUrl": "https://your-domain.com:11434"
}
```

## Model設定

### 1. 利用可能なモデル一覧

#### コード生成に最適なモデル
- `codellama:7b` - バランスの取れたコード生成
- `codellama:13b` - より高度なコード生成
- `codellama:34b` - 最高品質のコード生成

#### 汎用モデル
- `llama3.2:3b` - 軽量、高速処理
- `llama3.2:7b` - バランスの取れた性能
- `llama3.2:70b` - 最高性能

#### その他のモデル
- `mistral:7b` - 汎用性能
- `qwen2.5:7b` - 多言語対応
- `gemma2:2b` - 軽量モデル
- `phi3:3.8b` - 高速処理

### 2. モデル設定方法

#### VS Code設定での指定

```json
{
  "cline.model": "codellama:7b"
}
```

#### 設定ファイルでの指定

`.cline/config.json`:
```json
{
  "models": {
    "ollama": {
      "default_model": "codellama:7b",
      "models": [
        "codellama:7b",
        "llama3.2:7b",
        "mistral:7b"
      ]
    }
  }
}
```

## 詳細設定オプション

### 1. パフォーマンス設定

```json
{
  "cline.temperature": 0.3,        // 0.0-1.0 (低いほど決定論的)
  "cline.maxTokens": 2048,         // 最大トークン数
  "cline.timeout": 30000,          // タイムアウト（ミリ秒）
  "cline.retryAttempts": 3         // リトライ回数
}
```

### 2. 機能設定

```json
{
  "cline.autoComplete": true,      // 自動補完
  "cline.codeGeneration": true,    // コード生成
  "cline.refactoring": true,       // リファクタリング
  "cline.debugging": true,         // デバッグ支援
  "cline.testing": true,           // テスト生成
  "cline.documentation": true,     // ドキュメント生成
  "cline.showSuggestions": true,   // 提案表示
  "cline.inlineSuggestions": true  // インライン提案
}
```

## 設定の優先順位

1. **VS Code設定** (`.vscode/settings.json`) - 最高優先度
2. **プロジェクト設定** (`.cline/project.json`) - 中優先度
3. **グローバル設定** (`.cline/config.json`) - 低優先度

## 設定例

### 例1: ローカル開発環境

```json
{
  "cline.baseUrl": "http://localhost:11434",
  "cline.model": "codellama:7b",
  "cline.temperature": 0.3,
  "cline.maxTokens": 2048
}
```

### 例2: 高性能リモートサーバー

```json
{
  "cline.baseUrl": "http://192.168.1.100:11434",
  "cline.model": "llama3.2:70b",
  "cline.temperature": 0.2,
  "cline.maxTokens": 8192,
  "cline.timeout": 60000
}
```

### 例3: 軽量高速処理

```json
{
  "cline.baseUrl": "http://localhost:11434",
  "cline.model": "llama3.2:3b",
  "cline.temperature": 0.1,
  "cline.maxTokens": 1024,
  "cline.timeout": 15000
}
```

## トラブルシューティング

### Base URL接続エラー

1. **Ollamaサービスの確認**:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **ファイアウォール設定**:
   - ポート11434が開放されているか確認

3. **ネットワーク接続**:
   ```bash
   ping your-server-ip
   ```

### Model読み込みエラー

1. **利用可能モデルの確認**:
   ```bash
   ollama list
   ```

2. **モデルのダウンロード**:
   ```bash
   ollama pull codellama:7b
   ```

3. **モデルの削除と再ダウンロード**:
   ```bash
   ollama rm codellama:7b
   ollama pull codellama:7b
   ```

### パフォーマンス問題

1. **メモリ使用量の確認**:
   ```bash
   top -p $(pgrep ollama)
   ```

2. **モデルの軽量化**:
   - より小さいモデルを使用
   - `llama3.2:3b`や`codellama:7b`を試す

3. **タイムアウト設定の調整**:
   ```json
   {
     "cline.timeout": 60000
   }
   ```

## ベストプラクティス

### 1. 開発環境別の設定

#### 開発環境
```json
{
  "cline.model": "codellama:7b",
  "cline.temperature": 0.3,
  "cline.maxTokens": 2048
}
```

#### 本番環境
```json
{
  "cline.model": "llama3.2:70b",
  "cline.temperature": 0.1,
  "cline.maxTokens": 4096
}
```

### 2. プロジェクト別の最適化

#### Pythonプロジェクト
```json
{
  "cline.model": "codellama:7b",
  "cline.temperature": 0.2
}
```

#### Web開発プロジェクト
```json
{
  "cline.model": "llama3.2:7b",
  "cline.temperature": 0.4
}
```

### 3. セキュリティ考慮事項

- リモートサーバーを使用する場合はHTTPSを推奨
- APIキーが必要な場合は適切に管理
- ファイアウォール設定でアクセス制限

## 参考資料

- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Cline Extension Documentation](https://github.com/cline-ai/cline)
- [VS Code Settings Reference](https://code.visualstudio.com/docs/getstarted/settings) 