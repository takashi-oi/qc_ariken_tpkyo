#!/bin/bash

# Cline設定テストスクリプト
# 有研東京検査所 精度管理システム用

set -e

echo "🧪 Cline設定テストを開始します..."

# 色付き出力の関数
print_success() {
    echo -e "\033[32m✅ $1\033[0m"
}

print_error() {
    echo -e "\033[31m❌ $1\033[0m"
}

print_warning() {
    echo -e "\033[33m⚠️ $1\033[0m"
}

print_info() {
    echo -e "\033[34mℹ️ $1\033[0m"
}

# 1. Ollamaサービスの確認
echo "1. Ollamaサービスの確認..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    print_success "Ollamaサービスが正常に動作しています"
else
    print_error "Ollamaサービスに接続できません"
    print_info "Ollamaを起動してください: ollama serve"
    exit 1
fi

# 2. 利用可能モデルの確認
echo "2. 利用可能モデルの確認..."
models=$(ollama list --format json | jq -r '.[].name' 2>/dev/null || echo "")
if [ -n "$models" ]; then
    print_success "利用可能なモデル:"
    echo "$models" | while read model; do
        echo "  - $model"
    done
else
    print_warning "利用可能なモデルが見つかりません"
    print_info "モデルをダウンロードしてください: ollama pull codellama:7b"
fi

# 3. 設定ファイルの確認
echo "3. 設定ファイルの確認..."
if [ -f ".cline/config.json" ]; then
    print_success ".cline/config.json が存在します"
    
    # JSON構文の確認
    if jq empty .cline/config.json 2>/dev/null; then
        print_success "JSON構文が正しいです"
    else
        print_error "JSON構文にエラーがあります"
    fi
    
    # 設定値の確認
    base_url=$(jq -r '.models.ollama.endpoint // empty' .cline/config.json 2>/dev/null)
    default_model=$(jq -r '.models.ollama.default_model // empty' .cline/config.json 2>/dev/null)
    
    if [ -n "$base_url" ]; then
        print_success "Base URL: $base_url"
    else
        print_warning "Base URLが設定されていません"
    fi
    
    if [ -n "$default_model" ]; then
        print_success "Default Model: $default_model"
    else
        print_warning "Default Modelが設定されていません"
    fi
else
    print_error ".cline/config.json が見つかりません"
fi

if [ -f ".cline/project.json" ]; then
    print_success ".cline/project.json が存在します"
else
    print_warning ".cline/project.json が見つかりません"
fi

# 4. VS Code設定の確認
echo "4. VS Code設定の確認..."
if [ -f ".vscode/settings.json" ]; then
    print_success ".vscode/settings.json が存在します"
    
    # Cline設定の確認
    cline_enabled=$(jq -r '.cline.enabled // empty' .vscode/settings.json 2>/dev/null)
    cline_base_url=$(jq -r '.cline.baseUrl // empty' .vscode/settings.json 2>/dev/null)
    cline_model=$(jq -r '.cline.model // empty' .vscode/settings.json 2>/dev/null)
    
    if [ "$cline_enabled" = "true" ]; then
        print_success "Cline拡張機能が有効です"
    else
        print_warning "Cline拡張機能が無効です"
    fi
    
    if [ -n "$cline_base_url" ]; then
        print_success "VS Code Base URL: $cline_base_url"
    else
        print_warning "VS Code Base URLが設定されていません"
    fi
    
    if [ -n "$cline_model" ]; then
        print_success "VS Code Model: $cline_model"
    else
        print_warning "VS Code Modelが設定されていません"
    fi
else
    print_warning ".vscode/settings.json が見つかりません"
fi

# 5. モデルの動作テスト
echo "5. モデルの動作テスト..."
if [ -n "$default_model" ]; then
    print_info "モデル '$default_model' でテストを実行中..."
    
    # 簡単なテストクエリ
    test_response=$(ollama run "$default_model" "print('Hello, World!')" 2>/dev/null || echo "")
    
    if [ -n "$test_response" ]; then
        print_success "モデル '$default_model' が正常に動作しています"
    else
        print_error "モデル '$default_model' のテストに失敗しました"
    fi
else
    print_warning "テスト用のモデルが設定されていません"
fi

# 6. ネットワーク接続テスト
echo "6. ネットワーク接続テスト..."
if ping -c 1 localhost > /dev/null 2>&1; then
    print_success "localhostへの接続が正常です"
else
    print_error "localhostへの接続に失敗しました"
fi

# 7. ポート確認
echo "7. ポート確認..."
if netstat -an | grep ":11434" > /dev/null 2>&1; then
    print_success "ポート11434が使用されています"
else
    print_warning "ポート11434が使用されていません"
fi

echo ""
echo "📋 テスト結果サマリー:"
echo "=================="

# 設定の推奨事項
echo ""
echo "💡 推奨設定:"
echo "1. Base URL: http://localhost:11434"
echo "2. Default Model: codellama:7b"
echo "3. Temperature: 0.3"
echo "4. Max Tokens: 2048"
echo "5. Timeout: 30000"

echo ""
echo "🔧 設定方法:"
echo "1. VS Code設定: .vscode/settings.json"
echo "2. プロジェクト設定: .cline/project.json"
echo "3. グローバル設定: .cline/config.json"

echo ""
print_info "テストが完了しました。問題がある場合は上記の推奨設定を確認してください。" 