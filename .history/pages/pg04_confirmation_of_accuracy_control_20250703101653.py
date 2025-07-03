"""
品質管理（QC）データの精度管理を行うためのモジュール。
データベースからQCデータを取得し、グラフ表示とコメント入力機能を提供します。
"""

import logging
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Dict, Generator, List

import pandas as pd
import streamlit as st

# loggingの重複定義を避けるため、再定義を削除
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseConfig:
    """データベース構成設定"""

    path: str = "db_folder/qc_data_base.db"
    max_attempts: int = 3


class DatabaseManager:
    """データベース管理クラス"""

    def __init__(self, config: DatabaseConfig = DatabaseConfig()):
        self.config = config
        self._connection_pool: List[sqlite3.Connection] = []
        self.ensure_database_path()
        self.create_tables()  # テーブル作成メソッドを呼び出す
        self.add_type_column_if_not_exists()  # Typeカラム追加メソッドを呼び出す
        self.add_date_column_if_not_exists()  # dateカラム追加メソッドを呼び出す

    def ensure_database_path(self) -> None:
        """データベースファイルのディレクトリが存在することを確認し、存在しない場合は作成する"""
        db_dir = os.path.dirname(self.config.path)
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir)
                st.info(f"ディレクトリ '{db_dir}' を作成しました。")
            except OSError as e:
                st.error(f"ディレクトリ '{db_dir}' の作成に失敗しました: {str(e)}")
                st.error(f"データベースディレクトリの作成に失敗しました: {e}")
                raise

    def create_tables(self) -> None:
        """必要なテーブルを作成する"""
        create_table_qc_pc = """
        CREATE TABLE IF NOT EXISTS table_qc_pc (
            Date_Time TEXT,
            Type TEXT,
            SD_Conversion REAL
            -- 必要な他のカラムをここに追加
        )
        """

        # 修正後の table_qc_status_log の作成ステートメント
        create_table_qc_status_log = """
        CREATE TABLE IF NOT EXISTS table_qc_status_log (
            Date_Time TEXT,
            Measurer TEXT,
            Item_Code TEXT,
            Batch TEXT,
            standard_usage TEXT,
            control_usage TEXT,
            reagents_usage TEXT,
            measuring_instrument_usage TEXT,
            File_Name TEXT,
            Type TEXT  -- Type カラムを追加
        )
        """

        create_table_qc_check_log = """
        CREATE TABLE IF NOT EXISTS table_qc_check_log (
            start_date TEXT,
            end_date TEXT,
            measurement TEXT,
            measurer TEXT,
            type TEXT,
            check_result TEXT,
            comment TEXT,
            check_date TEXT,
            date TEXT
        )
        """

        with self.get_connection() as conn:
            conn.execute(create_table_qc_pc)
            conn.execute(create_table_qc_status_log)
            conn.execute(create_table_qc_check_log)
            logger.info("必要なテーブルを作成または確認しました。")

    def add_type_column_if_not_exists(self) -> None:
        """table_qc_status_log に Type カラムを追加"""
        with self.get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(table_qc_status_log);")
            columns = [row[1] for row in cursor.fetchall()]
            if "Type" not in columns:
                try:
                    conn.execute(
                        "ALTER TABLE table_qc_status_log ADD COLUMN Type TEXT;"
                    )
                    logger.info("Type カラムを追加しました。")
                except sqlite3.Error as e:
                    logger.error("Type カラムの追加に失敗しました: %s", e)
                    st.error(f"Type カラムの追加に失敗しました: {e}")

    def add_date_column_if_not_exists(self) -> None:
        """table_qc_check_log に date カラムを追加"""
        with self.get_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(table_qc_check_log);")
            columns = [row[1] for row in cursor.fetchall()]
            if "date" not in columns:
                try:
                    conn.execute(
                        "ALTER TABLE table_qc_check_log ADD COLUMN date TEXT;")
                    logger.info("date カラムを追加しました。")
                except sqlite3.Error as e:
                    logger.error("date カラムの追加に失敗しました: %s", e)
                    st.error(f"date カラムの追加に失敗しました: {e}")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """データベース接続のコンテキスト管理"""
        conn = None
        try:
            if self._connection_pool:
                conn = self._connection_pool.pop()
            else:
                conn = sqlite3.connect(self.config.path)
            yield conn
        except sqlite3.Error as e:
            logger.error("データベース接続エラー: %s", str(e))
            st.error("データベースに接続できません")
            raise
        finally:
            if conn is not None:
                try:
                    conn.commit()
                    self._connection_pool.append(conn)
                except sqlite3.Error as e:
                    logger.error("接続のクローズに失敗: %s", e)
                    if conn is not None:
                        try:
                            conn.close()
                        except sqlite3.Error as close_error:
                            logger.error("接続のクローズに失敗: %s", close_error)

    def fetch_data(
        self, start_date: str, end_date: str
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """QCデータを取得し、セッションステートに格納"""
        query_qc = """
            SELECT Date_Time AS date_time, Type, SD_Conversion AS sd_conversion
            FROM table_qc_pc
            WHERE Date_Time BETWEEN ? AND ?
            ORDER BY Date_Time DESC
        """
        query_status = """
            SELECT Date_Time AS date_time, Item_Code, Batch, standard_usage,
            control_usage, reagents_usage, measuring_instrument_usage,
            Type AS status_type
            FROM table_qc_status_log
            WHERE Date_Time BETWEEN ? AND ?
            ORDER BY Date_Time DESC
        """
        try:
            with self.get_connection() as conn:
                qc_data = pd.read_sql_query(
                    query_qc,
                    conn,
                    params=(start_date, end_date),
                    parse_dates=["date_time"],
                )
                status_data = pd.read_sql_query(
                    query_status,
                    conn,
                    params=(start_date, end_date),
                    parse_dates=["date_time"],
                )
                return qc_data, status_data
        except (sqlite3.Error, pd.errors.DatabaseError) as e:
            logger.error("データベースエラー: %s", e)
            st.error(f"データの取得に失敗しました: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def save_qc_check(
        self,
        start_date: str,
        end_date: str,
        measurement: str,
        measurer: str,
        check_logs: List[Dict[str, str]],
    ) -> bool:
        """QCチェック結果をデータベースに保存"""
        query = """
            INSERT INTO table_qc_check_log
            (start_date, end_date, measurement, measurer, type, check_result,
            comment, check_date, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
        """
        try:
            with self.get_connection() as conn:
                for log in check_logs:
                    params = (
                        start_date,
                        end_date,
                        measurement,
                        measurer,
                        log["Type"],
                        log["comment_check"],
                        log["comment"],
                        date.today(),
                    )
                    conn.execute(query, params)
                st.balloons()
                return True
        except sqlite3.Error as e:
            logger.error("QCチェック結果の保存エラー: %s", e)
            st.error(f"QCチェック結果の保存に失敗しました: {e}")
            return False

    def get_table_schema_info(self, table_name: str) -> pd.DataFrame:
        """
        指定したテーブルのスキーマ情報を取得し、DataFrameで返す。

        Args:
            table_name (str): スキーマ情報を取得するテーブル名。

        Returns:
            pd.DataFrame: テーブルのスキーマ情報を含むDataFrame。
        """
        query = f"PRAGMA table_info({table_name});"
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query)
                columns = cursor.fetchall()
                # カラム情報をDataFrameに変換
                schema_df = pd.DataFrame(
                    columns,
                    columns=["cid",
                             "name",
                             "type",
                             "notnull",
                             "dflt_value",
                             "pk"],
                )
                return schema_df
        except sqlite3.Error as e:
            logger.error("スキーマ情報取得エラー: %s", e)
            st.error(f"スキーマ情報の取得に失敗しました: {e}")
            return pd.DataFrame()


