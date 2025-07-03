"""
表示機能が向上したQCデータ処理モジュール
"""
# 非同期処理のためのライブラリ
import asyncio
# 任意の型を指定するためのライブラリ
from typing import Any
# データ操作のためのライブラリ
import pandas as pd
# Webアプリケーション作成のためのライブラリ
import streamlit as st
# データフレームを扱うためのクラス
from pandas import DataFrame
# データクラスを作成するためのライブラリ
from dataclasses import dataclass


@dataclass
class ProcessedData:
    """処理されたQCデータ結果のコンテナ"""
    file_info: DataFrame  # ファイル情報を格納するデータフレーム
    ic_data: DataFrame  # ICデータを格納するデータフレーム
    nc_data: DataFrame  # NCデータを格納するデータフレーム
    pc_data: DataFrame  # PCデータを格納するデータフレーム

    def is_valid(self) -> bool:
        """必要なデータコンポーネントが存在するか確認"""
        return (
            not self.file_info.empty and  # ファイル情報が空でないこと
            isinstance(self.ic_data, DataFrame) and  # ICデータがデータフレームであること
            isinstance(self.nc_data, DataFrame) and  # NCデータがデータフレームであること
            isinstance(self.pc_data, DataFrame)  # PCデータがデータフレームであること
        )


class QCDataApp:
    """QCデータ処理アプリケーション"""

    def __init__(self):
        """初期化"""
        # データ表示用のインスタンスを作成
        self.display = QCDataDisplay()
        # データ処理用のインスタンスを作成
        self.processor = QCDataProcessor()

    async def run(self):
        """アプリケーションを実行"""
        try:
            # ページ設定
            st.set_page_config(page_title="Quality Check Data Analysis", layout="wide")
            # タイトルを設定
            st.title("Quality Check Data Analysis")

            # サイドバーの設定
            with st.sidebar:
                # 測定者データ（Excel)の読み込み
                employee_data = pd.read_excel(
                    "master_folder/employee_code.xlsx"
                )
                # 測定者を選択
                Measurer = st.selectbox(
                    "測定者名",
                    employee_data["Member's_Name"].tolist()
                )
                # 測定結果File（Excel）のアップロード
                uploaded_file = st.file_uploader(
                    "測定結果Excelファイルをアップロードして下さい",
                    type=['xlsx', 'xls']
                )
            # アップロードされたファイルと測定者名がある場合
            if uploaded_file and Measurer:
                # データ処理と表示を実行する
                await self.processor.process_and_display(
                    uploaded_file,
                    Measurer
                )

        except Exception as e:
            # エラーメッセージを表示
            st.error(f"Application error: {str(e)}")
            # エラーを再発生
            raise RuntimeError(f"Quality Check Data processing failed: {str(e)}") from e


class QCDataDisplay:
    """QCデータ結果の表示機能"""

    @staticmethod
    def display_all_data(processed_data: ProcessedData):
        """処理されたQCデータをセクションごとに表示"""
        # 結果タイトルを表示
        st.write("## Quality Check Data Analysis Results")
        # 無効なデータの場合
        if not processed_data.is_valid():
            # エラーメッセージを表示
            st.error("無効または不完全なデータ")
            # エラーを発生
            raise ValueError("無効または不完全な処理データ")

        # ファイル情報の表示
        st.write("### File Information")  # ファイル情報のタイトルを表示
        st.dataframe(
            processed_data.file_info,  # ファイル情報をデータフレームとして表示
            use_container_width=True,  # コンテナの幅を使用
            hide_index=True  # インデックスを非表示
        )

        # ICデータの表示
        st.write("### Inner Control Data", processed_data.ic_data)

        # NCデータの表示
        st.write("### Negative Control Data", processed_data.nc_data)

        # PCデータの表示
        st.write("### Positive Control Data", processed_data.pc_data)


