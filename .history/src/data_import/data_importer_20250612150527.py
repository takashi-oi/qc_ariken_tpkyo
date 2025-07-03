"""
データインポート機能を提供するモジュール
"""

import pandas as pd
from typing import Optional, Any
from src.utils.file_processing import ProcessedData


class DataImporter:
    """データインポートを管理するクラス"""

    def __init__(self):
        """初期化"""
        self.display = None  # 必要に応じてQCDataDisplayを初期化

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
                return processed_data
            return None

        except Exception as e:
            raise ValueError(f"Error processing file: {str(e)}") from e

    def _get_file_info(self, file: Any, measurer: str) -> pd.DataFrame:
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
                      uploaded_df: pd.DataFrame,
                      file_info: pd.DataFrame) -> ProcessedData:
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
            ic_df['Verdict'] = ic_df['Ct'].apply(
                lambda x: 'Pass' if x > 10 else 'Fail'
            )
            # 不要な列を削除
            ic_df = ic_df[[
                'Verdict', 'Item_Code', 'Date_Time', 'Batch', 'Model',
                'Measurer', 'Dye', 'Type', 'Lot_Number', 'Sample Type',
                'Ct', 'CL', 'SD'
            ]]

            # NC データの処理
            nc_df = processed_df[
                (processed_df['Sample Type'] == 'Negative') &
                (processed_df['Type'] != 'IC')
            ].copy()
            nc_df['Verdict'] = nc_df['Ct'].apply(
                lambda x: 'Pass' if pd.isna(x) or x == '-' else 'Fail'
            )
            # 不要な列を削除
            nc_df = nc_df[[
                'Verdict', 'Item_Code', 'Date_Time', 'Batch', 'Model',
                'Measurer', 'Dye', 'Type', 'Lot_Number', 'Sample Type',
                'Ct', 'CL', 'SD'
            ]]

            # PC データの処理
            pc_df = processed_df[
                (processed_df['Sample Type'] == 'Positive') &
                (processed_df['Type'] != 'IC')
            ].copy()
            pc_df['SD_Conversion'] = (pc_df['Ct'] - pc_df['CL']) / pc_df['SD']
            # 不要な列を削除
            pc_df = pc_df[[
                'SD_Conversion', 'Item_Code', 'Date_Time', 'Batch', 'Model',
                'Measurer', 'Dye', 'Type', 'Lot_Number', 'Sample Type',
                'Ct', 'CL', 'SD'
            ]]

            return ProcessedData(
                file_info=file_info,
                ic_data=ic_df,
                nc_data=nc_df,
                pc_data=pc_df
            )

        except Exception as e:
            raise ValueError(f"データ処理エラー: {str(e)}") from e
