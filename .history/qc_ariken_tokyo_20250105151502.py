"""_summary_
 mine menu
"""

import streamlit as st

st.markdown("# 株式会社有研 東京検査所")
st.markdown("## 感染症(病原性腸内細菌)検査（PCR検査）")
st.markdown("#### 病原性腸内細菌検査／ノロウイルス検査")
st.markdown("### 内部精度管理 : WESTGARD Mulch-Rule")
st.markdown("#### メニュー")
st.page_link("qc_ariken_tokyo.py", label= "Home", icon="🏠")
st.markdown("### ⭐️ルチルール設定:測定結果の確認")
st.page_link("##### pg 02 : qc act log:")
st.markdown("### ⭐️精度管理実施状況確認の登録")
st.markdown("##### pg 03 : Confirmation of accuracy control "
            "implementation status:")
st.markdown("### ⭐️QCチェックの実施")
st.markdown("##### pg 04 : pg04_statistical accuracy management report:")
st.markdown("### ⭐️統計学的精度管理図作成")
