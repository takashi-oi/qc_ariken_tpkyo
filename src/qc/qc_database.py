"""
QCデータベース操作モジュール
"""

import asyncio
from contextlib import asynccontextmanager

import duckdb
import pandas as pd
import streamlit as st

from src.config import Config
from src.database.connection import DatabaseManager
from src.utils.file_processing import ProcessedData


@st.cache_resource
def get_cached_db_manager(db_path: str):
    """データベースマネージャーのキャッシュインスタンスを取得"""
    manager = DatabaseManager(db_path)
    # テーブル作成をここで行う（初回のみ実行される）
    try:
        asyncio.run(manager.create_tables())
    except Exception as e:
        # すでにイベントループが走っている場合の対策等は必要だが、
        # Streamlitのトップレベルスコープ（キャッシュ関数内）では通常大丈夫
        pass
    return manager


class QCDatabase:
    """QCデータベース操作クラス"""

    def __init__(self):
        self.db_manager = get_cached_db_manager(Config.DATABASE_PATH)

    @asynccontextmanager
    async def error_handler(self):
        """エラーハンドリング用コンテキストマネージャ"""
        try:
            yield
        except duckdb.IntegrityError as e:
            st.error(f"データベース整合性エラー: {str(e)}")
        except duckdb.Error as e:
            st.error(f"データベースエラー: {str(e)}")
        except (ValueError, TypeError) as e:
            st.error(f"値または型に関するエラーが発生しました: {str(e)}")
        except (OSError, IOError) as e:
            st.error(f"入出力エラーが発生しました: {str(e)}")
        except (duckdb.Error, RuntimeError) as e:
            st.error(f"予期しないエラーが発生しました: {str(e)}")

    async def check_for_duplicates(self, data: ProcessedData) -> bool:
        """データベースの重複チェックを行う"""
        if not isinstance(data.file_info, pd.DataFrame) or data.file_info.empty:
            st.error("処理するデータのファイル情報が存在しません")
            return True

        try:
            # 重複チェック用のデータを準備
            duplicate_checks = {
                "table_qc_file_info": {
                    "Date_Time": data.file_info["Date_Time"].iloc[0],
                    "Item_Code": data.file_info["Item_Code"].iloc[0],
                    "Model": data.file_info["Model"].iloc[0],
                    "Measurer": data.file_info["Measurer"].iloc[0],
                    **(
                        {"Lot_Number": data.file_info["Lot_Number"].iloc[0]}
                        if "Lot_Number" in data.file_info.columns
                        else {}
                    ),
                },
                "table_qc_nc": {
                    "Date_Time": data.file_info["Date_Time"].iloc[0],
                },
                "table_qc_pc": {
                    "Date_Time": data.file_info["Date_Time"].iloc[0],
                },
            }

            # 各テーブルの重複チェック
            duplicate_found = False
            for table, check_data in duplicate_checks.items():
                if await self.db_manager.check_duplicate_records(table, check_data):
                    st.warning(f"{table}に重複するレコードが存在します")
                    duplicate_found = True
                    break  # 重複が見つかったらループを抜ける

            return duplicate_found

        except IndexError:
            st.error("ファイル情報データが不完全です")
            return True
        except KeyError as e:
            st.error(f"必要なデータカラムがありません: {e}")
            return True

    async def handle_database_operations(self, data: ProcessedData) -> None:
        """データベース操作の処理（最適化版）"""
        if st.button("データベース登録／マルチルールチェック開始"):
            if not isinstance(data.file_info, pd.DataFrame) or data.file_info.empty:
                st.error("処理するデータが存在しません")
                return

            async with self.error_handler():
                # 重複チェック
                if await self.check_for_duplicates(data):
                    return

                # データベースへの保存
                await self.db_manager.import_qc_data(
                    file_info=data.file_info,
                    ic_data=(
                        data.ic_data
                        if isinstance(data.ic_data, pd.DataFrame)
                        else pd.DataFrame()
                    ),
                    nc_data=(
                        data.nc_data
                        if isinstance(data.nc_data, pd.DataFrame)
                        else pd.DataFrame()
                    ),
                    pc_data=(
                        data.pc_data
                        if isinstance(data.pc_data, pd.DataFrame)
                        else pd.DataFrame()
                    ),
                )
                st.success("データベースへの保存が完了しました")

                # データベース保存後にマルチルールチェックを実行
                st.markdown("### マルチルールチェック結果")
                from .qc_data_processor import QCDataProcessor

                processor = QCDataProcessor()
                await processor.process_and_display_westgard_results(data)
