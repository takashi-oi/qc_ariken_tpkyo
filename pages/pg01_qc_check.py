"""
精度管理：マルチルール

データの処理、データベース操作、Westgardルールのチェックを行います。
"""

import asyncio

import streamlit as st

# 新しいモジュール構造からインポート
from src.qc import QCCheckApp

# ページ設定
st.set_page_config(page_title="管理試料測定結果登録・確認", layout="wide")

# タイトルを表示
st.markdown("### 管理試料測定結果登録・確認")


# メイン実行関数
if __name__ == "__main__":
    app = QCCheckApp()
    asyncio.run(app.run())