class QCCheckUI:
    """QCチェックのUI管理"""

    def __init__(self,
                 db_manager: DatabaseManager,
                 today: date = date.today()):
        self.db_manager = db_manager
        self._today = today

    def init_session_state(self) -> None:
        """セッション状態を初期化"""
        if "check_data" not in st.session_state:
            st.session_state["check_data"] = (pd.DataFrame(), pd.DataFrame())

    def render_sidebar(self) -> tuple[str, str, str, str]:
        """サイドバーのUIを描画"""
        with st.sidebar:
            st.markdown("### 日付範囲を選択")
            # 前月の計算
            if self._today.month == 1:
                start_year = self._today.year - 1
                start_month = 12
            else:
                start_year = self._today.year
                start_month = self._today.month - 1

            start_date = st.date_input(
                "開始日", value=date(start_year, start_month, 1), key="start_date"
            )
            end_date = st.date_input("終了日", value=self._today, key="end_date")
            measurement = st.selectbox(
                "責任区分",
                [
                    "精度管理担当者",
                    "遺伝子関連・染色体検査の精度の確保に係る責任者",
                    "精度管理責任者",
                    "管理者",
                    "指導監督医",
                ],
                index=0,
            )
            measurer = st.text_input("精度管理評価者名  ").strip() or "未入力"
            # 変数に格納してから返す
            if isinstance(start_date, date):
                start_date_str = start_date.strftime("%Y-%m-%d")
            else:
                start_date_str = "不明"
            if isinstance(end_date, date):
                end_date_str = end_date.strftime("%Y-%m-%d")
            else:
                end_date_str = "不明"

            # データ取得ボタンを追加
            if st.button("データ取得"):
                st.session_state["check_data"] = self.db_manager.fetch_data(
                    start_date_str, end_date_str
                )

            return (start_date_str, end_date_str, measurement, measurer)

    def render_charts(self) -> List[Dict[str, str]]:
        """チャートを描画し、QCログを生成"""
        check_data = st.session_state.get(
            "check_data", (pd.DataFrame(), pd.DataFrame())
        )

        # check_dataがタプルであることを確認
        if not isinstance(check_data, tuple) or len(check_data) != 2:
            st.warning("データが正しく取得できていません")
            return []

        qc_data, status_data = check_data  # ここでデフォルト値を設定

        if qc_data is None or (isinstance(qc_data,
                                          pd.DataFrame) and qc_data.empty):
            st.warning("QCデータがありません")
            return []

        try:
            # QCデータの概要を表示
            st.subheader("抽出されたQCデータの概要")
            st.write("データ件数:", len(qc_data))
            st.write(
                "期間:", qc_data["date_time"
                               ].min(), "から", qc_data["date_time"].max()
            )

            # QCデータの詳細をExpander内に表示
            with st.expander("QCデータの詳細を表示"):
                st.dataframe(qc_data)

            check_logs = []
            for type_name, group in qc_data.groupby("Type"):
                with st.expander(f"Type: {type_name}", expanded=True):
                    st.line_chart(group.set_index("date_time")["sd_conversion"])

                    # ステータスデータを表示
                    status_group = status_data[status_data["status_type"] == type_name]
                    if not status_group.empty:
                        st.write("ステータスデータ:")
                        st.dataframe(status_group)

                    col1, col2 = st.columns([1, 3])
                    with col1:
                        comment_check = st.radio(
                            "QCコメント",
                            ["問題なし", "問題あり"],
                            key=f"comment_check_{type_name}",
                        )
                    with col2:
                        comment = st.text_input(
                            "コメント", key=f"comment_{type_name}"
                        ).strip()

                    check_logs.append(
                        {
                            "Type": type_name,
                            "comment_check": comment_check,
                            "comment": comment or "なし",
                        }
                    )

            return check_logs
        except (AttributeError, TypeError) as e:
            logger.warning("UI要素の生成に失敗: %s", str(e))
            st.error("UI要素の生成中にエラーが発生しました")
            return []


