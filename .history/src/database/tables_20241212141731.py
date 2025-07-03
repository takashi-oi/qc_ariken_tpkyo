"""データベーステーブル作成モジュール"""
import sqlite3
from src.config import global_logger as logger


def create_tables(conn: sqlite3.Connection) -> None:
    """必要なテーブルを作成する関数

    Args:
        conn (sqlite3.Connection): データベース接続オブジェクト
    """
    try:
        cursor = conn.cursor()

        # file_infoテーブル作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            import_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            other_metadata TEXT
        )
        ''')

        # nc_dataテーブル作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS nc_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_info_id INTEGER,
            nc_column1 TEXT,
            nc_column2 TEXT,
            FOREIGN KEY (file_info_id) REFERENCES file_info(id)
        )
        ''')

        # pc_dataテーブル作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pc_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_info_id INTEGER,
            pc_column1 TEXT,
            pc_column2 TEXT,
            FOREIGN KEY (file_info_id) REFERENCES file_info(id)
        )
        ''')

        conn.commit()
        logger.info("テーブルが正常に作成されました")

    except sqlite3.Error as e:
        logger.error("テーブル作成中にエラーが発生: %s", e)
        raise
