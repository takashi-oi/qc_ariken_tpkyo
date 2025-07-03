"""品質チェック"""

# 標準ライブラリ
import asyncio
from typing import NamedTuple, Optional
import sqlite3

# サードパーティライブラリ
import pandas as pd
import streamlit as st
from contextlib import asynccontextmanager

# 自作モジュール
from src.config import Config
from src.database.connection import (
    check_duplicate_records,
    get_db_connection,
    import_to_database
)
from src.utils.file_processing import QCDataApp
from src.models.westgard_rules import MultiRule
from src.models.westgard_rules import check_westgard_rules


class ProcessedData(NamedTuple):
    """処理済みデータを格納する型付きクラス"""
    file_info: pd.DataFrame
    ic_data: pd.DataFrame
    nc_data: pd.DataFrame
    pc_data: pd.DataFrame

    @classmethod
    def from_qc_data(cls, qc_data):
        """QCDataAppの結果からProcessedDataを生成"""
        return cls(
            file_info=qc_data.file_info,
            ic_data=qc_data.ic_data,
            nc_data=qc_data.nc_data,
            pc_data=qc_data.pc_data
        )


class QCCheckApp:
    """品質チェックアプリケーションクラス"""

    def __init__(self):
        st.set_page_config(page_title="QCチェック", layout="wide")
        self.qc_app = QCDataApp()
        self.westgard_checker = MultiRule(type_conditions={
            'IC': [{'Type': 'sd_conversion', 'value': 2.0}],
            'NC': [{'Type': 'sd_conversion', 'value': 3.0}],
            'PC': [{'Type': 'sd_conversion', 'value': 2.5}]
        }, db_connection=None)  # db_connectionは必要に応じて設定

    async def process_data_batch(self, data: ProcessedData) -> dict:
        """データの一括処理を行う"""
        results = {}
        tasks = [
            ('IC', data.ic_data),
            ('NC', data.nc_data),
            ('PC', data.pc_data)
        ]

        for data_type, df in tasks:
            if df is not None and not df.empty:
                results[data_type] = await self.westgard_checker.apply_rules(
                    qc_data=df['Ct'].tolist(),
                    sd_conversions=df['SD_Conversion'].tolist() if 'SD_Conversion' in df.columns else [],
                    types=df['Type'].tolist(),
                    item_codes=df['Item_Code'].tolist(),
                    dyes=df['Dye'].tolist(),
                    batch=df['Batch'].tolist(),
                    model=df['Model'].tolist(),
                    date=df['Date_Time'].tolist()
                )
        
        return results

    async def display_data_summary(self, data: ProcessedData) -> None:
        """データ概要の表示（最適化版）"""
        metrics = {
            "ファイル情報": len(data.file_info) if data.file_info is not None else 0,
            "ICデータ": len(data.ic_data) if data.ic_data is not None else 0,
            "NCデータ": len(data.nc_data) if data.nc_data is not None else 0,
            "PCデータ": len(data.pc_data) if data.pc_data is not None else 0
        }

        st.write("#### データ概要")
        cols = st.columns(4)
        for col, (label, value) in zip(cols, metrics.items()):
            col.metric(label, f"{value}件")

    async def display_detailed_data(self, data: ProcessedData) -> None:
        """詳細データの表示（最適化版）"""
        data_sections = {
            "ファイル情報の詳細": data.file_info,
            "ICデータの詳細": data.ic_data,
            "NCデータの詳細": data.nc_data,
            "PCデータの詳細": data.pc_data
        }

        for title, df in data_sections.items():
            with st.expander(title, expanded=True):
                if df is not None and not df.empty:
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info(f"{title.split('の')[0]}はありません")

    async def perform_westgard_checks(self, data: ProcessedData) -> None:
        """Westgardルールチェックの実行（最適化版）"""
        data_types = {
            "IC": data.ic_data,
            "NC": data.nc_data,
            "PC": data.pc_data
        }

        for data_type, df in data_types.items():
            if df is not None and not df.empty:
                st.write(f"#### {data_type}データのマルチルールチェック結果")
                results = check_westgard_rules(df)
                st.dataframe(results, use_container_width=True)

    @asynccontextmanager
    async def error_handler(self):
        """エラーハンドリング用コンテキストマネージャ"""
        try:
            yield
        except sqlite3.IntegrityError as e:
            st.error(f"データベース整合性エラー: {str(e)}")
        except sqlite3.Error as e:
            st.error(f"データベースエラー: {str(e)}")
        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")

    async def handle_database_operations(self, data: ProcessedData) -> None:
        """データベース操作の処理（最適化版）"""
        st.write("#### データベース操作")

        if not st.button("データベースへの登録／マルチルールチェック開始"):
            return

        if data.file_info is None or data.file_info.empty:
            st.error("処理するデータが存在しません")
            return

        async with self.error_handler():
            async with get_db_connection(Config.DATABASE_PATH) as conn:
                # 重複チェック
                tables = {
                    'table_qc_file_info': data.file_info,
                    'table_qc_ic': data.ic_data,
                    'table_qc_nc': data.nc_data,
                    'table_qc_pc': data.pc_data
                }

                for table_name, df in tables.items():
                    if df is not None and not df.empty:
                        if await check_duplicate_records(conn, table_name, df):
                            st.warning(f"{table_name}に重複するレコードが存在します")
                            return

                # データベース保存とWestgardチェックを並行実行
                await asyncio.gather(
                    import_to_database(conn=conn,
                                       **dataclasses.asdict(data)),
                    self.process_and_display_westgard_results(data)
                )

                st.success("データベースへの保存が完了しました")

    async def run(self) -> None:
        """アプリケーションのメイン実行関数"""
        try:
            qc_data = await self.qc_app.run()
            if qc_data and qc_data.file_info is not None:
                st.write("### データベース取り込み前の確認")
                data = ProcessedData.from_qc_data(qc_data)
                await self.display_data_summary(data)
                await self.display_detailed_data(data)
                await self.handle_database_operations(data)

        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")

    async def process_and_display_westgard_results(self, data: ProcessedData) -> None:
        """Westgardルールチェックの処理と表示"""
        data_types = {
            "IC": data.ic_data,
            "NC": data.nc_data,
            "PC": data.pc_data
        }

        for data_type, df in data_types.items():
            if df is not None and not df.empty:
                st.write(f"#### {data_type}データのマルチルールチェック結果")
                # check_westgard_rulesを非同期関数として扱う
                results = await asyncio.to_thread(check_westgard_rules, df)
                st.dataframe(results, use_container_width=True)


# メイン実行関数
if __name__ == "__main__":
    app = QCCheckApp()
    asyncio.run(app.run())
