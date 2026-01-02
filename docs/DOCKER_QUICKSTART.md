# Docker クイックスタートガイド（Windows）

## 簡単な手順

### 1. 事前準備
- Docker Desktop for Windowsをインストール
- Docker Desktopを起動

### 2. 起動方法

#### オプションA: バッチファイルを使用（最も簡単）
```
Batch_file/run_docker.bat
```

#### オプションB: PowerShellでコマンド実行
```powershell
docker-compose up -d --build
```

### 3. アプリケーションにアクセス
ブラウザで開く: **http://localhost:8501**

### 4. 停止方法
```
Batch_file/stop_docker.bat
```
または
```powershell
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
- Docker Desktopが起動しているか確認
- WSL2が有効になっているか確認

詳細は `README_DOCKER.md` を参照してください。













