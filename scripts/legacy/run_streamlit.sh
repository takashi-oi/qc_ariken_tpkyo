#!/bin/bash

# 株式会社 ARCHArch 精度管理システム - Streamlit起動スクリプト

echo "=== 株式会社 ARCHArch 精度管理システム ==="
echo "Streamlitアプリケーションを起動します..."

# プロジェクトディレクトリに移動
cd "$(dirname "$0")"

# 仮想環境の確認
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "エラー: 仮想環境が見つかりません。"
    echo "以下のコマンドで仮想環境を作成してください："
    echo "  python3.14 -m venv .venv"
    echo "  .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# 依存関係の確認
echo "依存関係を確認中..."
if ! python -c "import duckdb" 2>/dev/null; then
    echo "duckdbがインストールされていません。インストール中..."
    pip install duckdb duckdb-engine
fi

if ! python -c "import pandas" 2>/dev/null; then
    echo "pandasがインストールされていません。インストール中..."
    pip install pandas
fi

# Streamlitアプリケーションを起動
echo "Streamlitアプリケーションを起動中..."
echo "ブラウザで http://localhost:8501 にアクセスしてください"
echo ""
echo "アプリケーションを停止するには Ctrl+C を押してください"
echo ""

python -m streamlit run Arch.py
