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

            with st.sidebar:
                employee_data = pd.read_excel(
                    "master_folder/employee_code.xlsx")
                Measurer = st.selectbox("測定者名",
                                        employee_data["Member's_Name"].tolist()
                                        )

                uploaded_file = st.file_uploader(
                    "測定結果Excelファイルをアップロードして下さい",
                    type=['xlsx', 'xls']
                    )

            if uploaded_file and Measurer:
                await self.processor.process_and_display(uploaded_file,
                                                         Measurer)

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
            st.error("無効または不完全なデータ")
            raise ValueError("無効または不完全な処理データ")

        # ファイル情報の表示
        st.write("### File Information")
        st.dataframe(
            processed_data.file_info,
            use_container_width=True,
            hide_index=True
        )

        # ICデータの表示
        st.write("### IC Data", processed_data.ic_data)

        # NCデータの表示
        st.write("### Negative Control Data", processed_data.nc_data)

        # PCデータの表示
        st.write("### Positive Control Data", processed_data.pc_data)


class QCDataProcessor:
    """QCデータ処理機能"""

    def __init__(self):
        self.display = QCDataDisplay()

    async def _get_file_info(self, file: Any, Measurer: str) -> DataFrame:
        """ファイル情報を取得"""
        try:
            file_info = pd.DataFrame({
                'Filename': [file.name],
                'Measurer': [Measurer],
                'item_code': [file.name[0]],
                'batch': [file.name[1]],
                'model': [file.name.split('_')[1].split('-')[0]],
                'date': [pd.Timestamp.now()]
            })
            return file_info
        except Exception as e:
            raise ValueError(f"Error creating file info: {str(e)}")

    async def process_and_display(self, file: Any, Measurer: str):
        """QCデータを処理して結果を表示"""
        try:
            if not file or not Measurer:
                raise ValueError("File and Measurer name are required")

            uploaded_df = pd.read_excel(file)
            if uploaded_df.empty:
                raise ValueError("Uploaded file contains no data")

            file_info = await self._get_file_info(file, Measurer)
            processed_data = await self._process_data(uploaded_df, file_info)
            self.display.display_all_data(processed_data)

        except Exception as e:
            raise ValueError(f"Error processing file: {str(e)}") from e

    async def _process_data(self,
                            uploaded_df: DataFrame,
                            file_info: DataFrame) -> ProcessedData:
        """アップロードされたデータを個別のコンポーネントに処理"""
        try:
            processed_df = self._preprocess_data(uploaded_df, file_info)

            qc_control_path = 'master_folder/qc_control.xlsx'
            qc_control_df = pd.read_excel(qc_control_path)
            processed_df = pd.merge(processed_df, qc_control_df,
                                    how='inner')

            ic_data = processed_df[processed_df['Type'] == 'IC'].copy()
            nc_data = processed_df[(processed_df['Sample Type'] == 'Negative'
                                    ) & (processed_df['Type'] != 'IC')].copy()
            pc_data = processed_df[(processed_df['Sample Type'] == 'Positive'
                                    ) & (processed_df['Type'] != 'IC')].copy()

            if ic_data.empty:
                ic_data = pd.DataFrame(
                    columns=['Sample Type', 'Ct', 'verdict'])
            else:
                ic_data['verdict'] = ic_data['Ct'].apply(
                    lambda x: 'Pass'
                    if pd.to_numeric(x, errors='coerce') >= 10
                    else 'Fail'
                )

            if nc_data.empty:
                nc_data = pd.DataFrame(
                    columns=['Sample Type', 'Ct', 'verdict'])
            else:
                nc_data['verdict'] = nc_data['Ct'].apply(
                    lambda x: 'Pass'
                    if pd.isna(x) or x == '-'
                    else 'Fail'
                )

            if pc_data.empty:
                pc_data = pd.DataFrame(
                    columns=['Sample Type', 'Ct', 'sd_conversion'])
            else:
                pc_data['sd_conversion'] = (pd.to_numeric(pc_data['Ct'],
                                                          errors='coerce') -
                                            pd.to_numeric(pc_data['CL'],
                                                          errors='coerce')) / \
                                            pd.to_numeric(pc_data['SD'],
                                                          errors='coerce')
                pc_data['sd_conversion'] = pc_data['sd_conversion'].round(3)

            if not ic_data.empty:
                ic_data = ic_data[['verdict',
                                   'item_code',
                                   'date',
                                   'batch',
                                   'model',
                                   'Measurer',
                                   'Dye',
                                   'Type',
                                   'Lot Number',
                                   'Sample Type',
                                   'Ct',
                                   'CL',
                                   'SD']]
                ic_data['Ct'] = pd.to_numeric(ic_data['Ct'], errors='coerce')

            if not nc_data.empty:
                nc_data = nc_data[['verdict',
                                   'item_code',
                                   'date',
                                   'batch',
                                   'model',
                                   'Measurer',
                                   'Dye',
                                   'Type',
                                   'Lot Number',
                                   'Sample Type',
                                   'Ct',
                                   'CL',
                                   'SD']]
                nc_data['Ct'] = pd.to_numeric(nc_data['Ct'], errors='coerce')

            if not pc_data.empty:
                pc_data = pc_data[['sd_conversion',
                                   'item_code',
                                   'date',
                                   'batch',
                                   'model',
                                   'Measurer',
                                   'Dye',
                                   'Type',
                                   'Lot Number',
                                   'Sample Type',
                                   'Ct',
                                   'CL',
                                   'SD']]

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

            required_columns = {'Sample Type', 'Ct'}
            missing_columns = required_columns - set(processed_df.columns)
            if missing_columns:
                raise ValueError(
                    f"Missing required columns: {missing_columns}")

            for col in file_info.columns:
                if col not in processed_df.columns:
                    processed_df[col] = file_info[col].iloc[0]

            return processed_df

        except Exception as e:
            raise ValueError(f"Error preprocessing data: {str(e)}") from e


if __name__ == "__main__":
    app = QCDataApp()
    asyncio.run(app.run())
