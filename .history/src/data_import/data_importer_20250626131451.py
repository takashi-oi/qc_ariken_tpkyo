"""
データインポート機能を提供するモジュール
"""

from typing import Any, Optional

import pandas as pd

from src.utils.file_processing import ProcessedData


class DataImporter:
    """データインポートを管理するクラス"""

    def __init__(self):
        """初期化"""
        self.display = None  # 必要に応じてQCDataDisplayを初期化

    async def process_and_display(
        self, file: Any, measurer: str
    ) -> Optional[ProcessedData]:
        """QCデータを処理して結果を表示"""
        try:
            if not file or not measurer:
                raise ValueError("File and measurer name are required")

            # ファイルの読み込み
            uploaded_df = pd.read_excel(file)
            if uploaded_df.empty:
                raise ValueError("Uploaded file contains no data")

            # ファイル情報の取得
            file_info = self._get_file_info(file, measurer)

            # データの処理
            processed_data = self._process_data(uploaded_df, file_info)

            if processed_data:
                # 処理結果の検証
                if (
                    isinstance(processed_data.file_info, pd.DataFrame)
                    and not processed_data.file_info.empty
                ):
                    return processed_data
                else:
                    raise ValueError("Processed data validation failed")
            return None

        except Exception as e:
            import streamlit as st

            st.error(f"ファイル処理エラー: {str(e)}")
            st.info(f"ファイル名: {file.name if hasattr(file, 'name') else 'Unknown'}")
            st.info(f"測定者: {measurer}")
            raise ValueError(f"Error processing file: {str(e)}") from e

    def _get_file_info(self, file: Any, measurer: str) -> pd.DataFrame:
        """ファイル情報を取得"""
        try:
            base_name = file.name.rsplit(".", 1)[0]
            name_parts = base_name.split("-")
            if len(name_parts) < 2:
                raise ValueError("Invalid file name format: missing date")

            code_batch = name_parts[0].split("_")
            if len(code_batch) < 2:
                raise ValueError("Invalid file name format: missing code or batch")

            return pd.DataFrame(
                {
                    "File_Name": [file.name],
                    "Measurer": [measurer],
                    "Item_Code": [code_batch[0][0]],
                    "Batch": [code_batch[0][1]],
                    "Model": [file.name.split("_")[1].split("-")[0]],
                    "Date_Time": [
                        pd.to_datetime(name_parts[1]).strftime("%Y/%m/%d %H:%M:%S")
                    ],
                }
            )
        except (IndexError, ValueError) as e:
            raise ValueError(f"Invalid file name format: {file.name}") from e

    def _process_data(
        self, uploaded_df: pd.DataFrame, file_info: pd.DataFrame
    ) -> ProcessedData:
        """アップロードされたデータを処理"""
        try:
            import streamlit as st
            
            # デバッグ情報の表示
            st.info(f"📊 アップロードされたデータ: {len(uploaded_df)}行")
            st.info(f"📋 ファイル情報: {file_info['Item_Code'].iloc[0]}")
            
            # QC制御データの読み込み
            qc_control_df = pd.read_excel('data/master/qc_control.xlsx')
            st.info(f"📋 QC制御データ: {len(qc_control_df)}行")
            
            # データの結合
            processed_df = pd.merge(
                uploaded_df,
                qc_control_df[
                    qc_control_df['Item_Code'] ==
                    file_info['Item_Code'].iloc[0]
                ],
                how='left'
            )
            st.info(f"📊 結合後のデータ: {len(processed_df)}行")

            # file_infoの情報を各行に追加
            for col in file_info.columns:
                processed_df[col] = file_info[col].iloc[0]
            # File_Nameがなければ追加
            if 'File_Name' not in processed_df.columns:
                processed_df['File_Name'] = file_info['File_Name'].iloc[0]

            # IC データの処理
            ic_df = processed_df[processed_df['Type'] == 'IC'].copy()
            ic_df['Verdict'] = ic_df['Ct'].apply(
                lambda x: 'Pass' if x > 10 else 'Fail'
            )
            ic_df = ic_df[[
                'File_Name', 'Verdict', 'Item_Code', 'Date_Time', 'Batch',
                'Model', 'Measurer', 'Dye', 'Type', 'Lot_Number',
                'Sample Type', 'Ct', 'CL', 'SD'
            ]]

            # NC データの処理
            nc_df = processed_df[
                (processed_df['Sample Type'] == 'Negative') &
                (processed_df['Type'] != 'IC')
            ].copy()
            if not nc_df.empty:
                nc_df['Verdict'] = nc_df['Ct'].apply(
                    lambda x: 'Pass' if pd.isna(x) or x == '-' else 'Fail'
                )
                nc_df = nc_df[[
                    'File_Name', 'Verdict', 'Item_Code', 'Date_Time', 'Batch',
                    'Model', 'Measurer', 'Dye', 'Type', 'Lot_Number',
                    'Sample Type', 'Ct', 'CL', 'SD'
                ]]
            st.info(f"📊 NCデータ: {len(nc_df)}行")

            # PC データの処理
            pc_df = processed_df[
                (processed_df['Sample Type'] == 'Positive') &
                (processed_df['Type'] != 'IC')
            ].copy()
            if not pc_df.empty:
                pc_df['SD_Conversion'] = (pc_df['Ct'] - pc_df['CL']) / pc_df['SD']
                pc_df = pc_df[[
                    'File_Name', 'SD_Conversion', 'Item_Code', 'Date_Time',
                    'Batch', 'Model', 'Measurer', 'Dye', 'Type', 'Lot_Number',
                    'Sample Type', 'Ct', 'CL', 'SD'
                ]]
            st.info(f"📊 PCデータ: {len(pc_df)}行")

            result = ProcessedData(
                file_info=file_info,
                ic_data=ic_df,
                nc_data=nc_df,
                pc_data=pc_df
            )
            
            st.success("✅ データ処理が完了しました")
            return result

        except Exception as e:
            import streamlit as st
            st.error(f"データ処理エラー: {str(e)}")
            st.info("処理されたデータの詳細:")
            st.write(f"アップロードデータ列: {list(uploaded_df.columns)}")
            st.write(f"ファイル情報列: {list(file_info.columns)}")
            raise ValueError(f"データ処理エラー: {str(e)}") from e
