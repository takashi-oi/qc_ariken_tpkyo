"""
QC表示モジュール
"""

import pandas as pd
import streamlit as st

from src.utils.file_processing import ProcessedData


class QCDisplay:
    """QC表示クラス"""

    async def display_data_summary(self,
                                   data: ProcessedData
                                   ) -> None:
        """データ概要の表示（最適化版）"""
        metrics = {
            "ファイル情報": (
                len(data.file_info)
                if isinstance(data.file_info, pd.DataFrame)
                else 0
            ),
            "ICデータ": (
                len(data.ic_data)
                if isinstance(data.ic_data, pd.DataFrame)
                else 0
            ),
            "NCデータ": (
                len(data.nc_data)
                if isinstance(data.nc_data, pd.DataFrame)
                else 0
            ),
            "PCデータ": (
                len(data.pc_data)
                if isinstance(data.pc_data, pd.DataFrame)
                else 0
            ),
        }

        cols = st.columns(len(metrics))
        for col, (label, value) in zip(cols, metrics.items()):
            with col:
                st.metric(label, f"{value}件")

    async def display_detailed_data(self,
                                    data: ProcessedData
                                    ) -> None:
        """詳細データの表示（最適化版）"""
        data_sections = {
            "ファイル情報": data.file_info,
            "Inner Control Data": data.ic_data,
            "Negative Control Data": data.nc_data,
            "Positive Control Data": data.pc_data,
        }

        for title, df in data_sections.items():
            with st.expander(title, expanded=True):
                if isinstance(df, pd.DataFrame) and not df.empty:
                    if title == "ファイル情報":
                        # カラム順・日本語名・日付フォーマット・インデックス非表示
                        display_columns = [
                            "Measurer",
                            "Item_Code",
                            "Date_Time",
                            "Batch",
                            "Model",
                        ]
                        display_columns = [
                            col for col in display_columns if col in df.columns
                        ]
                        display_df = df[display_columns].copy()

                        # カラム名日本語化
                        rename_dict = {
                            "Measurer": "担当者",
                            "Item_Code": "項目コード",
                            "Date_Time": "実施日時（yy/mm/dd）",
                            "Batch": "バッチ",
                            "Model": "機種",
                        }
                        display_df = display_df.rename(columns=rename_dict)

                        # 日付フォーマット
                        if "実施日時（yy/mm/dd）" in display_df.columns:
                            display_df["実施日時（yy/mm/dd）"] = pd.to_datetime(
                                display_df["実施日時（yy/mm/dd）"]
                            ).dt.strftime("%y/%m/%d")

                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True
                        )
                    elif (
                        title == "Inner Control Data"
                        or title == "Negative Control Data"
                    ):
                        # 指定されたカラム順序で表示
                        display_columns = [
                            "Verdict",
                            "Item_Code",
                            "Date_Time",
                            "Batch",
                            "Model",
                            "Measurer",
                            "Dye",
                            "Type",
                            "Lot_Number",
                            "Sample Type",
                            "Ct",
                            "CL",
                            "SD",
                            "File_Name",
                        ]
                        # 存在するカラムのみ選択
                        available_columns = [
                            col for col in display_columns if col in df.columns
                        ]
                        display_df = df[available_columns].copy()

                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.dataframe(df,
                                     use_container_width=True,
                                     hide_index=True)
                else:
                    st.info(f"{title.split('の', maxsplit=1)[0]}はありません")
