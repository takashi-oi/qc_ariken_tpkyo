# Arch 管理システム

株式会社 ARCHArch の精度管理システム

## 📋 概要

感染症（病原性腸内細菌）検査（PCR検査）における内部精度管理をWESTGARD multi-Rule手法により実施するWebアプリケーションです。

## 🚀 クイックスタート

### Docker環境（推奨）

```bash
./start_docker.sh
```

または

```bash
docker-compose up --build -d
```

ブラウザで **http://localhost:8501** にアクセス

詳細は [docs/DOCKER_QUICKSTART.md](./docs/DOCKER_QUICKSTART.md) を参照

### Linux環境（ローカル実行）

```bash
```bash
sh run_app.sh
```

ブラウザで **http://localhost:8501** にアクセス

詳細は [docs/バッチ起動手順書.md](./docs/バッチ起動手順書.md) を参照

## 📚 ドキュメント

詳細なドキュメントは [docs/](./docs/) ディレクトリを参照してください。

- [システム仕様書](./docs/システム仕様書.md)
- [データベース設計書](./docs/データベース設計書.md)
- [ページ別関数仕様書](./docs/ページ別関数仕様書.md)
- [Docker クイックスタート](./docs/DOCKER_QUICKSTART.md)
- [起動手順書](./docs/バッチ起動手順書.md)

## 🛠️ 技術スタック

- **フロントエンド**: Streamlit
- **バックエンド**: Python 3.13
- **データベース**: 
  - SQLite3（マスターデータ管理 + 試薬管理）: `db_folder/master_data.db`
  - DuckDB（測定結果データ管理）: `db_folder/qc_data_base.db`
- **精度管理手法**: WESTGARD multi-Rule

## 📦 主要機能

- **管理試料測定結果登録・確認** (pg01)
- **測定状況登録** (pg02)
- **精度管理試料測定結果・対応** (pg03)
- **管理者関係・精度管理実施状況確認** (pg04)
- **精度管理図出力** (pg05)
- **試薬管理システム** (pg06)
  - 発注・納品・使用管理、ロット別トレーサビリティ、在庫管理、有効期限アラート
- **マスターテーブル管理** (pg99)

## 🔧 開発環境セットアップ

### 必要なソフトウェア

- Python 3.13 以上
- Docker（Docker環境を使用する場合）
- その他依存関係（requirements.txt参照）

### セットアップ手順

1. リポジトリのクローン
2. 依存関係のインストール
   ```bash
   pip install -r requirements.txt
   ```
3. データベースディレクトリの作成
   ```bash
   mkdir -p db_folder data/master logs
   ```
84. アプリケーションの起動
   - Docker環境: `./start_docker.sh`
   - ローカル環境: `sh run_app.sh`

詳細は [docs/バッチ起動手順書.md](./docs/バッチ起動手順書.md) を参照

## 📝 ライセンス


