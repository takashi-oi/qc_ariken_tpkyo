"""
表示機能が向上したQCデータ処理モジュール
"""

import asyncio
from dataclasses import dataclass
import pandas as pd
import streamlit as st
from pandas import DataFrame
from typing import Any


@dataclass
class ProcessedData:
    """処理されたQCデータ結果のコンテナ"""
    file_info: DataFrame
    ic_data: DataFrame
    nc_data: DataFrame
    pc_data: DataFrame

    def is_valid(self) -> bool:
        """必要なデータコンポーネントが存在するか確認"""
        return (
            not self.file_info.empty and
            isinstance(self.ic_data, DataFrame) and
            isinstance(self.nc_data, DataFrame) and 
            isinstance(self.pc_data, DataFrame)
        )


class QCDataApp:
    """QCデータ処理アプリケーション"""

    def __init__(self):
        """初期化"""
        self.display = QCDataDisplay()
        self.processor = QCDataProcessor()

    async def run(self):
        """アプリケーションを実行"""
        try:
            st.set_page_config(page_title="QC Data Analysis", layout="wide")
            st.title("QC Data Analysis")
            # サイドバー表示に修正
            with st.sidebar:
                # 測定者名の選択
                employee_data = pd.read_excel(
                    "master_folder/employee_code.xlsx")
                measurer = st.selectbox("測定者名",
                                        employee_data["Member's_Name"].tolist()
                                        )

                # ファイルアップローダーの設定
                uploaded_file = st.file_uploader(
                    "測定結果Excelファイルをアップロードして下さい",
                    type=['xlsx', 'xls']
                    )

            if uploaded_file and measurer:
                await self.processor.process_and_display(uploaded_file,
                                                         measurer)

        except Exception as e:
            st.error(f"Application error: {str(e)}")
            raise RuntimeError(
                f"QC Data processing failed: {str(e)}") from e


class QCDataDisplay:
    """QCデータ結果の表示機能"""

    @staticmethod
    def display_all_data(processed_data: ProcessedData):
        """処理されたQCデータをセクションごとに表示"""
        st.write("## QC Data Analysis Results")

        if not processed_data.is_valid():
            st.error("Invalid or incomplete data")
            raise ValueError("Invalid or incomplete processed data")

        # ファイル情報の表示
        st.write("### File Information")
        st.dataframe(
            processed_data.file_info,
            use_container_width=True,
            hide_index=True
        )

        # ICデータの表示
        st.write("### IC Data")
        QCDataDisplay._display_ic_data(processed_data.ic_data)

        # NCデータの表示
        st.write("### NC Data")
        QCDataDisplay._display_nc_data(processed_data.nc_data)

        # PCデータの表示
        st.write("### PC Data")
        QCDataDisplay._display_pc_data(processed_data.pc_data)

    @staticmethod
    def _display_ic_data(ic_data: DataFrame):
        """ICデータをメトリクスで表示"""
        try:
            st.dataframe(ic_data, use_container_width=True)

            if 'verdict' in ic_data.columns:
                cols = st.columns(3)
                pass_count = (ic_data['verdict'] == 'Pass').sum()
                fail_count = (ic_data['verdict'] == 'Fail').sum()
                total = len(ic_data)

                cols[0].metric("Pass", pass_count)
                cols[1].metric("Fail", fail_count)
                cols[2].metric("Pass Rate",
                               f"{(pass_count / total * 100):.1f}%"
                               if total > 0 else "0%")
        except Exception as e:
            raise ValueError(f"Error displaying IC data: {str(e)}") from e

    @staticmethod
    def _display_nc_data(nc_data: DataFrame):
        """NCデータを分析して表示"""
        try:
            st.dataframe(nc_data, use_container_width=True)

            if 'Ct' in nc_data.columns and not nc_data['Ct'].empty:
                ct_values = pd.to_numeric(
                    nc_data['Ct'].replace(['-', None], pd.NA), errors='coerce')
                if not ct_values.isna().all():
                    cols = st.columns(3)
                    cols[0].metric("Average Ct", f"{ct_values.mean():.2f}")
                    cols[1].metric("Min Ct", f"{ct_values.min():.2f}")
                    cols[2].metric("Max Ct", f"{ct_values.max():.2f}")

        except Exception as e:
            raise ValueError(f"Error displaying NC data: {str(e)}")

    @staticmethod
    def _display_pc_data(pc_data: DataFrame):
        """PCデータを分析して表示"""
        try:
            st.dataframe(pc_data, use_container_width=True)

            if 'Ct' in pc_data.columns and not pc_data['Ct'].empty:
                ct_values = pd.to_numeric(pc_data['Ct'], errors='coerce')
                if not ct_values.isna().all():
                    cols = st.columns(3)
                    cols[0].metric("Average Ct", f"{ct_values.mean():.2f}")
                    cols[1].metric("Min Ct", f"{ct_values.min():.2f}")
                    cols[2].metric("Max Ct", f"{ct_values.max():.2f}")

        except Exception as e:
            raise ValueError(f"Error displaying PC data: {str(e)}")


