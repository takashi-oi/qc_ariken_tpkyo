@echo off
chcp 65001 > nul
echo ========================================
echo QC管理システム - Docker起動スクリプト
echo ========================================
echo.

REM 現在のディレクトリをプロジェクトルートに移動
cd /d "%~dp0\.."

REM Dockerが実行中か確認
docker --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Dockerがインストールされていないか、起動していません。
    echo Docker Desktopを起動してから再度実行してください。
    pause
    exit /b 1
)

REM Docker Composeが利用可能か確認
docker-compose --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Composeが利用できません。
    pause
    exit /b 1
)

echo Dockerイメージをビルドして起動します...
echo.

REM Windows環境専用の設定で起動（オプション指定可能）
if "%1"=="windows" (
    docker-compose -f docker-compose.windows.yml up -d --build
) else (
    docker-compose up -d --build
)

if errorlevel 1 (
    echo [ERROR] Dockerコンテナの起動に失敗しました。
    pause
    exit /b 1
)

echo.
echo ========================================
echo コンテナが正常に起動しました！
echo ========================================
echo.
echo アプリケーションにアクセス: http://localhost:8501
echo.
echo ログを確認するには: docker-compose logs -f
echo コンテナを停止するには: docker-compose down
echo.

REM ログを表示するか確認（オプション）
set /p show_logs="ログを表示しますか？ (y/n): "
if /i "%show_logs%"=="y" (
    echo.
    echo ログを表示中... (Ctrl+Cで終了)
    docker-compose logs -f
)

pause