class QCDataProcessor:
    """QCデータ処理機能"""

    def __init__(self):
        # データ表示用のインスタンスを作成
        self.display = QCDataDisplay()

    async def _get_file_info(self,
                             file: Any,
                             Measurer: str) -> DataFrame:
        """ファイル情報を取得"""
        try:
            file_info = pd.DataFrame({
                'File_Name': [file.name],  # ファイル名
                'Measurer': [Measurer],  # 測定者名
                'Item_Code': [file.name[0]],  # アイテムコード
                'Batch': [file.name[1]],  # バッチ番号
                'Model': [file.name.split('_')[1].split('-')[0]],  # モデル名
                'Date_Time': [pd.Timestamp.now()]  # 現在の日付
            })
            # ファイル情報を返す
            return file_info
        except Exception as e:
            # エラーを発生
            raise ValueError(f"Error creating file info: {str(e)}") from e

    async def process_and_display(self,
                                  file: Any,
                                  Measurer: str):
        """QCデータを処理して結果を表示"""
        try:
            # ファイルまたは測定者名がない場合
            if not file or not Measurer:
                # エラーを発生
                raise ValueError("File and Measurer name are required")

            # アップロードされたファイルを読み込む
            uploaded_df = pd.read_excel(file)
            # データフレームが空の場合
            if uploaded_df.empty:
                # エラーを発生
                raise ValueError("Uploaded file contains no data")

            # ファイル情報を取得
            file_info = await self._get_file_info(file, Measurer)
            # データを処理
            processed_data = await self._process_data(uploaded_df, file_info)
            # 処理されたデータを表示
            self.display.display_all_data(processed_data)

        except Exception as e:
            # エラーを発生
            raise ValueError(f"Error processing file: {str(e)}") from e

    async def _process_data(self,
                            uploaded_df: DataFrame,
                            file_info: DataFrame) -> ProcessedData:
        """アップロードされたデータを個別のコンポーネントに処理"""
        try:
            # データを前処理
            processed_df = self._preprocess_data(uploaded_df, file_info)
            # QCコントロールファイルのパス
            qc_control_path = 'master_folder/qc_control.xlsx'
            # QCコントロールデータを読み込む
            qc_control_df = pd.read_excel(qc_control_path)
            # データをマージ
            processed_df = pd.merge(processed_df, qc_control_df, how='inner')

            # ICデータ、NCデータ、PCデータをそれぞれ抽出
            # ICデータを抽出
            ic_data = processed_df[processed_df['Type'] == 'IC'].copy()
            # NCデータを抽出
            nc_data = processed_df[
                (processed_df['Sample Type'] == 'Negative') &
                (processed_df['Type'] != 'IC')].copy()
            # PCデータを抽出
            pc_data = processed_df[
                (processed_df['Sample Type'] == 'Positive') &
                (processed_df['Type'] != 'IC')].copy()

            # ICデータの判定
            if ic_data.empty:
                # 空のデータフレームを作成
                ic_data = pd.DataFrame(columns=['Sample Type',
                                                'Ct',
                                                'verdict'])
            else:
                # 判定を適用
                ic_data['verdict'] = ic_data['Ct'].apply(
                    lambda x: 'Pass'
                    if pd.to_numeric(x, errors='coerce') >= 10
                    else 'Fail'
                )

            # NCデータの判定
            # NCデータが空の場合
            if nc_data.empty:
                # 空のデータフレームを作成
                nc_data = pd.DataFrame(columns=['Sample Type',
                                                'Ct',
                                                'verdict'])
            else:
                # 判定を適用
                nc_data['verdict'] = nc_data['Ct'].apply(
                    lambda x: 'Pass' if pd.isna(x) or x == '-' else 'Fail'
                )

            # PCデータの変換
            # PCデータが空の場合
            if pc_data.empty:
                # 空のデータフレームを作成
                pc_data = pd.DataFrame(columns=['Sample Type',
                                                'Ct',
                                                'SD_Conversion'])
            else:
                # SD変換を計算
                pc_data['SD_Conversion'] = (
                    pd.to_numeric(pc_data['Ct'], errors='coerce') -
                    pd.to_numeric(pc_data['CL'], errors='coerce')
                ) / pd.to_numeric(pc_data['SD'], errors='coerce')
                # 小数点以下3桁に丸める
                pc_data['SD_Conversion'] = pc_data['SD_Conversion'].round(3)

            # 各データフレームの列を整理
            if not ic_data.empty:
                ic_data = ic_data[['verdict',
                                   'Item_Code',
                                   'Date_Time',
                                   'Batch',
                                   'Model',
                                   'Measurer',
                                   'Dye',
                                   'Type',
                                   'Lot Number',
                                   'Sample Type',
                                   'Ct',
                                   'CL',
                                   'SD']]
                # Ctを数値に変換
                ic_data['Ct'] = pd.to_numeric(ic_data['Ct'], errors='coerce')

            if not nc_data.empty:
                nc_data = nc_data[['verdict',
                                   'Item_Code',
                                   'Date_Time',
                                   'Batch',
                                   'Model',
                                   'Measurer',
                                   'Dye',
                                   'Type',
                                   'Lot Number',
                                   'Sample Type',
                                   'Ct',
                                   'CL',
                                   'SD']]
                # Ctを数値に変換
                nc_data['Ct'] = pd.to_numeric(nc_data['Ct'], errors='coerce')

            if not pc_data.empty:
                pc_data = pc_data[['SD_Conversion',
                                   'Item_Code',
                                   'Date_Time',
                                   'Batch',
                                   'Model',
                                   'Measurer',
                                   'Dye',
                                   'Type',
                                   'Lot Number',
                                   'Sample Type',
                                   'Ct',
                                   'CL',
                                   'SD']]

            return ProcessedData(  # 処理されたデータを返す
                file_info=file_info,
                ic_data=ic_data,
                nc_data=nc_data,
                pc_data=pc_data
            )

        except Exception as e:
            # エラーを発生
            raise ValueError(f"Error processing data: {str(e)}") from e

    def _preprocess_data(self,
                         df: DataFrame,
                         file_info: DataFrame) -> DataFrame:
        """アップロードされたデータを前処理"""
        try:
            processed_df = df.copy()  # データフレームのコピーを作成

            required_columns = {'Sample Type', 'Ct'}  # 必要なカラムを定義
            # かけているカラムを確認
            missing_columns = required_columns - set(processed_df.columns)
            # 欠けているカラムがある場合
            if missing_columns:
                # エラーを発生
                raise ValueError(
                    f"Missing required columns: {missing_columns}"
                    )

            for col in file_info.columns:  # ファイル情報の各カラムについて
                if col not in processed_df.columns:  # カラムが存在しない場合
                    processed_df[col] = file_info[col].iloc[0]  # ファイル情報から値を追加
            # 前処理されたデータを返す
            return processed_df

        except Exception as e:
            # エラーを発生
            raise ValueError(f"Error preprocessing data: {str(e)}") from e


if __name__ == "__main__":
    app = QCDataApp()  # QCデータアプリケーションのインスタンスを作成
    asyncio.run(app.run())  # アプリケーションを実行
