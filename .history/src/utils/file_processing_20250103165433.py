"""
表示機能が向上したQCデータ処理モジュール
"""

import asyncio
import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import streamlit as st
from pandas import DataFrame


@dataclass
class ProcessedData:
    """処理されたQCデータ結果のコンテナ"""
    file_info: DataFrame
    ic_data: DataFrame
    nc_data: DataFrame
    pc_data: DataFrame

    def is_valid(self) -> bool:
        """必要なデータコンポーネントが存在するか確認"""
        return not (
            self.file_info.empty or
            self.ic_data.empty or
            self.nc_data.empty or
            self.pc_data.empty
        )


class QCDataDisplay:
    """QCデータ結果の表示機能を向上"""

    @staticmethod
    def display_all_data(processed_data: ProcessedData):
        """処理されたQCデータをセクションごとに表示"""
        st.write("## QC Data Analysis Results")

        # ファイル情報の表示
        st.write("### File Information")
        if not processed_data.file_info.empty:
            st.dataframe(
                processed_data.file_info,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No file information available")

        # ICデータの表示
        st.write("### IC Data")
        if not processed_data.ic_data.empty:
            QCDataDisplay._display_ic_data(processed_data.ic_data)
        else:
            st.warning("No IC data available")

        # NCデータの表示
        st.write("### NC Data")
        if not processed_data.nc_data.empty:
            QCDataDisplay._display_nc_data(processed_data.nc_data)
        else:
            st.warning("No NC data available")

        # PCデータの表示
        st.write("### PC Data")
        if not processed_data.pc_data.empty:
            QCDataDisplay._display_pc_data(processed_data.pc_data)
        else:
            st.warning("No PC data available")

    @staticmethod
    def _display_ic_data(ic_data: DataFrame):
        """ICデータをメトリクスで表示"""
        # メインデータの表示
        st.dataframe(ic_data, use_container_width=True)

        # メトリクスの表示
        if 'verdict' in ic_data.columns:
            cols = st.columns(2)
            pass_count = (ic_data['verdict'] == 'Pass').sum()
            fail_count = (ic_data['verdict'] == 'Fail').sum()

            cols[0].metric("Pass", pass_count)
            cols[1].metric("Fail", fail_count)

            # 合格率の計算と表示
            total = len(ic_data)
            if total > 0:
                pass_rate = (pass_count / total) * 100
                st.metric("Pass Rate", f"{pass_rate:.1f}%")

    @staticmethod
    def _display_nc_data(nc_data: DataFrame):
        """NCデータを分析して表示"""
        # メインデータの表示
        st.dataframe(nc_data, use_container_width=True)

        # NC特有の統計情報の表示
        if 'Ct' in nc_data.columns:
            cols = st.columns(3)
            cols[0].metric("Average Ct", f"{nc_data['Ct'].mean():.2f}")
            cols[1].metric("Min Ct", f"{nc_data['Ct'].min():.2f}")
            cols[2].metric("Max Ct", f"{nc_data['Ct'].max():.2f}")

    @staticmethod
    def _display_pc_data(pc_data: DataFrame):
        """PCデータを分析して表示"""
        # メインデータの表示
        st.dataframe(pc_data, use_container_width=True)

        # PC特有の統計情報の表示
        if 'Ct' in pc_data.columns:
            cols = st.columns(3)
            cols[0].metric("Average Ct", f"{pc_data['Ct'].mean():.2f}")
            cols[1].metric("Min Ct", f"{pc_data['Ct'].min():.2f}")
            cols[2].metric("Max Ct", f"{pc_data['Ct'].max():.2f}")


class QCDataProcessor:
    """QCデータ処理機能を向上"""

    def __init__(self):
        self.display = QCDataDisplay()

    async def _get_file_info(self, file: 'Any', measurer: 'str') -> DataFrame:
        """ファイル情報を取得"""
        file_info = pd.DataFrame({
            'Measurer': [measurer],
            'Filename': [file.name],
            'Upload Time': [pd.Timestamp.now()]
        })
        return file_info

    async def process_and_display(self, file: 'Any', measurer: 'str'):
        """QCデータを処理して結果を表示"""
        try:
            # ファイルの読み込みと前処理
            uploaded_df = pd.read_excel(file)

            # ファイル情報の取得
            file_info = await self._get_file_info(file, measurer)

            # データの処理
            processed_data = await self._process_data(uploaded_df, file_info)

            # 結果の表示
            self.display.display_all_data(processed_data)

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

    async def _process_data(self,
                            uploaded_df: DataFrame,
                            file_info: DataFrame) -> ProcessedData:
        """アップロードされたデータを個別のコンポーネントに処理"""
        # データの前処理
        processed_df = self._preprocess_data(uploaded_df, file_info)

        # 各タイプのデータを分離して処理
        ic_data = processed_df[processed_df['Sample Type'] == 'IC'].copy()
        nc_data = processed_df[processed_df['Sample Type'] == 'NC'].copy()
        pc_data = processed_df[processed_df['Sample Type'] == 'PC'].copy()

        # IC データの処理
        if not ic_data.empty:
            ic_data['verdict'] = ic_data['Ct'].apply(
                lambda x: 'Pass' if x >= 10 else 'Fail'
            )
        
        # NC データを分離して処理
        if not 

        return ProcessedData(
            file_info=file_info,
            ic_data=ic_data,
            nc_data=nc_data,
            pc_data=pc_data
        )

    def _preprocess_data(self,
                         df: DataFrame,
                         file_info: DataFrame) -> DataFrame:
        """アップロードされたデータを前処理"""
        processed_df = df.copy()

        # タイプマッピングの適用
        type_mapping = {
            'Negative': 'NC',
            'Positive': 'PC',
            'IC': 'IC'
        }

        if 'Sample Type' in processed_df.columns:
            processed_df['Sample Type'] = \
                processed_df['Sample Type'].map(type_mapping)

        # ファイル情報の追加
        for col in file_info.columns:
            if col not in processed_df.columns:
                processed_df[col] = file_info[col].iloc[0]

        return processed_df


def main():
    """メインアプリケーションのエントリポイント"""
    st.title("QC Data Analysis")

    # ファイルアップローダーの設定
    uploaded_file = st.file_uploader(
        "Upload QC Data Excel File",
        type=['xlsx', 'xls']
    )

    # 測定者名の入力
    measurer = st.text_input("Measurer Name")

    if uploaded_file and measurer:
        processor = QCDataProcessor()
        asyncio.run(processor.process_and_display(uploaded_file, measurer))


if __name__ == "__main__":
    main()
