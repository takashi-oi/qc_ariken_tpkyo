"""Streamlitアプリケーションで測定項目とモデルを表示します。"""

import io
import logging
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import Config

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ページ設定
st.set_page_config(page_title="マスターテーブル管理", layout="wide")

# データベース設定（SQLite3）
DB_PATH = Config.MASTER_DATABASE_PATH

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
        """データベース接続を初期化（SQLite3）"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能にする
        self.create_master_tables()

    def create_master_tables(self):
        """マスターテーブルを作成（存在しない場合のみ）"""
        try:
            # テーブルが存在しない場合のみ作成
            # 実際の列構造はデータ移行時に動的に決定される
            cursor = self.conn.cursor()
            for table_name in MASTER_TABLES.values():
                # SQLite3でテーブルが存在するかチェック
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name=?
                    """,
                    (table_name,),
                )
                result = cursor.fetchone()

                if not result:
                    # 最小限のテーブルを作成（列は後で追加される）
                    cursor.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            id INTEGER PRIMARY KEY AUTOINCREMENT
                        )
                        """
                    )

            self.conn.commit()
            logger.info("マスターテーブル作成成功")
        except sqlite3.Error as e:
            logger.error("マスターテーブル作成エラー: %s", e)
            # エラーを無視して続行

    def import_excel_to_db(self, excel_file, table_key: str) -> bool:
        """ExcelファイルからDBにデータをインポート"""
        table_name = MASTER_TABLES.get(table_key)

        if not table_name:
            return False

        try:
            # Excelファイルを読み込む
            df = pd.read_excel(excel_file)

            if df.empty:
                return False

            # 既存テーブルを削除して再作成（列構造を動的に変更）
            cursor = self.conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

            # DataFrameから直接テーブルを作成（SQLite3用）
            df.to_sql(
                table_name,
                con=self.conn,
                if_exists="replace",
                index=False,
            )

            self.conn.commit()
            logger.info("%sのインポート成功: %d件", table_key, len(df))
            return True
        except Exception as e:
            logger.error("%sのインポートエラー: %s", table_key, e)
            return False

    def export_db_to_excel(self, table_name: str) -> bytes:
        """データベースからExcelファイルをエクスポート"""
        try:
            # データを読み込む
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.conn)

            # Excelファイルをメモリ上に作成
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
            output.seek(0)

            logger.info("%sのエクスポート成功: %d件", table_name, len(df))
            return output.getvalue()
        except Exception as e:
            logger.error("%sのエクスポートエラー: %s", table_name, e)
            raise

    def migrate_excel_to_db(self, table_key: str) -> bool:
        """既存のExcelファイルからDBにデータを移行（後方互換性のため）"""
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
            cursor = self.conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

            # DataFrameから直接テーブルを作成（SQLite3用）
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
            return False

    def load_master_data(self, table_name: str, force_reload: bool = False) -> pd.DataFrame:
        """マスターデータを読み込む（キャッシュ付き）"""
        if force_reload:
            # キャッシュをクリアして最新データを読み込む
            load_master_data_cached.clear()
        return load_master_data_cached(self.conn, table_name)

    def save_master_data(self, df: pd.DataFrame, table_name: str) -> bool:
        """マスターデータを保存"""
        try:
            # 既存データを削除
            cursor = self.conn.cursor()
            cursor.execute(f"DELETE FROM {table_name}")

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
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            result = cursor.fetchone()
            return result[0] > 0 if result else False
        except sqlite3.Error:
            return False

    def close(self):
        """接続を閉じる"""
        if self.conn:
            self.conn.close()


@st.cache_data(ttl=300)
def load_master_data_cached(_conn: sqlite3.Connection, table_name: str
                            ) -> pd.DataFrame:
    """マスターデータを読み込む（キャッシュ付き）"""
    try:
        query = f"SELECT * FROM {table_name}"
        return pd.read_sql_query(query, _conn)
    except sqlite3.Error as e:
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

# 選択されたテーブルを管理
if "selected_table" not in st.session_state:
    st.session_state.selected_table = "employee_code"

# エクスポートデータを管理
if "export_data" not in st.session_state:
    st.session_state.export_data = {}
if "export_filename" not in st.session_state:
    st.session_state.export_filename = {}

# テーブル名と表示名のマッピング
TABLE_DISPLAY_NAMES = {
    "employee_code": "担当者",
    "measurement_item": "測定パネル",
    "measuring_model": "測定機器",
    "qc_control": "QC Control",
}

# サイドバーに全てのボタンを配置
with st.sidebar:
    st.markdown("# マスターテーブル管理")
    
    # テーブル選択ボタン
    st.markdown("### マスターテーブル選択")
    if st.button("📋 担当者", key="btn_employee", use_container_width=True):
        st.session_state.selected_table = "employee_code"
        st.rerun()
    
    if st.button("🔧 測定機器", key="btn_measuring_model", use_container_width=True):
        st.session_state.selected_table = "measuring_model"
        st.rerun()
    
    if st.button("📊 測定パネル", key="btn_measurement_item", use_container_width=True):
        st.session_state.selected_table = "measurement_item"
        st.rerun()
    
    if st.button("⚙️ QC Control", key="btn_qc_control", use_container_width=True):
        st.session_state.selected_table = "qc_control"
        st.rerun()
    
    st.divider()
    
    # 選択されたテーブルの表示
    selected_table_key = st.session_state.selected_table
    table_name = MASTER_TABLES[selected_table_key]
    display_name = TABLE_DISPLAY_NAMES[selected_table_key]
    
    st.markdown(f"### 現在選択: {display_name}")
    
    st.divider()
    
    # アクションボタン
    st.markdown("### データ操作")
    
    if st.button("🔄 最新データを読み込む", key="btn_refresh", use_container_width=True):
        # キャッシュをクリアして最新データを読み込む
        load_master_data_cached.clear()
        st.success("最新データを読み込みました。")
        st.rerun()
    
    st.divider()
    
    # Excelインポート
    st.markdown("### 📥 Excelインポート")
    uploaded_file = st.file_uploader(
        "Excelファイルを選択",
        type=['xlsx', 'xls'],
        key=f"upload_{selected_table_key}",
        label_visibility="visible"
    )
    if uploaded_file is not None:
        st.info(f"ファイル: {uploaded_file.name}")
        if st.button("インポート実行", key=f"btn_import_{selected_table_key}", use_container_width=True, type="primary"):
            with st.spinner("インポート中..."):
                if db_manager.import_excel_to_db(uploaded_file, selected_table_key):
                    load_master_data_cached.clear()
                    st.success(f"{display_name}のデータをインポートしました。")
                    st.rerun()
                else:
                    st.error("データのインポートに失敗しました。")
    
    st.divider()
    
    # Excelエクスポート
    st.markdown("### 📤 Excelエクスポート")
    if db_manager.check_table_has_data(table_name):
        if st.button("エクスポート実行", key=f"btn_export_{selected_table_key}", use_container_width=True, type="primary"):
            with st.spinner("エクスポート中..."):
                try:
                    excel_data = db_manager.export_db_to_excel(table_name)
                    excel_filename = f"{display_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    st.session_state.export_data[selected_table_key] = excel_data
                    st.session_state.export_filename[selected_table_key] = excel_filename
                    st.success("エクスポートデータを準備しました。")
                    st.rerun()
                except Exception as e:
                    st.error(f"エクスポートエラー: {e}")
        
        # エクスポートデータが準備されている場合はダウンロードボタンを表示
        if selected_table_key in st.session_state.export_data:
            st.download_button(
                label="📥 Excelファイルをダウンロード",
                data=st.session_state.export_data[selected_table_key],
                file_name=st.session_state.export_filename[selected_table_key],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_{selected_table_key}",
                use_container_width=True
            )
    else:
        st.info("エクスポートするデータがありません。")
    
    st.divider()
    
    # データ移行（既存のExcelファイルから）
    st.markdown("### データ移行")
    if st.button("ExcelからDBへ全データ移行", use_container_width=True):
        with st.spinner("データを移行中..."):
            for table_key in MASTER_TABLES.keys():
                if db_manager.migrate_excel_to_db(table_key):
                    st.session_state.migration_done[table_key] = True
                    st.success(f"{table_key}の移行完了")
                else:
                    st.warning(f"{table_key}の移行をスキップ（ファイルなし）")
        st.rerun()

# メインコンテンツエリア
st.markdown("# マスターテーブル管理")

# 選択されたテーブルの表示
selected_table_key = st.session_state.selected_table
table_name = MASTER_TABLES[selected_table_key]
display_name = TABLE_DISPLAY_NAMES[selected_table_key]

st.markdown(f"## {display_name}")

# データの読み込みと表示
if not db_manager.check_table_has_data(table_name):
    st.info(f"{display_name}のデータがありません。Excelから移行するか、データを追加してください。")
    edited_df = pd.DataFrame()
else:
    # データを読み込む
    df = db_manager.load_master_data(table_name)
    
    if df.empty:
        st.info(f"{display_name}のデータが空です。データを追加してください。")
        edited_df = pd.DataFrame()
    else:
        st.markdown(f"**データ件数: {len(df)}件**")
        
        # データエディタで編集可能にする
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            key=f"editor_{selected_table_key}",
        )
        
        # 保存ボタン（データエディタの下に配置）
        if st.button("💾 変更を保存", key="btn_save", use_container_width=True, type="primary"):
            if not edited_df.empty:
                if db_manager.save_master_data(edited_df, table_name):
                    load_master_data_cached.clear()
                    st.success(f"{display_name}のデータを保存しました。")
                    st.rerun()
                else:
                    st.error("データの保存に失敗しました。")
            else:
                st.warning("保存するデータがありません。")

# クリーンアップ
db_manager.close()
