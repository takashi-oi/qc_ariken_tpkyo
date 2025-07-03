@echo off
REM 仮想環境の有効化
call venv\Scripts\activate.bat

REM Streamlitアプリの起動
streamlit run qc_ariken_tokyo.py

pause 