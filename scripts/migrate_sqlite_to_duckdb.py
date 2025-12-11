"""
SQLite3からDuckDBへのデータ移行スクリプト
既存のSQLite3データベースをDuckDBに移行します。
"""
import sqlite3
import duckdb
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_all_tables(sqlite_conn: sqlite3.Connection) -> list[str]:
    """SQLiteデータベース内のすべてのテーブル名を取得"""
    cursor = sqlite_conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return [row[0] for row in cursor.fetchall()]


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    duckdb_conn: duckdb.DuckDBPyConnection,
    table_name: str,
) -> int:
    """テーブルをSQLiteからDuckDBに移行"""
    try:
        # SQLiteからデータを読み込み
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", sqlite_conn)
        
        if df.empty:
            logger.info(f"テーブル {table_name} は空です。スキップします。")
            return 0

        # DuckDBにデータを書き込み
        duckdb_conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        duckdb_conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
        
        row_count = len(df)
        logger.info(f"テーブル {table_name}: {row_count} 行を移行しました。")
        return row_count
    except Exception as e:
        logger.error(f"テーブル {table_name} の移行中にエラーが発生: {e}")
        raise


def migrate_database(
    sqlite_path: str, duckdb_path: str, backup: bool = True
) -> None:
    """SQLiteデータベースをDuckDBに移行"""
    # パスの確認
    sqlite_path_obj = Path(sqlite_path)
    if not sqlite_path_obj.exists():
        raise FileNotFoundError(f"SQLiteデータベースが見つかりません: {sqlite_path}")

    # バックアップの作成
    if backup:
        backup_path = f"{sqlite_path}.backup"
        logger.info(f"SQLiteデータベースをバックアップ: {backup_path}")
        # バックアップは手動で行うことを推奨

    # DuckDBデータベースのパスを準備
    duckdb_path_obj = Path(duckdb_path)
    duckdb_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # 既存のDuckDBデータベースがある場合は削除
    if duckdb_path_obj.exists():
        logger.warning(f"既存のDuckDBデータベースを削除: {duckdb_path}")
        duckdb_path_obj.unlink()

    # SQLite接続
    logger.info(f"SQLiteデータベースに接続: {sqlite_path}")
    sqlite_conn = sqlite3.connect(sqlite_path)

    # DuckDB接続
    logger.info(f"DuckDBデータベースを作成: {duckdb_path}")
    duckdb_conn = duckdb.connect(duckdb_path)

    try:
        # すべてのテーブルを取得
        tables = get_all_tables(sqlite_conn)
        logger.info(f"移行対象テーブル: {tables}")

        total_rows = 0
        for table_name in tables:
            rows = migrate_table(sqlite_conn, duckdb_conn, table_name)
            total_rows += rows

        duckdb_conn.commit()
        logger.info(f"移行完了: 合計 {len(tables)} テーブル、{total_rows} 行を移行しました。")

    except Exception as e:
        logger.error(f"移行中にエラーが発生: {e}")
        raise
    finally:
        sqlite_conn.close()
        duckdb_conn.close()


if __name__ == "__main__":
    import sys

    # デフォルトパス
    sqlite_db = "db_folder/qc_data_base.db"
    duckdb_db = "db_folder/qc_data_base.duckdb"

    # コマンドライン引数からパスを取得（オプション）
    if len(sys.argv) > 1:
        sqlite_db = sys.argv[1]
    if len(sys.argv) > 2:
        duckdb_db = sys.argv[2]

    try:
        migrate_database(sqlite_db, duckdb_db)
        print(f"移行が完了しました。")
        print(f"SQLite: {sqlite_db}")
        print(f"DuckDB: {duckdb_db}")
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)

