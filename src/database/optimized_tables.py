"""最適化されたデータベーステーブル構造"""

import sqlite3
from typing import Any, Dict

from src.config import global_logger as logger

# 最適化されたテーブル作成クエリ
OPTIMIZED_TABLE_QUERIES = {
    "qc_file_info": """
        CREATE TABLE IF NOT EXISTS qc_file_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            date_time DATETIME NOT NULL,
            batch TEXT NOT NULL,
            item_code TEXT NOT NULL,
            model TEXT NOT NULL,
            measurer TEXT NOT NULL,
            lot_number TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date_time, batch, item_code)
        )
    """,
    "qc_measurements": """
        CREATE TABLE IF NOT EXISTS qc_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_info_id INTEGER NOT NULL,
            measurement_type TEXT NOT NULL CHECK (measurement_type IN ('IC', 'NC', 'PC')),
            dye TEXT,
            ct_value REAL,
            sd_conversion REAL,
            verdict TEXT CHECK (verdict IN ('Pass', 'Fail')),
            sample_type TEXT,
            control_limit REAL,
            standard_deviation REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_info_id) REFERENCES qc_file_info(id) ON DELETE CASCADE,
            UNIQUE(file_info_id, measurement_type, dye)
        )
    """,
    "qc_activity_log": """
        CREATE TABLE IF NOT EXISTS qc_activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code TEXT NOT NULL,
            batch TEXT NOT NULL,
            model TEXT NOT NULL,
            date_time DATETIME NOT NULL,
            measurer TEXT NOT NULL,
            event_type TEXT NOT NULL,
            standard_usage TEXT,
            control_usage TEXT,
            reagents_usage TEXT,
            instrument_usage TEXT,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "qc_westgard_results": """
        CREATE TABLE IF NOT EXISTS qc_westgard_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_info_id INTEGER NOT NULL,
            measurement_type TEXT NOT NULL,
            rule_1_2s BOOLEAN DEFAULT 0,
            rule_1_3s BOOLEAN DEFAULT 0,
            rule_2_2s BOOLEAN DEFAULT 0,
            rule_r_4s BOOLEAN DEFAULT 0,
            rule_4_1s BOOLEAN DEFAULT 0,
            rule_8x BOOLEAN DEFAULT 0,
            total_violations INTEGER DEFAULT 0,
            evaluation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_info_id) REFERENCES qc_file_info(id) ON DELETE CASCADE
        )
    """,
}

# インデックス作成クエリ
INDEX_QUERIES = [
    # qc_file_info テーブルのインデックス
    "CREATE INDEX IF NOT EXISTS idx_file_info_date_time ON qc_file_info(date_time)",
    "CREATE INDEX IF NOT EXISTS idx_file_info_item_code ON qc_file_info(item_code)",
    "CREATE INDEX IF NOT EXISTS idx_file_info_batch ON qc_file_info(batch)",
    "CREATE INDEX IF NOT EXISTS idx_file_info_measurer ON qc_file_info(measurer)",
    "CREATE INDEX IF NOT EXISTS idx_file_info_date_item ON qc_file_info(date_time, item_code)",
    # qc_measurements テーブルのインデックス
    "CREATE INDEX IF NOT EXISTS idx_measurements_file_info ON qc_measurements(file_info_id)",
    "CREATE INDEX IF NOT EXISTS idx_measurements_type ON qc_measurements(measurement_type)",
    "CREATE INDEX IF NOT EXISTS idx_measurements_verdict ON qc_measurements(verdict)",
    "CREATE INDEX IF NOT EXISTS idx_measurements_ct_value ON qc_measurements(ct_value)",
    "CREATE INDEX IF NOT EXISTS idx_measurements_sd_conversion ON qc_measurements(sd_conversion)",
    # qc_activity_log テーブルのインデックス
    "CREATE INDEX IF NOT EXISTS idx_activity_log_date_time ON qc_activity_log(date_time)",
    "CREATE INDEX IF NOT EXISTS idx_activity_log_item_code ON qc_activity_log(item_code)",
    "CREATE INDEX IF NOT EXISTS idx_activity_log_event_type ON qc_activity_log(event_type)",
    # qc_westgard_results テーブルのインデックス
    "CREATE INDEX IF NOT EXISTS idx_westgard_file_info ON qc_westgard_results(file_info_id)",
    "CREATE INDEX IF NOT EXISTS idx_westgard_type ON qc_westgard_results(measurement_type)",
    "CREATE INDEX IF NOT EXISTS idx_westgard_violations ON qc_westgard_results(total_violations)",
]


class OptimizedDatabaseManager:
    """最適化されたデータベース管理クラス"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._create_optimized_tables()
        self._create_indexes()

    def _create_optimized_tables(self) -> None:
        """最適化されたテーブルを作成"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 外部キー制約を有効化
                cursor.execute("PRAGMA foreign_keys = ON")

                # テーブル作成
                for table_name, query in OPTIMIZED_TABLE_QUERIES.items():
                    cursor.execute(query)

                conn.commit()
                logger.info("最適化されたテーブルが正常に作成されました")

        except sqlite3.Error as e:
            logger.error("テーブル作成中にエラーが発生: %s", e)
            raise

    def _create_indexes(self) -> None:
        """パフォーマンス向上のためのインデックスを作成"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for index_query in INDEX_QUERIES:
                    cursor.execute(index_query)

                conn.commit()
                logger.info("インデックスが正常に作成されました")

        except sqlite3.Error as e:
            logger.error("インデックス作成中にエラーが発生: %s", e)
            raise

    def migrate_existing_data(self) -> None:
        """既存データを新しい構造に移行"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 既存テーブルの存在確認
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN 
                    ('table_qc_file_info', 'table_qc_ic', 'table_qc_nc', 'table_qc_pc')
                """
                )
                existing_tables = [row[0] for row in cursor.fetchall()]

                if not existing_tables:
                    logger.info("移行対象の既存テーブルが見つかりません")
                    return

                # データ移行処理
                for table_name in existing_tables:
                    if table_name == "table_qc_file_info":
                        self._migrate_file_info_data(cursor)
                    elif table_name in ["table_qc_ic", "table_qc_nc", "table_qc_pc"]:
                        self._migrate_measurement_data(cursor, table_name)

                conn.commit()
                logger.info("データ移行が完了しました")

        except sqlite3.Error as e:
            logger.error("データ移行中にエラーが発生: %s", e)
            raise

    def _migrate_file_info_data(self, cursor: sqlite3.Cursor) -> None:
        """ファイル情報データの移行"""
        cursor.execute(
            """
            INSERT INTO qc_file_info 
            (file_name, date_time, batch, item_code, model, measurer, lot_number)
            SELECT File_Name, Date_Time, Batch, Item_Code, Model, Measurer, Lot_Number
            FROM table_qc_file_info
            WHERE NOT EXISTS (
                SELECT 1 FROM qc_file_info 
                WHERE qc_file_info.date_time = table_qc_file_info.Date_Time
                AND qc_file_info.batch = table_qc_file_info.Batch
                AND qc_file_info.item_code = table_qc_file_info.Item_Code
            )
        """
        )

    def _migrate_measurement_data(
        self, cursor: sqlite3.Cursor, source_table: str
    ) -> None:
        """測定データの移行"""
        measurement_type = source_table.split("_")[-1].upper()

        cursor.execute(
            f"""
            INSERT INTO qc_measurements 
            (file_info_id, measurement_type, dye, ct_value, sd_conversion, 
             verdict, sample_type, control_limit, standard_deviation)
            SELECT 
                qfi.id,
                '{measurement_type}' as measurement_type,
                m.Dye,
                m.Ct,
                m.SD_Conversion,
                CASE 
                    WHEN m.Ct > 10 THEN 'Pass'
                    ELSE 'Fail'
                END as verdict,
                m.Type as sample_type,
                NULL as control_limit,
                NULL as standard_deviation
            FROM {source_table} m
            JOIN qc_file_info qfi ON 
                qfi.date_time = m.Date_Time 
                AND qfi.batch = m.Batch 
                AND qfi.item_code = m.Item_Code
            WHERE NOT EXISTS (
                SELECT 1 FROM qc_measurements qm
                WHERE qm.file_info_id = qfi.id 
                AND qm.measurement_type = '{measurement_type}'
            )
        """
        )

    def get_optimization_stats(self) -> Dict[str, Any]:
        """データベース最適化統計を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                stats = {}

                # テーブルサイズ情報
                cursor.execute(
                    """
                    SELECT name, sql FROM sqlite_master 
                    WHERE type='table' AND name LIKE 'qc_%'
                """
                )
                tables = cursor.fetchall()

                for table_name, _ in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    stats[f"{table_name}_count"] = count

                # インデックス情報
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name LIKE 'idx_%'
                """
                )
                indexes = [row[0] for row in cursor.fetchall()]
                stats["index_count"] = len(indexes)
                stats["indexes"] = indexes

                return stats

        except sqlite3.Error as e:
            logger.error("統計取得中にエラーが発生: %s", e)
            raise


def create_optimized_database(db_path: str) -> OptimizedDatabaseManager:
    """最適化されたデータベースを作成"""
    return OptimizedDatabaseManager(db_path)
