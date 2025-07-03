"""_summary_
 mine menu
"""

import sqlite3
import streamlit as st
ｚｚ
# ページの設定
st.set_page_config(
    # ページタイトルの設定Q
    page_title="有研東京検査所 精度管理システム",
    # ページレイアウトの設定
    layout="wide"
)

st.markdown("# 株式会社有研 東京検査所")
st.markdown("## 感染症(病原性腸内細菌)検査（PCR検査）")
st.markdown("#### 病原性腸内細菌検査／ノロウイルス検査")
st.markdown("### 内部精度管理手法 : WESTGARD multi-Rule")

st.markdown("#### メニュー")
# Homeページへのリンクは削除または案内文のみに
st.markdown("🏠 Home")

st.page_link("pages/pg01_qc_check.py",
             label="pg01 :管理試料測定結果登録：確認",
             icon="📈")

st.page_link("pages/pg02_test_status.py",
             label="pg02 : 測定状況登録", icon="✏️")

st.page_link("pages/pg03_qc_act_log.py",
             label="pg03 :精度管理試料測定結果：対応",
             icon="✏️")

st.page_link(
    "pages/pg04_confirmation_of_accuracy_control.py",
    label="pg04 :管理者関係：精度管理実施状況確認",
    icon="🔍"
)

st.page_link(
    "pages/pg05_statical.py",
    label="pg05 : 精度管理図出力:", icon="📈")

# スレッドセーフな接続を作成
if 'conn' not in st.session_state:
    # check_same_threadをTrueに変更
    st.session_state.conn = sqlite3.connect(
        'your_database.db', check_same_thread=True)
