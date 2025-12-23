#!/bin/bash

# 有研東京検査所 精度管理システム - UV環境起動スクリプト

echo "=== 有研東京検査所 精度管理システム ==="
echo "UV環境での起動を開始します..."

# プロジェクトディレクトリに移動
cd "$(dirname "$0")"

# UV環境が存在するかチェック
if [ ! -d ".venv" ]; then
    echo "エラー: UV環境が見つかりません。"
    echo "以下のコマンドでUV環境を初期化してください："
    echo "  ./init_uv_env.sh"
    exit 1
fi

# 仮想環境をアクティベート
echo "仮想環境をアクティベート中..."
source .venv/bin/activate

# Pythonバージョンの確認
echo "Pythonバージョン: $(python --version)"

# 依存関係の確認
echo "依存関係を確認中..."
if ! python -c "import streamlit" 2>/dev/null; then
    echo "依存関係がインストールされていません。インストール中..."
    uv pip install -r requirements.txt
fi

# duckdbの確認
if ! python -c "import duckdb" 2>/dev/null; then
    echo "duckdbがインストールされていません。インストール中..."
    uv pip install duckdb duckdb-engine
fi

# Streamlitアプリケーションを起動
echo "Streamlitアプリケーションを起動中..."
echo "ブラウザで http://localhost:8501 にアクセスしてください"
echo ""
echo "アプリケーションを停止するには Ctrl+C を押してください"
echo ""

streamlit run Arch.py


