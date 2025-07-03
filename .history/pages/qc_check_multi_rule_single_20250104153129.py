"""QCチェック用のマルチルールチェックページ"""

import sqlite3
from src.Models import westgard_rules
import streamlit as st
import pandas as pd
# Local imports
# ロギング設定
from src.config import global_logger as logger
# データベース接続
from src.database.connection import import_to_database  # データベース接続
from src.Models.westgard_rules import MultiRule  # マルチルール分析
from src.utils.data_conversion import check_duplicate_entry  # 重複チェック
from src.utils.file_processing import get_file_info  # ファイル情報取得

def main():
    """メイン関数"""
    try:
        # サイドバー入力の処理
        Measurer = st.sidebar.text_input(
            "測定者",
            placeholder="フルネームで登録して下さい"
        )
        if not Measurer:
            st.error("測定者が登録されていません。")
            return 1

        uploaded_files = st.sidebar.file_uploader(
            "検査結果エクセルファイルをアップロードしてください",
            accept_multiple_files=True
        )
        if not uploaded_files:
            st.error("検査結果エクセルファイルがアップロードされていません。")
            return 1

        # 分析開始ボタン
        if st.button("ファイルチェックとマルチルール分析を開始"):
            with st.spinner("分析を実行中..."):
                for file in uploaded_files:
                    try:
                        # ファイル情報の取得と検証
                        file_info = get_file_info(file, Measurer)
                        if file_info.empty:
                            st.error(f"ファイル {file.name} の情報取得に失敗しました。")
                            continue

                        # QCデータの読み込みと処理
                        df_qc_data = pd.read_excel(file)
                        df_qc_data['file_name'] = file.name
                        df_qc_data = pd.merge(
                            df_qc_data,
                            file_info,
                            on=['file_name'],
                            how='right'
                        )

                        # コントロールデータの処理
                        control_data = {
                            'nc': process_control_data(
                                df_qc_data,
                                file_info,
                                'nc'
                            ),
                            'ic': process_control_data(
                                df_qc_data,
                                file_info,
                                'ic'
                            ),
                            'pc': process_control_data(
                                df_qc_data,
                                file_info,
                                'pc'
                            )
                        }
                        # データベース処理
                        # 重複チェック
                        if not check_duplicate_entry(
                            file_info['Date_Tome'].iloc[0],
                            file_info['Batch'].iloc[0],
                            file_info['item_code'].iloc[0]
                        ):
                            # データベースにインポート
                            import_to_database(
                                file_info,
                                control_data['nc'],
                                control_data['ic'],
                                control_data['pc']
                            )
                            st.success(f"ファイル {file.name} のデータを登録しました。")
                        else:
                            st.warning(f"ファイル {file.name} は既に登録されています。")

                        # マータを表示
                        st.write(f"ファイル {file.name} のコントロールデータ")
                        st.write("NCデータ:", control_data['nc'])
                        st.write("ICデータ:", control_data['ic'])
                        st.write("PCデータ:", control_data['pc'])

                        # マルチルール分析の実行
                        westgard_multi_rule = \
                            westgard_rules.WestgardMultiRule({})
                        for type_name, group in df_qc_data.groupby('Type'):
                            results = westgard_multi_rule.apply_rules(
                                group['Ct'].values.tolist(),
                                group['sd_conversion'].values.tolist(),
                                group['Type'].values.tolist(),
                                group['item_code'].values.tolist(),
                                group['Dye'].values.tolist(),
                                group['Batch'].values.tolist(),
                                group['Model'].values.tolist(),
                                group['Date_Tome'].values.tolist()
                            )

                            # 結果の表示
                            st.write(f"Type: {type_name} の分析結果")
                            st.write(results)

                            # グラフの表示
                            if 'sd_conversion' in results.columns:
                                st.line_chart(
                                    results.set_index('Date_Tome')['sd_conversion'],
                                    use_container_width=True
                                )

                    except Exception as e:
                        if isinstance(e, FileNotFoundError):
                            st.error(f"ファイル {file.name} が見つかりません: {str(e)}")
                            logger.error("File not found: %s", e)
                        elif isinstance(e, pd.errors.EmptyDataError):
                            st.error(f"ファイル {file.name} のデータが空です: {str(e)}")
                            logger.error("Data in file is empty: %s", e)
                        else:
                            st.error(f"ファイル {file.name} の処理中にエラーが発生: {str(e)}")
                            logger.error("File processing error: %s", e)
                        continue

                st.success("全ての分析が完了しました。")
                st.balloons()

    except Exception as e:
        if isinstance(e, sqlite3.Error):
            st.error(f"データベースエラーが発生しました: {str(e)}")
            logger.error("Database error: %s", e)
        else:
            st.error(f"予期せぬエラーが発生しました: {str(e)}")
            logger.error("Unexpected error: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    main()
