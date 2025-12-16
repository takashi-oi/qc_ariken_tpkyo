@echo off
chcp 65001 > nul
echo ========================================
echo QC管理システム - Docker停止スクリプト
echo ========================================
echo.

REM 現在のディレクトリをプロジェクトルートに移動
cd /d "%~dp0\.."

REM Docker Composeでコンテナを停止
docker-compose down

if errorlevel 1 (
    echo [ERROR] コンテナの停止に失敗しました。
    pause
    exit /b 1
)

echo.
echo ========================================
echo コンテナが正常に停止しました。
echo ========================================
echo.
pause













