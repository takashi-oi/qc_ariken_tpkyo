"""データベース接続管理"""
import asyncio
import sqlite3
from contextlib import asynccontextmanager
from typing import Any, Dict

import pandas as pd

from src.config import global_logger as logger

# テーブル作成のSQL定義
CREATE_TABLE_QUERIES = {
    'table_qc_file_info': """
        CREATE TABLE IF NOT EXISTS table_qc_file_info (
            File_Name TEXT,
            Date_Time TEXT,
            Batch TEXT,
            Item_Code TEXT,
            Model TEXT,
            Measurer TEXT,
            Lot_Number TEXT,
            PRIMARY KEY (Date_Time, Batch, Item_Code)
        )
    """,
    'table_qc_ic': """
        CREATE TABLE IF NOT EXISTS table_qc_ic (
            File_Name TEXT,
            Date_Time TEXT,
            Batch TEXT,
            Item_Code TEXT,
            Model TEXT,
            Measurer TEXT,
            Type TEXT,
            Dye TEXT,
            Ct REAL,
            SD_Conversion REAL,
            Lot_Number TEXT,
            PRIMARY KEY (Date_Time, Batch, Type)
        )
    """,
    'table_qc_nc': """
        CREATE TABLE IF NOT EXISTS table_qc_nc (
            File_Name TEXT,
            Date_Time TEXT,
            Batch TEXT,
            Item_Code TEXT,
            Model TEXT,
            Measurer TEXT,
            Type TEXT,
            Dye TEXT,
            Ct REAL,
            SD_Conversion REAL,
            Lot_Number TEXT,
            PRIMARY KEY (Date_Time, Batch, Type)
        )
    """,
    'table_qc_pc': """
        CREATE TABLE IF NOT EXISTS table_qc_pc (
            File_Name TEXT,
            Date_Time TEXT,
            Batch TEXT,
            Item_Code TEXT,
            Model TEXT,
            Measurer TEXT,
            Type TEXT,
            Dye TEXT,
            Ct REAL,
            SD_Conversion REAL,
            Lot_Number TEXT,
            PRIMARY KEY (Date_Time, Batch, Type)
        )
    """
}


@asynccontextmanager
async def get_db_connection(db_path: str):
    """データベース接続の安全な管理"""
    connection = None
    try:
        connection = sqlite3.connect(db_path)
        yield connection
    except sqlite3.Error as e:
        logger.error("データベース接続エラー: %s", e)
        raise
    finally:
        if connection:
            connection.close()


class DatabaseManager:
    """データベース操作を一元管理するクラス"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        asyncio.run(self.create_tables())  # 初期化時にテーブルを作成

    async def create_tables(self) -> None:
        """必要なテーブルを作成"""
        async with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            for query in CREATE_TABLE_QUERIES.values():
                cursor.execute(query)
            conn.commit()

    async def check_duplicate_records(self,
                                      table_name: str,
                                      conditions: Dict[str, Any]) -> bool:
        """レコードの重複をチェック"""
        async with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            where_clause = " AND ".join(
                [f"{k} = ?" for k in conditions.keys()])
            query = f"""
            SELECT COUNT(*) FROM {table_name}
            WHERE {where_clause}
            """
            cursor.execute(query, list(conditions.values()))
            return cursor.fetchone()[0] > 0

    async def bulk_insert(self,
                          table_name: str,
                          data: pd.DataFrame) -> None:
        """データの一括挿入"""
        if data.empty:
            return

        async with get_db_connection(self.db_path) as conn:
            try:
                data.to_sql(table_name,
                            conn,
                            if_exists='append',
                            index=False,
                            method='multi')
            except Exception as e:
                logger.error("データ挿入エラー: %s", e)
                raise

    async def import_qc_data(self,
                             file_info: pd.DataFrame,
                             ic_data: pd.DataFrame,
                             nc_data: pd.DataFrame,
                             pc_data: pd.DataFrame) -> None:
        """QCデータの一括インポート"""
        data_mapping = {
            'table_qc_file_info': file_info,
            'table_qc_ic': ic_data,
            'table_qc_nc': nc_data,
            'table_qc_pc': pc_data
        }

        async with get_db_connection(self.db_path) as conn:
            try:
                conn.execute('BEGIN TRANSACTION')

                # 重複チェック
                duplicate_check = {
                    'Date_Time': file_info['Date_Time'].iloc[0],
                    'Batch': file_info['Batch'].iloc[0],
                    'Item_Code': file_info['Item_Code'].iloc[0]
                }

                is_duplicate = await self.check_duplicate_records(
                    'table_qc_file_info',
                    duplicate_check
                )

                if is_duplicate:
                    logger.warning("重複するレコードが存在します")
                    return

                # データの一括挿入
                for table_name, data in data_mapping.items():
                    if not data.empty:
                        await self.bulk_insert(table_name, data)

                conn.commit()
                logger.info("データベースへのインポートが完了しました")

            except Exception as e:
                conn.rollback()
                logger.error("インポートエラー: %s", e)
                raise

    async def save_data(self, data_dict: Dict[str, pd.DataFrame]) -> None:
        """データを一括保存する"""
        table_mapping = {
            'file_info': 'table_qc_file_info',
            'ic_data': 'table_qc_ic',
            'nc_data': 'table_qc_nc',
            'pc_data': 'table_qc_pc'
        }

        try:
            for key, df in data_dict.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    await self.bulk_insert(table_mapping[key], df)
            logger.info("データの保存が完了しました")
        except Exception as e:
            logger.error("データ保存エラー: %s", e)
            raise