def main() -> None:
    """メインエントリポイント"""
    st.set_page_config(page_title="管理者関係：精度管理実施状況確認", layout="wide")
    st.title("品質管理状態確認")

    try:
        db_manager = DatabaseManager()
        ui = QCCheckUI(db_manager)
        ui.init_session_state()
        start_date, end_date, measurement, measurer = ui.render_sidebar()

        if not measurer:
            st.warning("精度管理評価者名を入力してください")
            return

        check_logs = ui.render_charts()
        if check_logs:
            st.success("QCチェックログが生成されました")

        # table_qc_status_log のデータフレームを表示
        st.subheader("標準物質／管理試料／検査試薬／検査機器：使用状況")
        check_data = st.session_state.get(
            "check_data", (pd.DataFrame(), pd.DataFrame())
        )
        status_data = check_data[1]

        if not status_data.empty:
            st.dataframe(
                status_data.rename(
                    columns={
                        "Date_Time": "日付:時間",
                        "Measurer": "測定者",
                        "Item_Code": "項目コード",
                        "Batch": "バッチ",
                        "standard_usage": "標準物質：使用状況",
                        "control_usage": "管理試料：使用量状況",
                        "reagents_usage": "検査試薬：使用状況",
                        "measuring_instrument_usage": "測定機器：使用状況",
                        "File_Name": "ファイル名",
                        "Type": "タイプ",
                    }
                )
            )
        else:
            st.write("table_qc_status_log にデータが存在しません。")

        # 保存ボタンを追加
        if st.button("チェック結果を保存"):
            if db_manager.save_qc_check(
                start_date, end_date, measurement, measurer, check_logs
            ):
                st.success("チェック結果を保存しました")
            else:
                st.error("チェック結果の保存に失敗しました")

    except (sqlite3.Error, ValueError, TypeError) as e:
        logger.error("アプリケーションエラー: %s", e)
        st.error(f"アプリケーションエラー: {e}")


if __name__ == "__main__":
    main()