class QCDataProcessor:
    """QCデータ処理機能"""

    def __init__(self):
        self.display = QCDataDisplay()

    async def _get_file_info(self, file: Any, measurer: str) -> DataFrame:
        """ファイル情報を取得"""
        try:
            file_info = pd.DataFrame({
                'Measurer': [measurer],
                'Filename': [file.name],
                'Upload Time': [pd.Timestamp.now()]
            })
            return file_info
        except Exception as e:
            raise ValueError(f"Error creating file info: {str(e)}")

    async def process_and_display(self, file: Any, measurer: str):
        """QCデータを処理して結果を表示"""
        try:
            if not file or not measurer:
                raise ValueError("File and measurer name are required")

            # ファイルの読み込みと前処理
            uploaded_df = pd.read_excel(file)
            if uploaded_df.empty:
                raise ValueError("Uploaded file contains no data")

            # ファイル情報の取得
            file_info = await self._get_file_info(file, measurer)

            # データの処理
            processed_data = await self._process_data(uploaded_df, file_info)

            # 結果の表示
            self.display.display_all_data(processed_data)

        except Exception as e:
            raise ValueError(f"Error processing file: {str(e)}") from e

    async def _process_data(self,
                            uploaded_df: DataFrame,
                            file_info: DataFrame) -> ProcessedData:
        """アップロードされたデータを個別のコンポーネントに処理"""
        try:
            # データの前処理
            processed_df = self._preprocess_data(uploaded_df, file_info)

            # 各タイプのデータを分離して処理
            ic_data = processed_df[processed_df['Sample Type'] == 'IC'].copy()
            nc_data = processed_df[processed_df['Sample Type'] == 'NC'].copy()
            pc_data = processed_df[processed_df['Sample Type'] == 'PC'].copy()

            # IC データの処理
            if not ic_data.empty:
                ic_data['verdict'] = ic_data['Ct'].apply(
                    lambda x: 'Pass'
                    if pd.to_numeric(x, errors='coerce') >= 10
                    else 'Fail'
                )

            # NC データの処理
            if not nc_data.empty:
                nc_data['verdict'] = nc_data['Ct'].apply(
                    lambda x: 'Pass'
                    if pd.isna(x) or x == '-'
                    else 'Fail'
                )

            # PC データの処理
            if not pc_data.empty:
                pc_data['verdict'] = pc_data['Ct'].apply(
                    lambda x: 'Pass'
                    if pd.to_numeric(x, errors='coerce') > 0
                    else 'Fail'
                )

            return ProcessedData(
                file_info=file_info,
                ic_data=ic_data,
                nc_data=nc_data,
                pc_data=pc_data
            )

        except Exception as e:
            raise ValueError(f"Error processing data: {str(e)}") from e

    def _preprocess_data(self,
                         df: DataFrame,
                         file_info: DataFrame) -> DataFrame:
        """アップロードされたデータを前処理"""
        try:
            processed_df = df.copy()

            # 必須カラムの確認
            required_columns = {'Sample Type', 'Ct'}
            missing_columns = required_columns - set(processed_df.columns)
            if missing_columns:
                raise ValueError(
                    f"Missing required columns: {missing_columns}")

            # タイプマッピングの適用
            type_mapping = {
                'Negative': 'NC',
                'Positive': 'PC',
                'IC': 'IC'
            }

            processed_df['Sample Type'] = \
                processed_df['Sample Type'].map(type_mapping)

            # 無効なサンプルタイプの確認
            invalid_types = set(
                processed_df['Sample Type'].dropna()
                ) - set(type_mapping.values())
            if invalid_types:
                raise ValueError(
                    f"Invalid sample types found: {invalid_types}")

            # ファイル情報の追加
            for col in file_info.columns:
                if col not in processed_df.columns:
                    processed_df[col] = file_info[col].iloc[0]

            return processed_df

        except Exception as e:
            raise ValueError(f"Error preprocessing data: {str(e)}") from e


def main():
    """メインアプリケーションのエントリポイント"""
    st.set_page_config(page_title="QC Data Analysis", layout="wide")
    st.title("QC Data Analysis")

    try:
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

    except Exception as e:
        st.error(f"Application error: {str(e)}")
        raise RuntimeError(f"QC Data processing failed: {str(e)}") from e


if __name__ == "__main__":
    main()
