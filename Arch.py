"""_summary_
mine menu
"""

import sqlite3

import streamlit as st

# ページの設定
st.set_page_config(
    # ページタイトルの設定Q
    page_title="Arch 管理システム",
    # ページレイアウトの設定
    layout="wide",
)

st.markdown("# 株式会社 Lab.Arch")
st.markdown("## Arch検査システム")
st.markdown("### 内部精度管理手法 : WESTGARD multi-Rule")
st.markdown("#### Luminex")

st.markdown("#### メニュー")
# Homeページへのリンクは削除または案内文のみに
st.markdown("🏠 Home")

st.page_link(
    "pages/pg01_qc_check.py",
    label="管理試料測定結果登録・確認",
    icon="📈"
)

st.page_link(
    "pages/pg02_test_status.py",
    label="測定状況登録",
    icon="✏️"
)

st.page_link(
    "pages/pg03_qc_act_log.py",
    label="精度管理試料測定結果・対応",
    icon="📝"
)

st.page_link(
    "pages/pg04_confirmation_of_accuracy_control.py",
    label="管理者関係・精度管理実施状況確認",
    icon="🔍"
)

st.page_link(
    "pages/pg05_statical.py",
    label="精度管理図出力",
    icon="📊"
)

st.page_link(
    "pages/pg99_master_table.py",
    label="マスターテーブル管理",
    icon="⚙️"
)

# スレッドセーフな接続を作成
if "conn" not in st.session_state:
    # check_same_threadをTrueに変更
    # データベースパスをdb_folderに統一
    import os

    db_path = os.path.join("db_folder", "master_data.db")
    os.makedirs("db_folder", exist_ok=True)
    st.session_state.conn = sqlite3.connect(db_path, check_same_thread=True)
