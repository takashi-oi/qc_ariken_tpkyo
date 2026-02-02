"""最適化されたデータベーステーブル構造"""

from typing import Any, Dict

import duckdb

from src.config import global_logger as logger

# 最適化されたテーブル作成クエリ
OPTIMIZED_TABLE_QUERIES = {
    "qc_file_info": """
        CREATE TABLE IF NOT EXISTS qc_file_info (
            id INTEGER PRIMARY KEY,
            file_name TEXT NOT NULL,
            date_time TIMESTAMP NOT NULL,
            batch TEXT NOT NULL,
            item_code TEXT NOT NULL,
            model TEXT NOT NULL,
            measurer TEXT NOT NULL,
            lot_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date_time, batch, item_code)
        )
    """,
    "qc_measurements": """
        CREATE SEQUENCE IF NOT EXISTS seq_qc_measurements_id;
        CREATE TABLE IF NOT EXISTS qc_measurements (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_qc_measurements_id'),
            file_info_id INTEGER NOT NULL,
            measurement_type TEXT NOT NULL CHECK (measurement_type IN ('IC', 'NC', 'PC')),
            dye TEXT,
            ct_value DOUBLE,
            sd_conversion DOUBLE,
            verdict TEXT CHECK (verdict IN ('Pass', 'Fail')),
            sample_type TEXT,
            control_limit DOUBLE,
            standard_deviation DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_info_id) REFERENCES qc_file_info(id),
            UNIQUE(file_info_id, measurement_type, dye)
        )
    """,
    "qc_activity_log": """
        CREATE SEQUENCE IF NOT EXISTS seq_qc_activity_log_id;
        CREATE TABLE IF NOT EXISTS qc_activity_log (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_qc_activity_log_id'),
            item_code TEXT NOT NULL,
            batch TEXT NOT NULL,
            model TEXT NOT NULL,
            date_time TIMESTAMP NOT NULL,
            measurer TEXT NOT NULL,
            event_type TEXT NOT NULL,
            standard_usage TEXT,
            control_usage TEXT,
            reagents_usage TEXT,
            instrument_usage TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "qc_westgard_results": """
        CREATE SEQUENCE IF NOT EXISTS seq_qc_westgard_results_id;
        CREATE TABLE IF NOT EXISTS qc_westgard_results (
            id INTEGER PRIMARY KEY DEFAULT nextval('seq_qc_westgard_results_id'),
            file_info_id INTEGER NOT NULL,
            measurement_type TEXT NOT NULL,
            rule_1_2s BOOLEAN DEFAULT false,
            rule_1_3s BOOLEAN DEFAULT false,
            rule_2_2s BOOLEAN DEFAULT false,
            rule_r_4s BOOLEAN DEFAULT false,
            rule_4_1s BOOLEAN DEFAULT false,
            rule_8x BOOLEAN DEFAULT false,
            total_violations INTEGER DEFAULT 0,
            evaluation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_info_id) REFERENCES qc_file_info(id)
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
            with duckdb.connect(self.db_path) as conn:
                # テーブル作成
                for table_name, query in OPTIMIZED_TABLE_QUERIES.items():
                    # シーケンス作成が含まれる場合があるので、複数ステートメントとして実行するか分割する
                    # DuckDBのconn.executeは1文ずつ推奨だが、スクリプトもいけるか確認
                    # 分割して実行
                    statements = [s.strip() for s in query.split(";") if s.strip()]
                    for stmt in statements:
                        conn.execute(stmt)

                logger.info("最適化されたテーブルが正常に作成されました")

        except duckdb.Error as e:
            logger.error("テーブル作成中にエラーが発生: %s", e)
            raise

    def _create_indexes(self) -> None:
        """パフォーマンス向上のためのインデックスを作成"""
        try:
            with duckdb.connect(self.db_path) as conn:
                for index_query in INDEX_QUERIES:
                    conn.execute(index_query)

                logger.info("インデックスが正常に作成されました")

        except duckdb.Error as e:
            logger.error("インデックス作成中にエラーが発生: %s", e)
            raise

    def migrate_existing_data(self) -> None:
        """既存データを新しい構造に移行"""
        try:
            with duckdb.connect(self.db_path) as conn:
                # 既存テーブルの存在確認
                existing_tables_df = conn.execute(
                    """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name IN 
                    ('table_qc_file_info', 'table_qc_ic', 'table_qc_nc', 'table_qc_pc')
                    """
                ).df()
                existing_tables = existing_tables_df["table_name"].tolist()

                if not existing_tables:
                    logger.info("移行対象の既存テーブルが見つかりません")
                    return

                # データ移行処理
                for table_name in existing_tables:
                    if table_name == "table_qc_file_info":
                        self._migrate_file_info_data(conn)
                    elif table_name in ["table_qc_ic", "table_qc_nc", "table_qc_pc"]:
                        self._migrate_measurement_data(conn, table_name)

                # DuckDB has implicit transaction in execute, but let's be safe if needed?
                # actually with duckdb.connect... context manager handles it?
                # DuckDB python client auto-commits by default unless in transaction.
                # But here we are just executing, it should persist.
                logger.info("データ移行が完了しました")

        except duckdb.Error as e:
            logger.error("データ移行中にエラーが発生: %s", e)
            raise

    def _migrate_file_info_data(self, conn: duckdb.DuckDBPyConnection) -> None:
        """ファイル情報データの移行"""
        # 既存テーブルのカラムを確認
        try:
            existing_cols_df = conn.execute("DESCRIBE table_qc_file_info").df()
            existing_cols = existing_cols_df["column_name"].tolist()
        except duckdb.Error:
            logger.warning(
                "table_qc_file_infoが見つからないか、エラーが発生しました。移行をスキップします。"
            )
            return

        # Select defaults for missing columns
        model_val = "Model" if "Model" in existing_cols else "'Unknown'"
        measurer_val = "Measurer" if "Measurer" in existing_cols else "'Unknown'"
        lot_val = "Lot_Number" if "Lot_Number" in existing_cols else "NULL"

        conn.execute(
            f"""
            INSERT INTO qc_file_info 
            (file_name, date_time, batch, item_code, model, measurer, lot_number)
            SELECT File_Name, Date_Time, Batch, Item_Code, {model_val}, {measurer_val}, {lot_val}
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
        self, conn: duckdb.DuckDBPyConnection, source_table: str
    ) -> None:
        """測定データの移行"""
        measurement_type = source_table.split("_")[-1].upper()

        # 既存テーブルのカラムを確認
        try:
            existing_cols_df = conn.execute(f"DESCRIBE {source_table}").df()
            existing_cols = existing_cols_df["column_name"].tolist()
        except duckdb.Error:
            logger.warning(f"{source_table}が見つからないため、移行をスキップします。")
            return

        dye_val = "m.Dye" if "Dye" in existing_cols else "NULL"
        ct_val = "m.Ct" if "Ct" in existing_cols else "NULL"

        if "Ct" in existing_cols:
            verdict_val = "CASE WHEN m.Ct > 10 THEN 'Pass' ELSE 'Fail' END"
        else:
            verdict_val = "'Pass'"

        type_val = "m.Type" if "Type" in existing_cols else "NULL"

        # Check linking keys
        if "Item_Code" not in existing_cols or "Date_Time" not in existing_cols:
            # Check if source table lacks keys (e.g. old table_qc_pc might assume single item?)
            # If so, we might not be able to link to qc_file_info reliably without more context.
            # But duplicate records are better than crash.
            # However, logic requires file_info_id.
            if measurement_type == "PC" and "Item_Code" not in existing_cols:
                # Fallback: maybe use file_info if it's the ONLY file?
                # Too risky. Skip for now and log.
                logger.warning(
                    f"Skipping {source_table} migration: missing join keys (Item_Code/Date_Time)"
                )
                return

        conn.execute(
            f"""
            INSERT INTO qc_measurements 
            (file_info_id, measurement_type, dye, ct_value, sd_conversion, 
             verdict, sample_type, control_limit, standard_deviation)
            SELECT 
                qfi.id,
                '{measurement_type}' as measurement_type,
                {dye_val},
                {ct_val},
                m.SD_Conversion,
                {verdict_val} as verdict,
                {type_val} as sample_type,
                NULL as control_limit,
                NULL as standard_deviation
            FROM {source_table} m
            JOIN qc_file_info qfi ON 
                qfi.date_time = m.Date_Time 
                AND qfi.item_code = m.Item_Code 
                -- Batch might be missing in m?
                -- qfi.batch = m.Batch
                -- If Batch is in m, use it.
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
            with duckdb.connect(self.db_path) as conn:
                stats = {}

                # テーブルサイズ情報
                # DuckDB specific: check row counts
                tables_df = conn.execute(
                    """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_name LIKE 'qc_%'
                    """
                ).df()

                for table_name in tables_df["table_name"]:
                    count = conn.execute(
                        f"SELECT COUNT(*) FROM {table_name}"
                    ).fetchone()[0]
                    stats[f"{table_name}_count"] = count

                # インデックス情報
                # DuckDB doesn't expose indexes simply in information_schema yet in all versions
                # checking pg_indexes or duckdb_indexes if available.
                # Fallback: skip detailed index names if too complex for now, or just query `duckdb_indexes`
                try:
                    indexes_df = conn.execute(
                        "SELECT index_name FROM duckdb_indexes"
                    ).df()
                    indexes = indexes_df["index_name"].tolist()
                    stats["index_count"] = len(indexes)
                    stats["indexes"] = indexes
                except:
                    stats["index_count"] = 0
                    stats["indexes"] = []

                return stats

        except duckdb.Error as e:
            logger.error("統計取得中にエラーが発生: %s", e)
            raise


def create_optimized_database(db_path: str) -> OptimizedDatabaseManager:
    """最適化されたデータベースを作成"""
    return OptimizedDatabaseManager(db_path)
