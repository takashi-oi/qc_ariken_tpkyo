"""データベース接続管理"""
import sqlite3
from contextlib import asynccontextmanager
import pandas as pd
from src.config import global_logger as logger
from src.config import Config


@asynccontextmanager
async def get_db_connection(db_path):
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


def get_db_connection_from_config(config: Config) -> sqlite3.Connection:
    """設定ファイルからデータベース接続を取得"""
    return sqlite3.connect(config.DATABASE_PATH)


def import_to_database(file_info: pd.DataFrame,
                       df_ic: pd.DataFrame,
                       df_nc: pd.DataFrame,
                       df_pc: pd.DataFrame) -> None:
    """データベースへのデータインポート処理

    Args:
        file_info: ファイル情報のDataFrame
        df_ic: ICデータのDataFrame
        df_nc: NCデータのDataFrame
        df_pc: PCデータのDataFrame
    """
    try:
        # 設定からデータベースパスを取得
        config = Config()

        # データベース接続
        with get_db_connection(config.DATABASE_PATH) as conn:
            # トランザクション開始
            conn.execute('BEGIN TRANSACTION')

            try:
                # ファイル情報をインポート
                file_info.to_sql('file_info',
                                 conn,
                                 if_exists='append',
                                 index=False)

                # ICデータをインポート
                df_ic.to_sql('ic_data',
                             conn,
                             if_exists='append',
                             index=False)

                # NCデータをインポート
                df_nc.to_sql('nc_data',
                             conn,
                             if_exists='append',
                             index=False)

                # PCデータをインポート
                df_pc.to_sql('pc_data',
                             conn,
                             if_exists='append',
                             index=False)

                # トランザクションをコミット
                conn.commit()

                logger.info("データベースへのインポートが正常に完了しました")
            except Exception as e:
                # エラー発生時はロールバック
                conn.rollback()
                logger.error("データベースインポート中にエラーが発生: %s", e)
                raise

    except Exception as e:
        logger.error("データベース接続またはインポート中にエラーが発生: %s", e)
        raise


def check_duplicate_entry(date: str, batch: str, item_code: str) -> bool:
    """データベース内の重複エントリーをチェックする関数

    Args:
        date: 測定日時
        batch: バッチ番号
        item_code: 品目コード

    Returns:
        bool: 重複がある場合はTrue、ない場合はFalse
    """
    try:
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM table_qc_test_data_file "
                "WHERE file_name = ?",
                (item_code,)
            )
            return cursor.fetchone()[0] > 0
    except sqlite3.Error as e:
        logger.error("重複チェックエラー: %s", e)
        return False


get_database_connection = get_db_connection
