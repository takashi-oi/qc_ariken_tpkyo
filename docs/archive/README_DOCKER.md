# Docker環境セットアップガイド

このドキュメントは、Windows環境でDockerを使用してQC管理システムを実行するための手順です。

## 前提条件

1. **Docker Desktop for Windows** がインストールされていること
2. **WSL2** が有効になっていること（推奨）
3. Windows 10 バージョン 2004以降、またはWindows 11

## セットアップ手順

### 1. Docker Desktopのインストールと設定

1. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop) をダウンロードしてインストール
2. Docker Desktopを起動
3. Settings > General で「Use the WSL 2 based engine」を有効化（推奨）

### 2. プロジェクトの準備

```powershell
# プロジェクトディレクトリに移動
cd C:\path\to\Arch

# データベースフォルダとログフォルダが存在することを確認
# （存在しない場合は自動的に作成されます）
```

### 3. Dockerイメージのビルドと起動

#### 方法1: docker-composeを使用（推奨）

```powershell
# イメージをビルドしてコンテナを起動
docker-compose up -d --build

# ログを確認
docker-compose logs -f

# コンテナを停止
docker-compose down
```

#### 方法2: Windows環境専用設定を使用

```powershell
# Windows環境専用の設定で起動
docker-compose -f docker-compose.windows.yml up -d --build
```

### 4. アプリケーションへのアクセス

ブラウザで以下のURLにアクセス：
```
http://localhost:8501
```

## よくある操作

### コンテナの状態確認

```powershell
# 実行中のコンテナを確認
docker ps

# コンテナのログを確認
docker-compose logs -f arch
```

### コンテナ内でコマンドを実行

```powershell
# コンテナ内のシェルにアクセス
docker exec -it arch bash

# Python環境の確認
docker exec -it arch python --version
```

### データのバックアップ

```powershell
# データベースのバックアップ
docker exec arch cp /app/db_folder/qc_data_base.db /app/db_folder/qc_data_base.db.backup

# または、ホストマシンで直接コピー
# Windowsエクスプローラーで db_folder を開いてコピー
```

### コンテナの再ビルド

```powershell
# コンテナを停止して削除
docker-compose down

# イメージを再ビルドして起動
docker-compose up -d --build
```

## トラブルシューティング

### ポートが既に使用されている場合

`8501`ポートが既に使用されている場合は、`docker-compose.yml`のポート設定を変更してください：

```yaml
ports:
  - "8502:8501"  # ホストの8502ポートをコンテナの8501ポートにマッピング
```

その後、`http://localhost:8502`にアクセスします。

### データベースの権限エラー

WindowsからWSL2へのファイルアクセスで権限の問題が発生する場合：

```powershell
# WSL2内でファイルの権限を確認・修正
wsl
cd /mnt/c/path/to/Arch/db_folder
chmod 666 qc_data_base.db
exit
```

### ボリュームマウントの問題

Windowsのパス形式（`C:\...`）で直接マウントする場合、代わりにWSL2のパス形式（`/mnt/c/...`）を使用するか、相対パスを使用してください。

### ログファイルが見つからない

ログファイルは`./logs`フォルダに出力されます。フォルダが存在しない場合は、コンテナ起動時に自動的に作成されます。

## データの永続化

以下のフォルダはホストマシンにマウントされており、コンテナを削除してもデータは保持されます：

- `./db_folder` - データベースファイル
- `./logs` - ログファイル
- `./data` - マスターデータ（Excelファイル）

## パフォーマンス最適化

Windows環境でのパフォーマンスを向上させるには：

1. **WSL2のメモリ制限を調整**
   - Docker Desktop > Settings > Resources > Advanced
   - メモリを4GB以上に設定（推奨：8GB）

2. **WSL2のファイルシステム最適化**
   - `.wslconfig`ファイルを作成して設定を調整

## 開発時のホットリロード

`docker-compose.yml`では、ソースコードがボリュームとしてマウントされているため、コードを変更すると自動的にStreamlitが再読み込みします。

ただし、大幅な変更や新しい依存関係の追加には、コンテナの再ビルドが必要です：

```powershell
docker-compose up -d --build
```

## 本番環境への展開

本番環境では、以下の点を考慮してください：

1. **セキュリティ設定**
   - 適切な認証の追加
   - HTTPSの有効化
   - ファイアウォールの設定

2. **リソース制限**
   - `docker-compose.windows.yml`の`deploy.resources`セクションで調整

3. **バックアップ戦略**
   - データベースの定期的なバックアップ
   - ログローテーションの設定













