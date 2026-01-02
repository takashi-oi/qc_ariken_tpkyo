# Docker クイックスタートガイド

## 簡単な手順

### 1. 事前準備

#### Windows/macOS
- Docker Desktopをインストール
- Docker Desktopを起動

#### Linux
- Docker EngineとDocker Composeをインストール
- Dockerデーモンが起動していることを確認

### 2. 起動方法

#### オプションA: 起動スクリプトを使用（推奨）
```bash
./start_docker.sh
```

#### オプションB: docker-composeコマンドで直接起動
```bash
docker-compose up --build -d
```

### 3. アプリケーションにアクセス
ブラウザで開く: **http://localhost:8501**

### 4. 停止方法
```bash
docker-compose down
```

## 主要コマンド

| 操作 | コマンド |
|------|---------|
| コンテナ起動 | `docker-compose up -d` |
| コンテナ停止 | `docker-compose down` |
| ログ確認 | `docker-compose logs -f` |
| コンテナ再起動 | `docker-compose restart` |
| コンテナ削除 | `docker-compose down -v` |

## トラブルシューティング

**ポート8501が使用中の場合:**
- `docker-compose.yml`の`ports`セクションを`8502:8501`に変更

**Dockerが起動しない場合:**
- Docker Desktop（Windows/macOS）またはDockerデーモン（Linux）が起動しているか確認
- `docker ps`コマンドでDockerが動作しているか確認

**ビルドが遅い場合:**
- `.dockerignore`が正しく設定されているか確認
- 仮想環境（`.venv`）やキャッシュファイルが除外されているか確認

**コンテナのログを確認:**
```bash
docker-compose logs -f
```

**コンテナの状態を確認:**
```bash
docker ps
docker-compose ps
```













