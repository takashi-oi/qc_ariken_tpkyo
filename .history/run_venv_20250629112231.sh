#!/bin/bash

# 有研東京検査所 精度管理システム - 仮想環境起動スクリプト (Python 3.12.7)

echo "=== 有研東京検査所 精度管理システム ==="
echo "Python 3.12.7 仮想環境での起動を開始します..."

# プロジェクトディレクトリに移動
cd "$(dirname "$0")"

# 仮想環境が存在するかチェック
if [ ! -d "venv" ]; then
    echo "エラー: 仮想環境が見つかりません。"
    echo "以下のコマンドでPython 3.12.7の仮想環境を作成してください："
    echo "python3.12 -m venv venv"
    exit 1
fi

# 仮想環境をアクティベート
echo "仮想環境をアクティベート中..."
source venv/bin/activate

# Pythonバージョンの確認
echo "Pythonバージョン: $(python --version)"

# 依存関係の確認
echo "依存関係を確認中..."
if ! python -c "import streamlit" 2>/dev/null; then
    echo "依存関係がインストールされていません。インストール中..."
    pip install -r requirements.txt
fi

# Streamlitアプリケーションを起動
echo "Streamlitアプリケーションを起動中..."
echo "ブラウザで http://localhost:8501 にアクセスしてください"
echo ""
echo "アプリケーションを停止するには Ctrl+C を押してください"
echo ""

streamlit run qc_ariken_tokyo.py 