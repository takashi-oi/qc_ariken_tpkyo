"""
表示機能が向上したQCデータ処理モジュール
"""
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

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

    @classmethod
    def validate_data(cls, data: 'ProcessedData') -> bool:
        """データの検証"""
        required_columns = {
            'Date_Time', 'Batch', 'Item_Code', 'Ct', 'verdict'
        }
        
        try:
            # 基本的な検証
            if data.file_info.empty:
                return False
                
            # 各データフレームの必須カラムを確認
            for df in [data.ic_data, data.nc_data, data.pc_data]:
                if not df.empty and not required_columns.issubset(df.columns):
                    return False
            
            return True
            
        except Exception as e:
            logger.error("データ検証エラー: %s", e)
            return False

    def get_all_dataframes(self) -> Dict[str, DataFrame]:
        """全てのデータフレームを辞書形式で取得"""
        return {
            'file_info': self.file_info,
            'ic_data': self.ic_data,
            'nc_data': self.nc_data,
            'pc_data': self.pc_data
        }


class QCDataApp:
    """QCデータ処理アプリケーション"""

    def __init__(self):
        self.display = QCDataDisplay()
        self.processor = QCDataProcessor()

    async def run(self) -> Optional[ProcessedData]:
        """アプリケーションを実行"""
        try:
            st.title("Quality Check Data Analysis")

            with st.sidebar:
                employee_data = pd.read_excel(
                    "master_folder/employee_code.xlsx")
                measurer = st.selectbox(
                    "測定者名",
                    employee_data["Member's_Name"].tolist()
                )
                uploaded_file = st.file_uploader(
                    "測定結果Excelファイルをアップロードして下さい",
                    type=['xlsx', 'xls']
                )

            if uploaded_file and measurer:
                processed_data = await self.processor.process_and_display(
                    uploaded_file,
                    measurer
                )
                return processed_data
            return None

        except Exception as e:
            st.error(f"Application error: {str(e)}")
            raise RuntimeError(
                f"Quality Check Data processing failed: {str(e)}") from e


class QCDataDisplay:
    """QCデータ結果の表示機能"""

    @staticmethod
    def display_all_data(processed_data: ProcessedData):
        """処理されたQCデータをセクションごとに表示"""
        st.write("## Quality Check Data Analysis Results")

        if not processed_data.is_valid():
            st.error("無効または不完全なデータ")
            raise ValueError("無効または不完全な処理データ")

        st.write("### File Information")
        st.dataframe(
            processed_data.file_info,
            use_container_width=True,
            hide_index=True
        )

        st.write("### Inner Control Data", processed_data.ic_data)
        st.write("### Negative Control Data", processed_data.nc_data)
        st.write("### Positive Control Data", processed_data.pc_data)


class QCDataProcessor:
    """QCデータ処理機能"""

    def __init__(self):
        self.display = QCDataDisplay()

    async def process_and_display(self, file: Any, measurer: str) -> Optional[ProcessedData]:
        """QCデータを処理して結果を表示"""
        try:
            if not file or not measurer:
                raise ValueError("File and measurer name are required")

            uploaded_df = pd.read_excel(file)
            if uploaded_df.empty:
                raise ValueError("Uploaded file contains no data")

            file_info = await self._get_file_info(file, measurer)
            processed_data = await self._process_data(uploaded_df, file_info)
            
            if processed_data:
                self.display.display_all_data(processed_data)
                return processed_data
            return None

        except Exception as e:
            raise ValueError(f"Error processing file: {str(e)}") from e
