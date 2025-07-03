"""
検査測定状況管理記録登録システム
"""

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional, Literal

import pandas as pd
import streamlit as st

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# アプリケーション設定
st.set_page_config(
    page_title="検査測定状況管理記録登録",
    layout="wide"
)


@dataclass
class Config:
    """アプリケーション設定"""
    db_path: str = "db_folder/qc_data_base.db"
    employee_master: str = "master_folder/employee_code.xlsx"
    measurement_master: str = "master_folder/measurement_item.xlsx"
    page_title: str = "検査測定状況管理記録登録"
    page_layout: Literal["centered", "wide"] = "wide"
    recent_records_limit: int = 5


class DatabaseManager:
    """データベース接続管理"""
    _instance = None  # シングルトンパターン用
    db_path: str  # db_path 属性を追加
    _conn: sqlite3.Connection  # _conn 属性を追加

    def __new__(cls, db_path: str):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path
            # データベースディレクトリの存在確認・作成
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("PRAGMA foreign_keys = ON")
                logger.info("データベース接続成功: %s", db_path)
                cls._instance._conn = conn
            except sqlite3.Error as e:
                logger.error("データベース接続エラー: %s", e)
                raise
        return cls._instance

    def get_connection(self) -> sqlite3.Connection:
        """コネクション取得"""
        return self._conn

    def close(self):
        """接続を明示的に閉じる"""
        if hasattr(self, '_conn') and self._conn:
            self._conn.close()
            logger.info("データベース接続を閉じました")

    def __del__(self):
        """デストラクタで接続を閉じる"""
        self.close()


