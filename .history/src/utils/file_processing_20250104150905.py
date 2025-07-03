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
        st.write("### IC Data")
        QCDataDisplay._display_ic_data(processed_data.ic_data)

        # NCデータの表示
        st.write("### NC Data")
        QCDataDisplay._display_nc_data(processed_data.nc_data)

        # ositiveデータの表示
        st.write("### Positive Data")
        QCDataDisplay._display_pc_data(processed_data.pc_data)

    @staticmethod
    def _display_ic_data(ic_data: DataFrame):
        """ICデータをメトリクスで表示"""
        try:
            st.dataframe(ic_data, use_container_width=True)

            if not ic_data.empty and 'verdict' in ic_data.columns:
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

            if not nc_data.empty and 'Ct' in nc_data.columns:
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

            if not pc_data.empty and 'Ct' in pc_data.columns:
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
                'Filename': [file.name],
                'measurer': [measurer],
                'item_code': [file.name[0]],  # ファイル名の先頭1文字を取得
                'batch': [file.name[1]],      # ファイル名の2文字目を取得
                # ファイル名から_と-の間の文字を抽出
                'model': [file.name.split('_')[1].split('-')[0]],
                'date': [pd.Timestamp.now()]
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

            st.write("check_processed_df", processed_df)

            # QCコントロールデータの読み込みと結合
            qc_control_path = 'master_folder/qc_control.xlsx'
            qc_control_df = pd.read_excel(qc_control_path)

            st.write("check_qc_control", qc_control_df)
            processed_df = pd.merge(processed_df, qc_control_df,
                                    how='inner')

            st.write("check_processed_df", processed_df)

            # 各タイプのデータを分離して処理
            ic_data = processed_df[processed_df['Type'] ==
                                   'IC'].copy()
            nc_data = processed_df[(processed_df['Sample Type'] == 'Negative'
                                    ) & (processed_df['Type'] != 'IC')].copy()
            pc_data = processed_df[(processed_df['Sample Type'] == 'Positive'
                                    ) & (processed_df['Type'] != 'IC')].copy()

            # 空のDataFrameの場合は空のDataFrameを作成
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

            # IC データのカラム修正
            if not ic_data.empty:
                ic_data = ic_data[['verdict',
                                   'item_code',
                                   'date',
                                   'batch',
                                   'model',
                                   'measurer',
                                   'Dye',
                                   'Type',
                                   'Lot Number',
                                   'Sample Type',
                                   'Ct',
                                   'CL',
                                   'SD']]
                ic_data['Ct'] = pd.to_numeric(ic_data['Ct'], errors='coerce')

            # NC データのカラム修正
            if not nc_data.empty:
                nc_data = nc_data[['verdict',
                                   'item_code',
                                   'date',
                                   'batch',
                                   'model',
                                   'measurer',
                                   'Dye',
                                   'Type',
                                   'Lot Number',
                                   'Sample Type',
                                   'Ct',
                                   'CL',
                                   'SD']]
                nc_data['Ct'] = pd.to_numeric(nc_data['Ct'], errors='coerce')
            
            # PC データのカラム修正
            if not pc_data.empty:
                pc_data = pc_data[['sd_conversion',
                                   'item_code',
                                   'date',
                                   'batch',
                                   'model',
                                   'measurer',
                                   
                                   ]]

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
