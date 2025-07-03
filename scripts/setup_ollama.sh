#!/bin/bash

# Ollamaセットアップスクリプト
# 有研東京検査所 精度管理システム用

set -e

echo "🚀 Ollamaセットアップを開始します..."

# macOSの場合のOllamaインストール
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📦 macOS用のOllamaをインストールしています..."
    
    # Homebrewがインストールされているかチェック
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrewがインストールされていません。"
        echo "以下のコマンドでHomebrewをインストールしてください："
        echo "/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    # Ollamaをインストール
    brew install ollama
    
    echo "✅ Ollamaのインストールが完了しました"
else
    echo "❌ このスクリプトは現在macOSのみをサポートしています"
    echo "他のOSの場合は、https://ollama.ai/download から手動でインストールしてください"
    exit 1
fi

# Ollamaサービスを開始
echo "🔄 Ollamaサービスを開始しています..."
ollama serve &

# サービスが起動するまで待機
echo "⏳ Ollamaサービスの起動を待機中..."
sleep 5

# 推奨モデルをダウンロード
echo "📥 推奨モデルをダウンロードしています..."

# コード生成に最適なモデル
echo "📦 CodeLlama 7Bをダウンロード中..."
ollama pull codellama:7b

# 汎用モデル
echo "📦 Llama3.2 7Bをダウンロード中..."
ollama pull llama3.2:7b

# 軽量モデル（高速処理用）
echo "📦 Llama3.2 3Bをダウンロード中..."
ollama pull llama3.2:3b

echo "✅ モデルのダウンロードが完了しました"

# モデルの動作確認
echo "🧪 モデルの動作確認中..."
if ollama run codellama:7b "print('Hello, World!')" &> /dev/null; then
    echo "✅ CodeLlama 7Bの動作確認が完了しました"
else
    echo "⚠️ CodeLlama 7Bの動作確認に失敗しました"
fi

# 設定ファイルの確認
echo "📋 設定ファイルの確認中..."
if [ -f ".cline/config.json" ] && [ -f ".cline/project.json" ]; then
    echo "✅ Cline設定ファイルが存在します"
else
    echo "❌ Cline設定ファイルが見つかりません"
    exit 1
fi

# 環境変数の設定
echo "🔧 環境変数を設定しています..."
echo 'export OLLAMA_HOST="http://localhost:11434"' >> ~/.zshrc
echo 'export OLLAMA_MODEL="codellama:7b"' >> ~/.zshrc

echo "✅ Ollamaセットアップが完了しました！"
echo ""
echo "📝 次のステップ："
echo "1. 新しいターミナルを開くか、以下のコマンドを実行してください："
echo "   source ~/.zshrc"
echo ""
echo "2. Cline拡張機能をVS Codeにインストールしてください"
echo ""
echo "3. 以下のコマンドでOllamaの状態を確認できます："
echo "   ollama list"
echo ""
echo "4. アプリケーションを起動するには："
echo "   python -m streamlit run qc_ariken_tokyo.py"
echo ""
echo "🎉 セットアップ完了！ClineとOllamaを使用してコーディングを開始できます。" 