class DatabaseInitializer:
    """データベース初期化処理"""
    @staticmethod
    def create_tables(conn: sqlite3.Connection) -> bool:
        """必要なテーブルを作成、成功時True、失敗時Falseを返す"""
        try:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS qc_multi_rule (
                    Date_Time TEXT,
                    Batch TEXT,
                    Item_Code TEXT,
                    type TEXT,
                    QC_RESULTS TEXT,
                    Violated_rule TEXT,
                    PRIMARY KEY (Date_Time, Batch, Item_Code, type)
                );

                CREATE TABLE IF NOT EXISTS qc_act_log (
                    Date_Time TEXT,
                    Batch TEXT,
                    Item_Code TEXT,
                    type TEXT,
                    implementor TEXT,
                    standard_usage TEXT,
                    control_usage TEXT,
                    reagents_usage TEXT,
                    measuring_instrument_usage TEXT,
                    cause TEXT,
                    capa TEXT,
                    Violated_rule TEXT,
                    PRIMARY KEY (Date_Time, Batch, Item_Code, type)
                );
            """)
            conn.commit()
            logger.info("テーブル作成成功")
            return True
        except sqlite3.Error as e:
            logger.error("テーブル作成エラー: %s", e)
            return False


class QCDataAccess:
    """データアクセス層"""
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._create_indices()

    def _create_indices(self) -> None:
        """パフォーマンス向上のためのインデックスを作成"""
        try:
            cursor = self.conn.cursor()
            cursor.executescript("""
                CREATE INDEX IF NOT EXISTS idx_mulch_rule_date_time ON
                                 qc_multi_rule (Date_Time);
                CREATE INDEX IF NOT EXISTS idx_mulch_rule_item_code ON
                                 qc_multi_rule (Item_Code);
                CREATE INDEX IF NOT EXISTS idx_act_log_date_time ON
                                 qc_act_log (Date_Time);
            """)
            self.conn.commit()
            logger.info("インデックス作成成功")
        except sqlite3.Error as e:
            logger.warning("インデックス作成エラー: %s", e)

    def get_recent_dates(self, item_code: str, limit: int = 5) -> List[str]:
        """最近の実施日を取得"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT DISTINCT Date_Time
                FROM qc_multi_rule
                WHERE Item_Code = ?
                ORDER BY Date_Time DESC
                LIMIT ?
            """, (item_code, limit))
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("最近の実施日取得エラー: %s", e)
            return []

    def check_duplicate(self,
                        date_time: str,
                        batch: str,
                        item_code: str,
                        type_var: str
                        ) -> bool:
        """重複チェック"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 1 FROM qc_act_log
                WHERE Date_Time = ? AND Batch = ? AND Item_Code = ? AND \
                           type = ?
                LIMIT 1
            """, (date_time, batch, item_code, type_var))
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error("重複チェックエラー: %s", e)
            return False

    def insert_qc_data(self, data: Dict[str, Any]) -> bool:
        """QCデータの挿入、成功時True、失敗時Falseを返す"""
        try:
            # データを適切な形式に変換
            formatted_data = {
                "Date_Time": data["date_time"].strftime("%Y-%m-%d"),
                "Batch": data["batch"],
                "Item_Code": data["item_code"],
                "type": data["type_variable"],
                "implementor": data["implementor"],
                "standard_usage": data["standard_usage"],
                "control_usage": data["control_usage"],
                "reagents_usage": data["reagents_usage"],
                "measuring_instrument_usage": data[
                    "measuring_instrument_usage"],
                "cause": data["cause"],
                "capa": data["capa"],
                "Violated_rule": data["Violated_rule"]
            }

            # 重複チェック
            if self.check_duplicate(
                formatted_data["Date_Time"],
                formatted_data["Batch"],
                formatted_data["Item_Code"],
                formatted_data["type"]
            ):
                logger.warning("重複データが存在します")
                return False

            # DataFrameに変換して挿入
            df = pd.DataFrame([formatted_data])
            with self.conn:
                df.to_sql("qc_act_log",
                          con=self.conn,
                          if_exists="append",
                          index=False,
                          method="multi")
            logger.info("1件のデータを登録しました")
            return True
        except (sqlite3.Error, pd.errors.DatabaseError) as e:
            logger.error("データ登録エラー: %s", e)
            return False

    def get_violated_rules(self,
                           item_code: Optional[str] = None
                           ) -> pd.DataFrame:
        """違反ルールの取得"""
        try:
            query = """
                SELECT DISTINCT Violated_rule
                FROM qc_multi_rule
            """
            params = ()

            if item_code:
                query += " WHERE Item_Code = ?"
                params = (item_code,)

            return pd.read_sql_query(query, self.conn, params=params)
        except sqlite3.Error as e:
            logger.error("違反ルール取得エラー: %s", e)
            return pd.DataFrame()

    def get_recent_records(self, limit: int = 5) -> pd.DataFrame:
        """最近の記録を取得"""
        try:
            query = """
                SELECT Date_Time, Batch, Item_Code, type, implementor,
                Violated_rule
                FROM qc_act_log
                ORDER BY Date_Time DESC
                LIMIT ?
            """
            return pd.read_sql_query(query, self.conn, params=(limit,))
        except sqlite3.Error as e:
            logger.error("最近の記録取得エラー: %s", e)
            return pd.DataFrame()


class MasterDataLoader:
    """マスターデータ読み込み（キャッシュ対応）"""
    _measurement_items_cache = None
    _employee_data_cache = None

    @classmethod
    def load_measurement_items(cls,
                               force_reload: bool = False
                               ) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """検査項目マスターの読み込み"""
        if cls._measurement_items_cache is not None and not force_reload:
            return cls._measurement_items_cache

        try:
            file_path = Path(Config.measurement_master)
            if not file_path.exists():
                logger.error("検査項目マスターファイルが存在しません: %s", file_path)
                return pd.DataFrame(), {}

            df = pd.read_excel(file_path)
            df.rename(columns={
                "項目コード": "Item_Code",
                "測定項目": "Measurement_Item"
            }, inplace=True)
            item_mapping = dict(zip(df["Item_Code"], df["Measurement_Item"]))
            cls._measurement_items_cache = (df, item_mapping)
            logger.info("検査項目マスター読み込み成功: %d件", len(df))
            return cls._measurement_items_cache
        except (FileNotFoundError,
                pd.errors.EmptyDataError,
                pd.errors.ParserError
                ) as e:
            logger.error("検査項目マスターの読み込みエラー: %s", e)
            return pd.DataFrame(), {}

    @classmethod
    def load_employee_data(cls, force_reload: bool = False) -> pd.DataFrame:
        """検査要員マスタの読み込み"""
        if cls._employee_data_cache is not None and not force_reload:
            return cls._employee_data_cache

        try:
            file_path = Path(Config.employee_master)
            if not file_path.exists():
                logger.error(
                    "検査要員マスタファイルが存在しません: %s", file_path)
                return pd.DataFrame()

            cls._employee_data_cache = pd.read_excel(file_path)
            logger.info(
                "検査要員マスタ読み込み成功: %d件", len(cls._employee_data_cache))
            return cls._employee_data_cache
        except (FileNotFoundError,
                pd.errors.EmptyDataError,
                pd.errors.ParserError) as e:
            logger.error("検査要員マスタの読み込みエラー: %s", e)
            return pd.DataFrame()


class FormValidator:
    """フォームデータ検証"""
    @staticmethod
    def validate_input(data: Dict[str, Any]) -> Tuple[bool, str]:
        """入力データの検証、(成功時True, エラーメッセージ)を返す"""
        required_fields = {
            "implementor": "実施者",
            "item_code": "項目コード",
            "date_time": "実施日時",
            "batch": "バッチ",
            "type_variable": "タイプ",
            "Violated_rule": "違反ルール"
        }

        for field, display_name in required_fields.items():
            if not data.get(field):
                return False, f"{display_name}は必須項目です"

        return True, ""


# Streamlitアプリケーション本体
def main():
    """メイン関数"""
    # サイドバーに担当者セレクトボックスを追加（未使用変数は削除）
    employee_df = MasterDataLoader.load_employee_data()
    if not employee_df.empty and "Member's_Name" in employee_df.columns:
        st.sidebar.selectbox(
            "担当者を選択",
            options=[""] + employee_df["Member's_Name"].tolist(),
            key="sidebar_implementor"
        )
    else:
        st.sidebar.warning("従業員マスターの読み込みに失敗しました。")

    # サイドバーに直近で読み込んだファイル名5件をセレクトボックスで表示
    file_info_df = st.session_state.get('file_info_df', pd.DataFrame({'File_Name': []}))
    file_name_options = file_info_df['File_Name'].tolist()

    def file_name_format(x):
        return x if x in file_name_options else 'Unknown'
    _ = st.selectbox(
        '測定ファイル名を選択して下さい',
        file_name_options,
        format_func=file_name_format
    )

    # アプリケーション設定
    st.markdown(f"### {Config.page_title}")

    # データベース初期化
    try:
        db_manager = DatabaseManager(Config.db_path)
        conn = db_manager.get_connection()
        initializer = DatabaseInitializer()
        if not initializer.create_tables(conn):
            st.error("データベースの初期化に失敗しました。ログを確認してください。")
            return

        data_access = QCDataAccess(conn)
    except (sqlite3.Error, FileNotFoundError) as e:
        st.error(f"データベース接続エラー: {e}")
        logger.error("データベース接続エラー: %s", e)
        return

    # マスターデータ読み込み
    measurement_df = MasterDataLoader.load_measurement_items()
    employee_df = MasterDataLoader.load_employee_data()

    if measurement_df[0].empty:
        st.warning("検査項目マスターの読み込みに失敗しました。")
    if employee_df.empty:
        st.warning("従業員マスターの読み込みに失敗しました。")

    # タブの作成
    tabs = st.tabs(["QCデータ登録", "最近の登録"])
    tab1, tab2 = tabs

    with tab1:
        # フォーム表示
        with st.form("qc_data_form"):
            st.subheader("QCデータ登録")

            # 項目選択
            item_options = []
            if not measurement_df[0].empty:
                item_options = [
                    f"{code} - {name}"
                    for code, name in zip(measurement_df[0]["Item_Code"],
                                          measurement_df[0]["Measurement_Item"
                                                            ])
                ]
            selected_item = st.selectbox("検査項目", options=[""] + item_options)
            selected_item_code = selected_item.split(
                " - ")[0] if selected_item and " - " in selected_item else ""
            st.form_submit_button("送信")

            # 日付時間の入力
            date_time = st.date_input("実施日")
            batch = st.text_input("バッチ")
            type_variable = st.selectbox("タイプ",
                                         options=["",
                                                  "OOS（規格外：再検査）",
                                                  "Shift（規格内：採用）",
                                                  "Trend（規格内：採用）"])

            # 違反ルール選択
            violated_rule_df = data_access.get_violated_rules(
                selected_item_code)
            if not violated_rule_df.empty and "Violated_rule" \
                    in violated_rule_df.columns:
                violated_rule_options = violated_rule_df[
                    "Violated_rule"].tolist()
            else:
                violated_rule_options = []
            violated_rule = st.selectbox("違反ルール",
                                         options=[""] + violated_rule_options)

            # 詳細情報入力
            col1, col2 = st.columns(2)
            with col1:
                standard_usage = st.text_area("標準物質使用状況")
                control_usage = st.text_area("管理試料使用状況")
            with col2:
                reagents_usage = st.text_area("試薬使用状況")
                measuring_instrument_usage = st.text_area("測定機器使用状況")
            cause = st.text_area("推測される原因")
            capa = st.text_area("CAPA（予防処置・是正処置）")

            # 送信ボタン
            submitted = st.form_submit_button("登録")
            if submitted:
                form_data = {
                    "item_code": selected_item_code,
                    "date_time": date_time,
                    "batch": batch,
                    "type_variable": type_variable,
                    "Violated_rule": violated_rule,
                    "standard_usage": standard_usage,
                    "control_usage": control_usage,
                    "reagents_usage": reagents_usage,
                    "measuring_instrument_usage": measuring_instrument_usage,
                    "cause": cause,
                    "capa": capa
                }

                # フォームデータ検証
                valid, error_message = FormValidator.validate_input(form_data)
                if not valid:
                    st.error(error_message)
                else:
                    # データベースにデータを挿入
                    if data_access.insert_qc_data(form_data):
                        st.success("データを登録しました。")
                    else:
                        st.error("データの登録に失敗しました。ログを確認してください。")

    with tab2:
        st.subheader("最近の登録")
        recent_records = data_access.get_recent_records(
            Config.recent_records_limit)
        if not recent_records.empty:
            st.dataframe(recent_records)
        else:
            st.info("最近の登録はありません。")


if __name__ == "__main__":
    main()
