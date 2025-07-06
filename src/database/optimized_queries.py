"""最適化されたデータベースクエリクラス"""

import sqlite3
from typing import Any, Dict, List, Optional

import pandas as pd

from src.config import global_logger as logger


class OptimizedQueryManager:
    """最適化されたクエリ管理クラス"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_qc_data_by_date_range(
        self, start_date: str, end_date: str, item_code: Optional[str] = None
    ) -> pd.DataFrame:
        """日付範囲でQCデータを取得（最適化版）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                SELECT
                    qfi.file_name,
                    qfi.date_time,
                    qfi.batch,
                    qfi.item_code,
                    qfi.model,
                    qfi.measurer,
                    qm.measurement_type,
                    qm.dye,
                    qm.ct_value,
                    qm.sd_conversion,
                    qm.verdict,
                    qm.sample_type
                FROM qc_file_info qfi
                JOIN qc_measurements qm ON qfi.id = qm.file_info_id
                WHERE qfi.date_time BETWEEN ? AND ?
                """

                params = [start_date, end_date]

                if item_code:
                    query += " AND qfi.item_code = ?"
                    params.append(item_code)

                query += " ORDER BY qfi.date_time DESC, qm.measurement_type"

                return pd.read_sql_query(query, conn, params=params)

        except sqlite3.Error as e:
            logger.error("QCデータ取得中にエラーが発生: %s", e)
            raise

    def get_westgard_violations(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Westgardルール違反を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                SELECT
                    qfi.file_name,
                    qfi.date_time,
                    qfi.item_code,
                    qfi.batch,
                    qwr.measurement_type,
                    qwr.rule_1_2s,
                    qwr.rule_1_3s,
                    qwr.rule_2_2s,
                    qwr.rule_r_4s,
                    qwr.rule_4_1s,
                    qwr.rule_8x,
                    qwr.total_violations,
                    qwr.evaluation_date
                FROM qc_westgard_results qwr
                JOIN qc_file_info qfi ON qwr.file_info_id = qfi.id
                WHERE qfi.date_time BETWEEN ? AND ?
                AND qwr.total_violations > 0
                ORDER BY qfi.date_time DESC, qwr.total_violations DESC
                """

                return pd.read_sql_query(query, conn, params=[start_date, end_date])

        except sqlite3.Error as e:
            logger.error("Westgard違反データ取得中にエラーが発生: %s", e)
            raise

    def get_activity_log_summary(self, start_date: str, end_date: str) -> pd.DataFrame:
        """活動ログのサマリーを取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                SELECT
                    item_code,
                    batch,
                    model,
                    date_time,
                    measurer,
                    event_type,
                    standard_usage,
                    control_usage,
                    reagents_usage,
                    instrument_usage
                FROM qc_activity_log
                WHERE date_time BETWEEN ? AND ?
                ORDER BY date_time DESC
                """

                return pd.read_sql_query(query, conn, params=[start_date, end_date])

        except sqlite3.Error as e:
            logger.error("活動ログ取得中にエラーが発生: %s", e)
            raise

    def get_measurement_statistics(
        self, item_code: Optional[str] = None, measurement_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """測定データの統計情報を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}

                # 基本統計
                base_query = """
                SELECT
                    COUNT(*) as total_measurements,
                    COUNT(CASE WHEN verdict = 'Pass' THEN 1 END) as pass_count,
                    COUNT(CASE WHEN verdict = 'Fail' THEN 1 END) as fail_count,
                    AVG(ct_value) as avg_ct,
                    AVG(sd_conversion) as avg_sd_conversion,
                    MIN(date_time) as earliest_date,
                    MAX(date_time) as latest_date
                FROM qc_measurements qm
                JOIN qc_file_info qfi ON qm.file_info_id = qfi.id
                WHERE 1=1
                """

                params = []

                if item_code:
                    base_query += " AND qfi.item_code = ?"
                    params.append(item_code)

                if measurement_type:
                    base_query += " AND qm.measurement_type = ?"
                    params.append(measurement_type)

                cursor = conn.cursor()
                cursor.execute(base_query, params)
                result = cursor.fetchone()

                if result:
                    stats.update(
                        {
                            "total_measurements": result[0],
                            "pass_count": result[1],
                            "fail_count": result[2],
                            "avg_ct": result[3],
                            "avg_sd_conversion": result[4],
                            "earliest_date": result[5],
                            "latest_date": result[6],
                        }
                    )

                # 測定タイプ別統計
                type_query = """
                SELECT
                    measurement_type,
                    COUNT(*) as count,
                    AVG(ct_value) as avg_ct,
                    AVG(sd_conversion) as avg_sd_conversion
                FROM qc_measurements qm
                JOIN qc_file_info qfi ON qm.file_info_id = qfi.id
                WHERE 1=1
                """

                if item_code:
                    type_query += " AND qfi.item_code = ?"
                    params = [item_code]
                else:
                    params = []

                type_query += " GROUP BY measurement_type"

                cursor.execute(type_query, params)
                type_stats = cursor.fetchall()

                stats["type_statistics"] = {
                    row[0]: {
                        "count": row[1],
                        "avg_ct": row[2],
                        "avg_sd_conversion": row[3],
                    }
                    for row in type_stats
                }

                return stats

        except sqlite3.Error as e:
            logger.error("統計情報取得中にエラーが発生: %s", e)
            raise

    def get_performance_metrics(self) -> Dict[str, Any]:
        """データベースパフォーマンス指標を取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                metrics = {}

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
                    metrics[f"{table_name}_count"] = count

                # インデックス情報
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='index' AND name LIKE 'idx_%'
                """
                )
                indexes = [row[0] for row in cursor.fetchall()]
                metrics["index_count"] = len(indexes)
                metrics["indexes"] = indexes

                # データベースサイズ
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                metrics["database_size_mb"] = (page_count * page_size) / (1024 * 1024)

                return metrics

        except sqlite3.Error as e:
            logger.error("パフォーマンス指標取得中にエラーが発生: %s", e)
            raise


def create_query_manager(db_path: str) -> OptimizedQueryManager:
    """クエリマネージャーを作成"""
    return OptimizedQueryManager(db_path)
