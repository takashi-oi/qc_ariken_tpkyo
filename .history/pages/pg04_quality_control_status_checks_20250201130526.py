"""
品質管理（QC）データの精度管理を行うためのモジュール。
データベースからQCデータを取得し、グラフ表示とコメント入力機能を提供します。
"""

import sqlite3
import logging
from dataclasses import dataclass
from typing import List, Generator, Dict
from contextlib import contextmanager
from datetime import date

import pandas as pd
import streamlit as st

# loggingの重複定義を避けるため、再定義を削除
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DatabaseConfig:
    """データベース構成設定"""
    path: str = 'db_folder/qc_data_base.db'
    max_attempts: int = 3


class DatabaseManager:
    """データベース管理クラス"""

    def __init__(self, config: DatabaseConfig = DatabaseConfig()):
        self.config = config
        self._connection_pool: List[sqlite3.Connection] = []

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
            logger.error("データベース接続エラー: %s", e)
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

    def fetch_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """QCデータを取得"""
        query = """
            SELECT
                t1.type,
                t1.log_datetime,
                t1.result,
                t2.info_message
            FROM
                table_qc_act_log t1
                LEFT JOIN table_qc_info_log t2 
                ON t1.log_datetime = t2.log_datetime
                AND t1.type = t2.type
            WHERE 
                t1.log_datetime BETWEEN ? AND ?
            ORDER BY 
                t1.type,
                t1.log_datetime DESC
        """
        try:
            with self.get_connection() as conn:
                return pd.read_sql_query(
                    query,
                    conn,
                    params=(start_date, end_date),
                    parse_dates=['log_datetime']
                )
        except (sqlite3.Error, pd.errors.DatabaseError) as e:
            logger.error("データ取得エラー: %s", e)
            st.error("データの取得に失敗しました")
            return pd.DataFrame()

    def save_qc_check(self, start_date: str, end_date: str, measurement: str,
                      measurer: str, check_logs: List[Dict[str, str]]) -> bool:
        """QCチェック結果をデータベースに保存"""
        query = """
            INSERT INTO qc_checks
            (start_date, end_date, measurement, measurer, type, check_result,
            comment, check_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        try:
            with self.get_connection() as conn:
                for log in check_logs:
                    params = (
                        start_date,
                        end_date,
                        measurement,
                        measurer,
                        log['Type'],
                        log['comment_check'],
                        log['comment']
                    )
                    conn.execute(query, params)
                return True
        except sqlite3.Error as e:
            logger.error("QCチェック結果の保存エラー: %s", e)
            st.error("QCチェック結果の保存に失敗しました")
            return False


class QCCheckUI:
    """QCチェックのUI管理"""
    def __init__(self,
                 db_manager: DatabaseManager,
                 today: date = date.today()):
        self.db_manager = db_manager
        self._today = today

    def init_session_state(self) -> None:
        """セッション状態を初期化"""
        if 'check_data' not in st.session_state:
            st.session_state['check_data'] = None

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
                "開始日",
                value=date(start_year, start_month, 1),
                key="start_date"
            )
            end_date = st.date_input("終了日",
                                     value=self._today,
                                     key="end_date")
            measurement = st.selectbox("責任区分", [
                "遺伝子関連・染色体検査の精度の確保に係る責任者",
                "管理者",
                "指導監督医",
                "精度管理責任者",
                "精度管理担当者"
            ], index=0)
            measurer = st.text_input("測定者名を入力してください").strip() or "未入力"
            # 変数に格納してから返す
            if isinstance(start_date, date):
                start_date_str = start_date.strftime('%Y-%m-%d')
            else:
                start_date_str = "不明"
            if isinstance(end_date, date):
                end_date_str = end_date.strftime('%Y-%m-%d')
            else:
                end_date_str = "不明"

            # データ取得ボタンを追加
            if st.button("データ取得"):
                data = self.db_manager.fetch_data(start_date_str, end_date_str)
                st.session_state['check_data'] = data

            return (
                start_date_str,
                end_date_str,
                measurement,
                measurer
            )

    def render_charts(self) -> List[Dict[str, str]]:
        """チャートを描画し、QCログを生成"""
        data = st.session_state.get('check_data')
        if data is None or isinstance(data, pd.DataFrame) and data.empty:
            st.warning("データがありません")
            return []

        try:
            # データの概要を表示
            st.subheader("抽出されたデータの概要")
            st.write("データ件数:", len(data))
            st.write("期間:",
                     data['log_datetime'].min(),
                     "から", data['log_datetime'].max()
                     )

            # データの詳細をExpander内に表示
            with st.expander("データの詳細を表示"):
                st.dataframe(data)

            check_logs = []
            for type_name, group in data.groupby('type'):
                with st.expander(f"Type: {type_name}", expanded=True):
                    st.line_chart(
                        group.set_index('log_datetime')['result']
                    )

                    col1, col2 = st.columns([1, 3])
                    with col1:
                        comment_check = st.radio(
                            "QCコメント",
                            ["問題なし", "問題あり"],
                            key=f"comment_check_{type_name}"
                        )
                    with col2:
                        comment = st.text_input(
                            "コメント",
                            key=f"comment_{type_name}"
                        ).strip()

                    check_logs.append({
                        'Type': type_name,
                        'comment_check': comment_check,
                        'comment': comment or "なし"
                    })

            return check_logs
        except (ValueError, KeyError, TypeError) as e:
            logger.error("チャート描画エラー: %s", e)
            st.error("チャートの描画中にエラーが発生しました")
            return []


def main() -> None:
    """メインエントリポイント"""
    st.set_page_config(page_title="QC管理チェック", layout="wide")
    st.title("管理者関係：品質管理状態確認記録")

    try:
        db_manager = DatabaseManager()
        ui = QCCheckUI(db_manager)
        ui.init_session_state()
        start_date, end_date, measurement, measurer = ui.render_sidebar()

        if not measurer:
            st.warning("測定者名を入力してください")
            return

        check_logs = ui.render_charts()
        if check_logs:
            st.success("QCチェックログが生成されました")

            # 保存ボタンを追加
            if st.button("チェック結果を保存"):
                if db_manager.save_qc_check(start_date, end_date, measurement,
                                            measurer, check_logs):
                    st.success("チェック結果を保存しました")
                else:
                    st.error("チェック結果の保存に失敗しました")
        else:
            st.warning("QCチェックログは生成されませんでした")
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error("アプリケーションエラー: %s", e)
        st.error("重大なエラーが発生しました")


if __name__ == "__main__":
    main()
