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
from src.config import global_logger as logger


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
        try:
            # 基本的な検証
            if data.file_info.empty:
                logger.warning("ファイル情報が空です")
                return False
                
            # 各データフレームの型チェック
            if not all(isinstance(df, DataFrame) for df in [
                data.ic_data,
                data.nc_data,
                data.pc_data
            ]):
                logger.warning("無効なデータフレーム型が検出されました")
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

    def is_valid(self) -> bool:
        """必要なデータコンポーネントが存在するか確認"""
        try:
            # 基本的な検証
            if self.file_info.empty:
                return False
                
            # 各データフレームの型チェック
            if not all(isinstance(df, DataFrame) for df in [
                self.ic_data,
                self.nc_data,
                self.pc_data
            ]):
                return False
            
            return True
            
        except Exception as e:
            print(f"データ検証エラー: {str(e)}")
            return False


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

    async def _get_file_info(self, file: Any, measurer: str) -> DataFrame:
        """ファイル情報を取得"""
        try:
            # ファイル名からファイル拡張子を除去
            base_name = file.name.rsplit('.', 1)[0]
            
            # ファイル名をハイフンで分割して日時部分を取得
            name_parts = base_name.split('-')
            if len(name_parts) < 2:
                raise ValueError("Invalid file name format: missing date")
            
            # 品目コードとバッチ番号を取得
            code_batch = name_parts[0].split('_')
            if len(code_batch) < 2:
                raise ValueError("Invalid file name format: missing code or batch")
            
            return pd.DataFrame({
                'File_Name': [file.name],
                'Measurer': [measurer],
                'Item_Code': [code_batch[0]],  # c1
                'Batch': [code_batch[1]],      # 3
                'Model': ['default_model'],    # デフォルト値を設定
                'Date_Time': [
                    pd.to_datetime(name_parts[1]).strftime('%Y/%m/%d %H:%M:%S')
                ]
            })
        except (IndexError, ValueError) as e:
            raise ValueError(f"Invalid file name format: {file.name}") from e
        except Exception as e:
            raise ValueError(f"Error creating file info: {str(e)}") from e

    async def _process_data(self, uploaded_df: DataFrame, file_info: DataFrame) -> ProcessedData:
        """アップロードされたデータを処理"""
        try:
            processed_df = pd.merge(
                uploaded_df,
                pd.read_excel('master_folder/qc_control.xlsx'),
                how='inner'
            )

            ic_data = processed_df[processed_df['Type'] == 'IC'].copy()
            nc_data = processed_df[
                (processed_df['Sample Type'] == 'Negative') &
                (processed_df['Type'] != 'IC')
            ].copy()
            pc_data = processed_df[
                (processed_df['Sample Type'] == 'Positive') &
                (processed_df['Type'] != 'IC')
            ].copy()

            return ProcessedData(
                file_info=file_info,
                ic_data=ic_data,
                nc_data=nc_data,
                pc_data=pc_data
            )

        except Exception as e:
            raise ValueError(f"Error processing data: {str(e)}") from e
