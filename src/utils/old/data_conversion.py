"""
PC/NC/ICのcheck & PCのSD conversion
"""

# モジュールのインポート
import logging
import sqlite3
from typing import Tuple

# データ分析モジュール
import pandas as pd
import streamlit as st

# 設定モジュール
from src.config import Config

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_table_data(table_name: str) -> pd.DataFrame:
    """指定されたテーブルからデータを取得する関数"""
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            query = f"SELECT * FROM {table_name}"
            return pd.read_sql_query(query, conn)
    except sqlite3.Error as e:
        logger.error("データベースエラー: %s", e)
        return pd.DataFrame()


def get_all_tables() -> list:
    """データベース内の全テーブル名を取得する関数"""
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type='table';
            """)
            tables = cursor.fetchall()
            return [table[0] for table in tables]
    except sqlite3.Error as e:
        logger.error("データベースエラー: %s", e)
        return []


def process_qc_data(
    df: pd.DataFrame,
    file_info: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """QCデータを処理する関数"""
    try:
        def process_control_data(
            df: pd.DataFrame,
            file_info: pd.DataFrame,
            control_type: str
        ) -> pd.DataFrame:
            """各コントロールタイプのデータを処理する内部関数"""
            control_df = df[df['control_type'] == control_type].copy()
            if not control_df.empty:
                control_df = pd.merge(
                    control_df,
                    file_info,
                    on=['date', 'batch'],
                    how='left'
                )
            return control_df

        df_nc = process_control_data(df, file_info, 'nc')
        df_ic = process_control_data(df, file_info, 'ic')
        df_pc = process_control_data(df, file_info, 'pc')

        # streamlitでデータフレームを表示
        if not df_nc.empty:
            st.write("NCデータ:", df_nc)
        if not df_ic.empty:
            st.write("ICデータ:", df_ic)
        if not df_pc.empty:
            st.write("PCデータ:", df_pc)

        return df_nc, df_ic, df_pc

    except pd.errors.EmptyDataError:
        logger.error("データフレームが空です")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except ValueError as ve:
        logger.error("値エラー: %s", ve)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except KeyError as ke:
        logger.error("キーエラー: %s", ke)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except (TypeError, IndexError) as e:
        logger.error("データ処理中にエラーが発生: %s", e)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def check_duplicate_entry(date: str, batch: str, item_code: str) -> bool:
    """データベースで重複をチェックする関数"""
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT COUNT(*) FROM table_qc_nc
            WHERE date = ? AND batch = ? AND item_code = ?
            """, (date, batch, item_code))
            return cursor.fetchone()[0] > 0
    except sqlite3.Error as e:
        logger.error("重複チェックエラー: %s", e)
        return False
