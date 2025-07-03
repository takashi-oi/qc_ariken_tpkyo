"""
検査測定状況管理記録登録システム
"""

# ロギング機能を提供するライブラリをインポート
import logging

# SQLiteデータベースを操作するためのライブラリをインポート
import sqlite3

# データクラスを定義するためのライブラリをインポート
from dataclasses import dataclass

# ファイルパスを操作するためのライブラリをインポート
from pathlib import Path

# 型ヒントを使用するためのライブラリをインポート
from typing import Any, Dict, List, Literal, Optional, Tuple

# データ分析と操作を行うためのライブラリをインポート
import pandas as pd

# Webアプリケーションを作成するためのライブラリをインポート
import streamlit as st

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# アプリケーション設定
st.set_page_config(page_title="QC判定対応記録登録", layout="wide")


@dataclass
class Config:
    """アプリケーション設定"""

    db_path: str = "db_folder/qc_data_base.db"
    employee_master: str = "data/master/employee_code.xlsx"
    measurement_master: str = "data/master/measurement_item.xlsx"
    page_title: str = "QC判定対応記録登録"
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
        if hasattr(self, "_conn") and self._conn:
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
            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS qc_multi_rule (
                    Date_Time TEXT,
                    Batch TEXT,
                    Item_Code TEXT,
                    type TEXT,
                    QC_RESULTS TEXT,
                    Violated_rule TEXT,
                    PRIMARY KEY (Date_Time, Batch, Item_Code, type)
                );

                CREATE TABLE IF NOT EXISTS table_qc_status_log (
                    Date_Time TEXT,
                    Measurer TEXT,
                    Item_Code TEXT,
                    Batch TEXT,
                    standard_usage TEXT,
                    control_usage TEXT,
                    reagents_usage TEXT,
                    measuring_instrument_usage TEXT,
                    Type TEXT,
                    File_Name TEXT
                );
            """
            )
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
            cursor.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_mulch_rule_date_time ON
                                 qc_multi_rule (Date_Time);
                CREATE INDEX IF NOT EXISTS idx_mulch_rule_item_code ON
                                 qc_multi_rule (Item_Code);
                CREATE INDEX IF NOT EXISTS idx_act_log_date_time ON
                                 table_qc_act_log (Date_Time);
            """
            )
            self.conn.commit()
            logger.info("インデックス作成成功")
        except sqlite3.Error as e:
            logger.warning("インデックス作成エラー: %s", e)

    def get_recent_dates(self, item_code: str, limit: int = 5) -> List[str]:
        """最近の実施日を取得"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT Date_Time
                FROM qc_multi_rule
                WHERE Item_Code = ?
                ORDER BY Date_Time DESC
                LIMIT ?
            """,
                (item_code, limit),
            )
            return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error("最近の実施日取得エラー: %s", e)
            return []

    def check_duplicate(
        self, date_time: str, batch: str, item_code: str, type_var: str
    ) -> bool:
        """重複チェック"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT 1 FROM table_qc_status_log
                WHERE Date_Time = ? AND Batch = ? AND Item_Code = ? AND \
                           Type = ?
                LIMIT 1
            """,
                (date_time, batch, item_code, type_var),
            )
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
                "Type": data["type_variable"],
                "Measurer": data.get("implementor", ""),
                "standard_usage": data.get("standard_usage", ""),
                "control_usage": data.get("control_usage", ""),
                "reagents_usage": data.get("reagents_usage", ""),
                "measuring_instrument_usage": data.get(
                    "measuring_instrument_usage", ""
                ),
                "File_Name": data.get("file_name", ""),
            }

            # 重複チェック
            if self.check_duplicate(
                formatted_data["Date_Time"],
                formatted_data["Batch"],
                formatted_data["Item_Code"],
                formatted_data["Type"],
            ):
                logger.warning("重複データが存在します")
                return False

            # DataFrameに変換して挿入
            df = pd.DataFrame([formatted_data])
            with self.conn:
                df.to_sql(
                    "table_qc_status_log",
                    con=self.conn,
                    if_exists="append",
                    index=False,
                    method="multi",
                )
            logger.info("1件のデータを登録しました")
            return True
        except (sqlite3.Error, pd.errors.DatabaseError) as e:
            logger.error("データ登録エラー: %s", e)
            return False

    def get_violated_rules(self, item_code: Optional[str] = None) -> pd.DataFrame:
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

    def get_file_info_records(self, file_name: str) -> pd.DataFrame:
        """指定されたファイル名のtable_qc_file_infoレコードを取得"""
        try:
            query = """
                SELECT * FROM table_qc_file_info
                WHERE File_Name = ?
                ORDER BY Date_Time DESC
            """
            return pd.read_sql_query(query, self.conn, params=(file_name,))
        except sqlite3.Error as e:
            logger.error("ファイル情報取得エラー: %s", e)
            return pd.DataFrame()

    def get_recent_records(self, limit: int = 5) -> pd.DataFrame:
        """最近の記録を取得"""
        try:
            # table_qc_status_logとtable_qc_multi_ruleからデータを結合して取得
            query = """
                SELECT
                    s.Date_Time,
                    s.Batch,
                    s.Item_Code,
                    s.Type,
                    s.Measurer,
                    m.Violated_rule
                FROM table_qc_status_log s
                LEFT JOIN table_qc_multi_rule m
                    ON s.Date_Time = m.Date_Time
                    AND s.Batch = m.Batch
                    AND s.Item_Code = m.Item_Code
                ORDER BY s.Date_Time DESC
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
    def load_measurement_items(
        cls, force_reload: bool = False
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
            df.rename(
                columns={"項目コード": "Item_Code", "測定項目": "Measurement_Item"},
                inplace=True,
            )
            item_mapping = dict(zip(df["Item_Code"], df["Measurement_Item"]))
            cls._measurement_items_cache = (df, item_mapping)
            logger.info("検査項目マスター読み込み成功: %d件", len(df))
            return cls._measurement_items_cache
        except (
            FileNotFoundError,
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
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
                logger.error("検査要員マスタファイルが存在しません: %s", file_path)
                return pd.DataFrame()

            cls._employee_data_cache = pd.read_excel(file_path)
            logger.info(
                "検査要員マスタ読み込み成功: %d件", len(cls._employee_data_cache)
            )
            return cls._employee_data_cache
        except (
            FileNotFoundError,
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
        ) as e:
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
            "Violated_rule": "違反ルール",
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
            key="sidebar_implementor",
        )
    else:
        st.sidebar.error("従業員マスターの読み込みに失敗しました。")

    # サイドバーに直近で読み込んだファイル名5件をセレクトボックスで表示
    file_name_options = []
    try:
        conn = sqlite3.connect(Config.db_path)
        query = (
            "SELECT DISTINCT File_Name "
            "FROM table_qc_file_info "
            "ORDER BY Date_Time DESC "
            "LIMIT 5"
        )
        file_name_df = pd.read_sql_query(query, conn)
        file_name_options = (
            file_name_df["File_Name"].tolist() if not file_name_df.empty else []
        )
        conn.close()
    except (sqlite3.Error, pd.errors.DatabaseError, FileNotFoundError) as e:
        st.sidebar.warning(f"ファイル名の取得に失敗しました: {e}")

    def file_name_format(x):
        return x if x in file_name_options else "Unknown"

    st.sidebar.selectbox(
        "測定ファイル名を選択して下さい",
        file_name_options,
        format_func=file_name_format,
        key="sidebar_file_name",
    )
    # サイドバーに「表示」ボタンを追加
    show_status_log = st.sidebar.button("表示", key="show_status_log")

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

    # --- データ表示部（測定情報・検査実施状況・QCマルチルール情報）ここまで ---

    if show_status_log:
        selected_file_name = st.session_state.get("sidebar_file_name", None)
        if selected_file_name:
            try:
                # table_qc_status_logからデータ抽出
                conn = sqlite3.connect(Config.db_path)
                query = (
                    "SELECT * FROM table_qc_status_log "
                    "WHERE File_Name = ? "
                    "ORDER BY Date_Time DESC"
                )
                status_log_df = pd.read_sql_query(
                    query, conn, params=(selected_file_name,)
                )

                # table_qc_file_infoからデータ抽出
                file_info_df = data_access.get_file_info_records(selected_file_name)

                # QCマルチルール情報の表示
                query_multi_rule = (
                    "SELECT * FROM table_qc_multi_rule "
                    "WHERE File_Name = ? "
                    "ORDER BY Date_Time DESC"
                )
                multi_rule_df = pd.read_sql_query(
                    query_multi_rule, conn, params=(selected_file_name,)
                )
                conn.close()

                # --- 測定情報 ---
                if not file_info_df.empty:
                    st.subheader("測定情報")
                    display_file_info = file_info_df.copy()
                    if len(display_file_info.columns) >= 6:
                        display_file_info = display_file_info.iloc[:, 1:6]
                        display_file_info.columns = [
                            "日時",
                            "バッチ",
                            "項目コード",
                            "モデル",
                            "測定者",
                        ]
                    else:
                        st.write("実際の列名:", list(display_file_info.columns))
                    st.dataframe(display_file_info)
                else:
                    st.info("該当ファイルのファイル情報はありません。")

                # --- 検査実施状況 ---
                if not status_log_df.empty:
                    st.subheader("検査実施状況")
                    columns_to_show = [
                        "Date_Time",
                        "Measurer",
                        "Item_Code",
                        "Batch",
                        "standard_usage",
                        "control_usage",
                        "reagents_usage",
                        "measuring_instrument_usage",
                    ]
                    available_cols = [
                        col for col in columns_to_show if col in status_log_df.columns
                    ]
                    display_status_log = status_log_df[available_cols].copy()
                    display_status_log.columns = [
                        "日時",
                        "担当者",
                        "項目コード",
                        "バッチ",
                        "標準物質使用状況",
                        "管理試料使用状況",
                        "測定試薬使用状況",
                        "測定機器使用状況",
                    ][: len(display_status_log.columns)]
                    st.dataframe(display_status_log)
                else:
                    st.info("該当ファイルのステータスログはありません。")

                # --- QCマルチルール情報 ---
                if not multi_rule_df.empty:
                    st.subheader("QCマルチルール情報")
                    # 誤差タイプが「-」以外のレコードのみ抽出
                    if "Error_type" in multi_rule_df.columns:
                        filtered_multi_rule_df = multi_rule_df[
                            multi_rule_df["Error_type"]
                            .astype(str)
                            .apply(lambda x: x.strip())
                            != "-"
                        ]
                    else:
                        filtered_multi_rule_df = multi_rule_df.copy()

                    columns_to_show = [
                        "Item_Code",
                        "Batch",
                        "Model",
                        "Date_Time",
                        "Judgment",
                        "Error_type",
                        "Type_error",
                        "Violated_rule",
                        "measurer",
                        "Type",
                        "Dye",
                        "Ct",
                        "SD_Conversion",
                        "Lot_Number",
                    ]
                    available_cols = []
                    for col in columns_to_show:
                        if col in filtered_multi_rule_df.columns:
                            available_cols.append(col)
                    display_multi_rule = filtered_multi_rule_df[available_cols].copy()
                    jp_columns = [
                        "項目コード",
                        "バッチ",
                        "機種",
                        "日時",
                        "判定",
                        "誤差タイプ",
                        "エラータイプ",
                        "違反ルール",
                        "測定者",
                        "タイプ",
                        "Dye",
                        "Ct値",
                        "SD換算",
                        "Lot番号",
                    ]
                    display_multi_rule.columns = jp_columns[
                        : len(display_multi_rule.columns)
                    ]
                    if not display_multi_rule.empty:
                        st.dataframe(display_multi_rule)
                    else:
                        st.info("該当するデータがありません。")
                else:
                    msg = "該当ファイルのQCマルチルール情報はありません。"
                    st.info(msg)
            except (sqlite3.Error, pd.errors.DatabaseError, FileNotFoundError) as e:
                err_msg = f"データの取得に失敗しました: {e}"
                st.error(err_msg)

        st.subheader("品質管理法")
        qc_type = st.selectbox("タイプ", ["QCマルチルール情報のタイトル"])

        st.text_area("Cause")


if __name__ == "__main__":
    main()
