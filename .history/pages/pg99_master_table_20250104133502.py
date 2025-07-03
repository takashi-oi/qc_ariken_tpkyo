"""Streamlitアプリケーションで測定項目とモデルを表示します。"""

import streamlit as st
import pandas as pd

st.markdown("# マスターテーブル")
col1, col2 , col3= st.columns(3)

with col1:
    st.markdown("## 測定項目")
    item = pd.read_excel("master_folder/measurement_item.xlsx")
    edited_item = st.data_editor(item, num_rows="dynamic")
    if st.button("測定項目を保存"):
        edited_item.to_excel("master_folder/measurement_item.xlsx",
                             index=False)

with col2:
    st.markdown("## 測定機器")
    model = pd.read_excel("master_folder/measuring_model.xlsx")
    edited_model = st.data_editor(model, num_rows="dynamic")
    if st.button("測定機器を保存"):
        edited_model.to_excel("master_folder/measuring_model.xlsx",
                              index=False)

with col3:
    st.markdown("## 担当者")
    employee = pd.read_excel("master_folder/employee_code.xlsx")
    edited_item = st.data

control = pd.read_excel("master_folder/qc_control.xlsx")
st.markdown("## QC Control")
edited_control = st.data_editor(control, num_rows="dynamic")
if st.button("QC Controlを保存"):
    edited_control.to_excel("master_folder/qc_control.xlsx",
                            index=False)
