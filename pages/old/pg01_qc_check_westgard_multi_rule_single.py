"""QCチェック用のWestgardマルチルールチェックページ"""

import sys
import os
import pandas as pd
import streamlit as st

# ファイル処理関連
from src.utils.file_processing import get_file_info
# PC/NC/ICのcheck & PCのSD conversion
from src.utils.old.data_conversion import check_duplicate_entry, process_qc_data
# Westgardマルチルール
from src.models.westgard_rules import MultiRule
# データベース接続
from src.database.connection import get_database_connection


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """メイン関数"""

    st.title("感染症（PCR）検査/精度管理")
    st.write("Westgard Multi Rule Check")

    # サイドバー入力の処理
    measurer = st.sidebar.text_input(
        "測定者",
        placeholder="フルネームで登録して下さい"
    )
    if not measurer:
        st.error("測定者が登録されていません。")
        return 1

    uploaded_files = st.sidebar.file_uploader(
        "検査結果エクセルファイルをアップロードしてください",
        accept_multiple_files=True
    )
    if not uploaded_files:
        st.error("検査結果エクセルファイルがアップロードされていません。")
        return 1

    # ファイルの処理
    df_control_data = None
    file_info = pd.DataFrame()

    for file in uploaded_files:
        try:
            # DataFrameを直接読み込む
            df_control_data = pd.read_excel(file)

            # get_file_infoを使用してfile_infoを作成
            file_info = get_file_info(file, measurer)
            if file_info.empty:
                st.error(f"ファイル {file.name} の情報を取得できませんでした。")
                continue

            # ファイル形式の検証
            if not all(col in df_control_data.columns for col in ['NC', 'IC', 'PC']):
                st.error(f"ファイル {file.name} に必要なカラム（NC、IC、PC）が含まれていません。")
                continue

        except Exception as e:
            st.error(f"ファイル {file.name} の処理中にエラーが発生しました: {str(e)}")
            continue

    if df_control_data is None or file_info.empty:
        st.error("有効なデータが見つかりませんでした。")
        return 1

##########################################################
    # End Generation Here

    # データ変換処理
    df_nc, df_ic, df_pc = process_qc_data(df_control_data, file_info)
    # 重複チェック
    has_duplicate = check_duplicate_entry(
        date=file_info['date'].iloc[0],
        batch=file_info['batch'].iloc[0],
        item_code=file_info['item_code'].iloc[0]
    )
    if has_duplicate:
        st.error("このデータは既に登録されています")
        return 1

    # Westgardマルチルールの分析を追加
    type_conditions = {
        "条件名": [
            {"閾値": 1.0, "メッセージ": "警告"},
            {"閾値": 2.0, "メッセージ": "エラー"}
        ]
    }  # 適切な条件を設定
    multi_rule = MultiRule(type_conditions)
    try:
        analysis_result = multi_rule.analyze(df_nc, df_ic, df_pc)
    except AttributeError as e:
        st.error(f"分析中にエラーが発生しました: {e}")
        analysis_result = None
    st.subheader("Westgardマルチルール分析結果")
    if analysis_result is not None:
        st.dataframe(analysis_result)
    else:
        st.error("分析結果が得られませんでした。")

##########################################################


if __name__ == "__main__":
    main()
