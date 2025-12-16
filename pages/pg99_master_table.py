"""Streamlitアプリケーションで測定項目とモデルを表示します。"""

import logging
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ページ設定
st.set_page_config(page_title="マスターテーブル管理", layout="wide")

# データベース設定
DB_PATH = "db_folder/qc_data_base.db"

# マスターテーブル名
MASTER_TABLES = {
    "measurement_item": "master_measurement_item",
    "measuring_model": "master_measuring_model",
    "employee_code": "master_employee_code",
    "qc_control": "master_qc_control",
}

# 既存のExcelファイルパス（移行用）
MASTER_DIR = Path("data/master")
EXCEL_FILES = {
    "measurement_item": MASTER_DIR / "measurement_item.xlsx",
    "measuring_model": MASTER_DIR / "measuring_model.xlsx",
    "employee_code": MASTER_DIR / "employee_code.xlsx",
    "qc_control": MASTER_DIR / "qc_control.xlsx",
}


class MasterDatabaseManager:
    """マスターデータベース管理クラス"""

    def __init__(self, db_path: str):
        """データベース接続を初期化"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self.create_master_tables()

    def create_master_tables(self):
        """マスターテーブルを作成（存在しない場合のみ）"""
        try:
            # テーブルが存在しない場合のみ作成
            # 実際の列構造はデータ移行時に動的に決定される
            for table_name in MASTER_TABLES.values():
                # テーブルが存在するかチェック
                result = self.conn.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_name = '{table_name}'
                    """
                ).fetchone()

                if not result or result[0] == 0:
                    # 最小限のテーブルを作成（列は後で追加される）
                    self.conn.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            id INTEGER PRIMARY KEY
                        )
                        """
                    )

            self.conn.commit()
            logger.info("マスターテーブル作成成功")
        except duckdb.Error as e:
            logger.error("マスターテーブル作成エラー: %s", e)
            # DuckDBではinformation_schemaが使えない場合があるため、
            # エラーを無視して続行

    def migrate_excel_to_db(self, table_key: str) -> bool:
        """ExcelファイルからDBにデータを移行"""
        excel_path = EXCEL_FILES.get(table_key)
        table_name = MASTER_TABLES.get(table_key)

        if not excel_path or not excel_path.exists():
            return False

        try:
            # Excelファイルを読み込む
            df = pd.read_excel(excel_path)

            if df.empty:
                return False

            # 既存テーブルを削除して再作成（列構造を動的に変更）
            self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")

            # DataFrameから直接テーブルを作成
            df.to_sql(
                table_name,
                con=self.conn,
                if_exists="replace",
                index=False,
            )

            self.conn.commit()
            logger.info("%sの移行成功: %d件", table_key, len(df))
            return True
        except Exception as e:
            logger.error("%sの移行エラー: %s", table_key, e)
            # エラー時は、DataFrameを直接使用してテーブルを作成
            try:
                df.to_sql(
                    table_name,
                    con=self.conn,
                    if_exists="replace",
                    index=False,
                )
                self.conn.commit()
                logger.info("%sの移行成功（代替方法）: %d件", table_key, len(df))
                return True
            except Exception as e2:
                logger.error("%sの移行エラー（代替方法）: %s", table_key, e2)
                return False

    def load_master_data(self, table_name: str) -> pd.DataFrame:
        """マスターデータを読み込む（キャッシュ付き）"""
        return load_master_data_cached(self.conn, table_name)

    def save_master_data(self, df: pd.DataFrame, table_name: str) -> bool:
        """マスターデータを保存"""
        try:
            # 既存データを削除
            self.conn.execute(f"DELETE FROM {table_name}")

            # データを挿入
            df.to_sql(
                table_name,
                con=self.conn,
                if_exists="append",
                index=False,
            )

            self.conn.commit()
            # キャッシュをクリア
            st.cache_data.clear()
            logger.info("%sの保存成功: %d件", table_name, len(df))
            return True
        except Exception as e:
            logger.error("%sの保存エラー: %s", table_name, e)
            return False

    def check_table_has_data(self, table_name: str) -> bool:
        """テーブルにデータが存在するか確認"""
        try:
            result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] > 0 if result else False
        except duckdb.Error:
            return False

    def close(self):
        """接続を閉じる"""
        if self.conn:
            self.conn.close()


@st.cache_data(ttl=300)
def load_master_data_cached(
    conn: duckdb.DuckDBPyConnection, table_name: str
) -> pd.DataFrame:
    """マスターデータを読み込む（キャッシュ付き）"""
    try:
        query = f"SELECT * FROM {table_name}"
        return pd.read_sql_query(query, conn)
    except duckdb.Error as e:
        logger.error("マスターデータ読み込みエラー: %s", e)
        return pd.DataFrame()


# データベースマネージャーを初期化
try:
    db_manager = MasterDatabaseManager(DB_PATH)
except Exception as e:
    st.error(f"データベース接続エラー: {e}")
    st.stop()

# 初回移行チェック
if "migration_done" not in st.session_state:
    st.session_state.migration_done = {}

# サイドバーに移行ボタンを追加
with st.sidebar:
    st.markdown("### データ移行")
    if st.button("ExcelからDBへ全データ移行"):
        with st.spinner("データを移行中..."):
            for table_key in MASTER_TABLES.keys():
                if db_manager.migrate_excel_to_db(table_key):
                    st.session_state.migration_done[table_key] = True
                    st.success(f"{table_key}の移行完了")
                else:
                    st.warning(f"{table_key}の移行をスキップ（ファイルなし）")
        st.rerun()

st.markdown("# マスターテーブル")

# 各マスターテーブルの表示と編集
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("## 測定項目")
    table_name = MASTER_TABLES["measurement_item"]

    # データが存在しない場合はExcelから移行を試みる
    if not db_manager.check_table_has_data(table_name):
        if EXCEL_FILES["measurement_item"].exists():
            if st.button("測定項目: Excelから移行", key="migrate_item"):
                if db_manager.migrate_excel_to_db("measurement_item"):
                    st.success("移行完了")
                    st.rerun()
        else:
            st.info("データがありません。データを追加してください。")

    item = db_manager.load_master_data(table_name)
    if not item.empty:
        edited_item = st.data_editor(item, num_rows="dynamic")
        if st.button("測定項目を登録/修正", key="save_item"):
            if db_manager.save_master_data(edited_item, table_name):
                st.success("測定項目を保存しました。")
                st.rerun()

with col2:
    st.markdown("## 測定機器")
    table_name = MASTER_TABLES["measuring_model"]

    if not db_manager.check_table_has_data(table_name):
        if EXCEL_FILES["measuring_model"].exists():
            if st.button("測定機器: Excelから移行", key="migrate_model"):
                if db_manager.migrate_excel_to_db("measuring_model"):
                    st.success("移行完了")
                    st.rerun()
        else:
            st.info("データがありません。データを追加してください。")

    model = db_manager.load_master_data(table_name)
    if not model.empty:
        edited_model = st.data_editor(model, num_rows="dynamic")
        if st.button("測定機器を登録/修正", key="save_model"):
            if db_manager.save_master_data(edited_model, table_name):
                st.success("測定機器を保存しました。")
                st.rerun()

with col3:
    st.markdown("## 担当者")
    table_name = MASTER_TABLES["employee_code"]

    if not db_manager.check_table_has_data(table_name):
        if EXCEL_FILES["employee_code"].exists():
            if st.button("担当者: Excelから移行", key="migrate_employee"):
                if db_manager.migrate_excel_to_db("employee_code"):
                    st.success("移行完了")
                    st.rerun()
        else:
            st.info("データがありません。データを追加してください。")

    employee = db_manager.load_master_data(table_name)
    if not employee.empty:
        edited_employee = st.data_editor(employee, num_rows="dynamic")
        if st.button("担当者名を登録/修正", key="save_employee"):
            if db_manager.save_master_data(edited_employee, table_name):
                st.success("担当者名を保存しました。")
                st.rerun()

st.markdown("## QC Control")
table_name = MASTER_TABLES["qc_control"]

if not db_manager.check_table_has_data(table_name):
    if EXCEL_FILES["qc_control"].exists():
        if st.button("QC Control: Excelから移行", key="migrate_control"):
            if db_manager.migrate_excel_to_db("qc_control"):
                st.success("移行完了")
                st.rerun()
    else:
        st.info("データがありません。データを追加してください。")

control = db_manager.load_master_data(table_name)
if not control.empty:
    edited_control = st.data_editor(control, num_rows="dynamic")
    if st.button("QC Controlを保存", key="save_control"):
        if db_manager.save_master_data(edited_control, table_name):
            st.success("QC Controlを保存しました。")
            st.rerun()

# クリーンアップ
db_manager.close()
