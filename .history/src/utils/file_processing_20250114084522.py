"""表示機能が向上したQCデータ処理モジュール"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

import pandas as pd
import streamlit as st
from pandas import DataFrame
from src.config import global_logger as logger


@dataclass
class ProcessedData:
    """処理されたQCデータ結果のコンテナ"""
    # データフレームの型をpd.DataFrameに変更
    file_info: pd.DataFrame
    ic_data: pd.DataFrame
    nc_data: pd.DataFrame
    pc_data: Optional[pd.DataFrame] = None  # pc_dataをオプションに変更

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
        except (ValueError, TypeError) as e:
            logger.error("データ検証エラー: %s", e)
            return False

    def get_all_dataframes(self) -> Dict[str, DataFrame]:
        """全てのデータフレームを辞書形式で取得"""
        return {
            'file_info': self.file_info,
            'ic_data': self.ic_data if self.ic_data is not None
            else pd.DataFrame(),
            'nc_data': self.nc_data if self.nc_data is not None
            else pd.DataFrame(),
            'pc_data': self.pc_data if self.pc_data is not None
            else pd.DataFrame()
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
        except (ValueError, TypeError) as e:
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
            st.title("Quality Check Data Analysis  Results")

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

    async def process_and_display(self,
                                  file: Any,
                                  measurer: str
                                  ) -> Optional[ProcessedData]:
        """QCデータを処理して結果を表示"""
        try:
            if not file or not measurer:
                raise ValueError("File and measurer name are required")

            uploaded_df = pd.read_excel(file)
            if uploaded_df.empty:
                raise ValueError("Uploaded file contains no data")

            file_info = self._get_file_info(file, measurer)
            processed_data = self._process_data(uploaded_df, file_info)

            if processed_data:
                self.display.display_all_data(processed_data)
                return processed_data
            return None

        except Exception as e:
            raise ValueError(f"Error processing file: {str(e)}") from e

    def _get_file_info(self, file: Any, measurer: str) -> DataFrame:
        """ファイル情報を取得"""
        try:
            base_name = file.name.rsplit('.', 1)[0]
            name_parts = base_name.split('-')
            if len(name_parts) < 2:
                raise ValueError("Invalid file name format: missing date")

            code_batch = name_parts[0].split('_')
            if len(code_batch) < 2:
                raise ValueError(
                    "Invalid file name format: missing code or batch"
                    )

            return pd.DataFrame({
                'File_Name': [file.name],
                'Measurer': [measurer],
                'Item_Code': [code_batch[0][0]],
                'Batch': [code_batch[0][1]],
                'Model': [file.name.split('_')[1].split('-')[0]],
                'Date_Time': [pd.to_datetime(
                    name_parts[1]).strftime('%Y/%m/%d %H:%M:%S')]
            })
        except (IndexError, ValueError) as e:
            raise ValueError(f"Invalid file name format: {file.name}") from e

    def _process_data(self,
                      uploaded_df: DataFrame,
                      file_info: DataFrame) -> ProcessedData:
        """アップロードされたデータを処理"""
        try:
            qc_control_df = pd.read_excel('master_folder/qc_control.xlsx')
            processed_df = pd.merge(
                uploaded_df,
                qc_control_df[
                    qc_control_df['Item_Code'] ==
                    file_info['Item_Code'].iloc[0]
                ],
                how='left'
            )

            # file_infoの情報を各行に追加
            for col in file_info.columns:
                processed_df[col] = file_info[col].iloc[0]

            # IC データの処理
            ic_df = processed_df[processed_df['Type'] == 'IC'].copy()
            ic_df['Verdict'] = ic_df['Ct'].apply(lambda x: 'Pass' if x > 10 else 'Fail')
            ic_df = ic_df[[
                'Verdict', 'Item_Code', 'Date_Time', 'Batch', 'Model',
                'Measurer', 'Dye', 'Type', 'Lot Number', 'Sample Type',
                'Ct', 'CL', 'SD'
            ]]

            # NC データの処理
            nc_

            return ProcessedData(
                file_info=file_info,
                ic_data=ic_df,
                nc_data=processed_df[
                    (processed_df['Sample Type'] == 'Negative') &
                    (processed_df['Type'] != 'IC')
                ].copy(),
                pc_data=processed_df[
                    (processed_df['Sample Type'] == 'Positive') &
                    (processed_df['Type'] != 'IC')
                ].copy()
            )
        except Exception as e:
            raise ValueError(f"データ処理エラー: {str(e)}") from e
