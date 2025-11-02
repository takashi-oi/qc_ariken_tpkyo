#!/bin/bash

# 有研東京検査所 精度管理システム - UV環境初期化スクリプト

echo "=== 有研東京検査所 精度管理システム ==="
echo "UV環境の初期化を開始します..."

# UVがインストールされているかチェック
if ! command -v uv &> /dev/null; then
    echo "エラー: UVがインストールされていません。"
    echo "以下のコマンドでUVをインストールしてください："
    echo "  macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  または: brew install uv"
    exit 1
fi

echo "UVバージョン: $(uv --version)"

# プロジェクトディレクトリに移動
cd "$(dirname "$0")"

# UV環境の作成（.venvフォルダ）
if [ -d ".venv" ]; then
    echo "既存のUV環境が見つかりました。削除して再作成します..."
    rm -rf .venv
fi

echo "UV環境を作成中..."
uv venv --python 3.13

if [ $? -ne 0 ]; then
    echo "エラー: UV環境の作成に失敗しました。"
    exit 1
fi

# 仮想環境をアクティベート
echo "仮想環境をアクティベート中..."
source .venv/bin/activate

# Pythonバージョンの確認
echo "Pythonバージョン: $(python --version)"

# 依存関係のインストール
echo "依存関係をインストール中..."
uv pip install --upgrade pip
uv pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "エラー: 依存関係のインストールに失敗しました。"
    exit 1
fi

echo ""
echo "✅ 初期設定が完了しました！"
echo ""
echo "次のステップ:"
echo "  ./run_uv.sh を実行してアプリケーションを起動してください"
echo ""
