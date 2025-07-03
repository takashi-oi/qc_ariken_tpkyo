"""
品質管理（QC）データの精度管理を行うためのモジュール。
データベースからQCデータを取得し、グラフ表示とコメント入力機能を提供します。
"""

import sqlite3
import logging

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import date
from typing import Generator
import pandas as pd
import streamlit as st


# ログの設定を修正
logging.basicConfig(
    level=20,  # INFOレベルは20
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """データベース構成設定"""
    path: str = 'db_folder/qc_data_base.db'
    max_attempts: int = 3


class DatabaseManager:
    """データベース管理クラス"""
    def __init__(self, config: DatabaseConfig = DatabaseConfig()):
        self.config = config

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """データベース接続のコンテキスト管理"""
        conn = None
        for attempt in range(self.config.max_attempts):
            try:
                conn = sqlite3.connect(self.config.path)
                yield conn
                break
            except sqlite3.Error as e:
                logger.error("Connection attempt %d failed: %s",
                             attempt + 1,
                             e)
                if attempt == self.config.max_attempts - 1:
                    st.error("データベースに接続できません")
                    raise
            finally:
                if conn is not None:
                    conn.close()

    def fetch_data(self, days_back: int = 30) -> pd.DataFrame:
        """QCデータを取得"""
        query = """
            SELECT Date_Time AS date_time, Type, SD_Conversion AS sd_conversion
            FROM table_qc_pc
            WHERE datetime(Date_Time) >= datetime('now', '-? days')
            ORDER BY Date_Time DESC
        """
        try:
            with self.get_connection() as conn:
                return pd.read_sql_query(query, conn, params=(days_back,))
        except (sqlite3.Error, pd.errors.DatabaseError) as e:
            logger.error("データ取得エラー: %s", e)
            st.error("データの取得に失敗しました")
            return pd.DataFrame()


class QCCheckUI:
    """QCチェックのUI管理"""
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def init_session_state(self) -> None:
        """セッション状態を初期化"""
        if 'check_data' not in st.session_state:
            data = self.db_manager.fetch_data()
            st.session_state['check_data'] = data if not data.empty else None

    @staticmethod
    def render_sidebar() -> tuple[date, str, str]:
        """サイドバーのUIを描画"""
        try:
            with st.sidebar:
                selected_date = st.date_input("日付を選択",
                                              value=date.today())
                measurement = st.selectbox("責任区分",
                                           ["Precision Manager",
                                            "Quality Manager", "Other Manager"
                                            ])
                measurer = st.text_input("測定者名を入力してください").strip()
                # st.date_inputの戻り値を安全にdate型に変換
                if hasattr(selected_date, 'date'):
                    selected_date = selected_date.date()
                elif not isinstance(selected_date, date):
                    selected_date = date.today() if not isinstance(
                        selected_date, date) else selected_date
            return selected_date, measurement, measurer
        except (AttributeError, TypeError) as e:
            logger.warning("UI要素の生成に失敗: %s", e)
            return date.today(), "Precision Manager", ""

    def render_charts(self) -> list[dict[str, str]]:
        """チャートを描画し、QCログを生成"""
        data = st.session_state.get('check_data')
        if data is None:
            st.warning("データがありません")
            return []

        check_logs = []
        for type_name, group in data.groupby('Type'):
            with st.expander(f"Type: {type_name}", expanded=True):
                st.line_chart(group, x='date_time', y='sd_conversion')

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


def main():
    """メインエントリポイント"""
    st.set_page_config(page_title="QC管理チェック", layout="wide")
    st.title("品質管理状態確認")

    try:
        db_manager = DatabaseManager()
        ui = QCCheckUI(db_manager)

        ui.init_session_state()
        selected_date, measurement, measurer = ui.render_sidebar()

        if not measurer:
            st.warning("測定者名を入力してください")
            return

        check_logs = ui.render_charts()
        if check_logs:
            st.success("QCチェックログが生成されました")
        else:
            st.warning("QCチェックログは生成されませんでした")
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error("アプリケーションエラー: %s", e)
        st.error("重大なエラーが発生しました")


if __name__ == "__main__":
    main()
