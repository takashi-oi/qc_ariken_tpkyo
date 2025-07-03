@echo off
REM 仮想環境の作成
python -m venv venv

REM 仮想環境の有効化
call venv\Scripts\activate.bat

REM 必要パッケージのインストール
pip install --upgrade pip
pip install -r requirements.txt

echo 初期設定が完了しました。
pause
d