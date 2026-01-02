# -*- coding: utf-8 -*-
"""
検査測定状況管理記録登録システム
"""
# ロギング機能を提供するライブラリをインポート
import logging

# データクラスを定義するためのライブラリをインポート
from dataclasses import dataclass

# ファイルパスを操作するためのライブラリをインポート
from pathlib import Path

# 型ヒントを使用するためのライブラリをインポート
from typing import Any, Dict, List, Literal, Optional, Tuple

# DuckDBデータベースを操作するためのライブラリをインポート
import duckdb

# データ分析と操作を行うためのライブラリをインポート
import pandas as pd

# Webアプリケーションを作成するためのライブラリをインポート
import streamlit as st

# マスターデータ読み込みユーティリティをインポート
from src.utils.master_loader import MasterDataLoader

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# アプリケーション設定
st.set_page_config(page_title="精度管理試料測定結果：対応", layout="wide")


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
    _conn: duckdb.DuckDBPyConnection  # _conn 属性を追加

    def __new__(cls, db_path: str):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = db_path
            # データベースディレクトリの存在確認・作成
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            try:
                conn = duckdb.connect(db_path)
                logger.info("データベース接続成功: %s", db_path)
                cls._instance._conn = conn
            except duckdb.Error as e:
                logger.error("データベース接続エラー: %s", e)
                raise
        return cls._instance

    def get_connection(self) -> duckdb.DuckDBPyConnection:
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
    def create_tables(conn: duckdb.DuckDBPyConnection) -> bool:
        """必要なテーブルを作成、成功時True、失敗時Falseを返す"""
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS table_qc_multi_rule (
                    Date_Time TEXT,
                    Batch TEXT,
                    Item_Code TEXT,
                    type TEXT,
                    QC_RESULTS TEXT,
                    Violated_rule TEXT,
                    PRIMARY KEY (Date_Time, Batch, Item_Code, type)
                )
                """
            )
            conn.execute(
                """
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
                )
                """
            )
            conn.commit()
            logger.info("テーブル作成成功")
            return True
        except duckdb.Error as e:
            logger.error("テーブル作成エラー: %s", e)
            return False


class QCDataAccess:
    """データアクセス層"""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self._create_indices()

    def _create_indices(self) -> None:
        """パフォーマンス向上のためのインデックスを作成"""
        try:
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mulch_rule_date_time ON
                                 table_qc_multi_rule (Date_Time)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mulch_rule_item_code ON
                                 table_qc_multi_rule (Item_Code)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mulch_rule_file_name ON
                                 table_qc_multi_rule (File_Name)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status_log_file_name ON
                                 table_qc_status_log (File_Name)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status_log_date_time ON
                                 table_qc_status_log (Date_Time)
                """
            )
            self.conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_act_log_date_time ON
                                 table_qc_act_log (Date_Time)
                """
            )
            self.conn.commit()
            logger.info("インデックス作成成功")
        except duckdb.Error as e:
            logger.warning("インデックス作成エラー: %s", e)

    def get_recent_dates(self, item_code: str, limit: int = 5) -> List[str]:
        """最近の実施日を取得"""
        try:
            result = self.conn.execute(
                """
                SELECT DISTINCT Date_Time
                FROM table_qc_multi_rule
                WHERE Item_Code = ?
                ORDER BY Date_Time DESC
                LIMIT ?
            """,
                (item_code, limit),
            )
            return [row[0] for row in result.fetchall()]
        except duckdb.Error as e:
            logger.error("最近の実施日取得エラー: %s", e)
            return []

    def check_duplicate(
        self, date_time: str, batch: str, item_code: str, type_var: str
    ) -> bool:
        """重複チェック"""
        try:
            result = self.conn.execute(
                """
                SELECT 1 FROM table_qc_status_log
                WHERE Date_Time = ? AND Batch = ? AND Item_Code = ? AND \
                           Type = ?
                LIMIT 1
            """,
                (date_time, batch, item_code, type_var),
            )
            return result.fetchone() is not None
        except duckdb.Error as e:
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
        except (duckdb.Error, pd.errors.DatabaseError) as e:
            logger.error("データ登録エラー: %s", e)
            return False

    def get_violated_rules(self, item_code: Optional[str] = None
                           ) -> pd.DataFrame:
        """違反ルールの取得"""
        try:
            query = """
                SELECT DISTINCT Violated_rule
                FROM table_qc_multi_rule
            """
            params = ()

            if item_code:
                query += " WHERE Item_Code = ?"
                params = (item_code,)

            return pd.read_sql_query(query, self.conn, params=params)
        except duckdb.Error as e:
            logger.error("違反ルール取得エラー: %s", e)
            return pd.DataFrame()

    def get_file_info_records(self, file_name: str) -> pd.DataFrame:
        """指定されたファイル名のtable_qc_file_infoレコードを取得"""
        try:
            query = """
                SELECT Date_Time, Batch, Item_Code, Model, Measurer
                FROM table_qc_file_info
                WHERE File_Name = ?
                ORDER BY Date_Time DESC
            """
            return pd.read_sql_query(query, self.conn, params=(file_name,))
        except duckdb.Error as e:
            logger.error("ファイル情報取得エラー: %s", e)
            return pd.DataFrame()

    def get_file_data_batch(
        self, file_name: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """ファイル名に基づいて3つのテーブルからデータを一括取得"""
        try:
            # table_qc_status_logからデータ抽出
            query_status = """
                SELECT Date_Time, Item_Code, Batch, standard_usage,
                       control_usage, reagents_usage,
                       measuring_instrument_usage
                FROM table_qc_status_log
                WHERE File_Name = ?
                ORDER BY Date_Time DESC
            """
            status_log_df = pd.read_sql_query(
                query_status, self.conn, params=(file_name,)
            )

            # table_qc_file_infoからデータ抽出
            file_info_df = self.get_file_info_records(file_name)

            # QCマルチルール情報の取得
            query_multi_rule = """
                SELECT Judgment, Error_type, Type_error, Violated_rule,
                       Type, Dye, Ct, SD_Conversion, Lot_Number
                FROM table_qc_multi_rule
                WHERE File_Name = ?
                ORDER BY Date_Time DESC
            """
            multi_rule_df = pd.read_sql_query(
                query_multi_rule, self.conn, params=(file_name,)
            )

            return status_log_df, file_info_df, multi_rule_df
        except duckdb.Error as e:
            logger.error("バッチデータ取得エラー: %s", e)
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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
        except duckdb.Error as e:
            logger.error("最近の記録取得エラー: %s", e)
            return pd.DataFrame()

    def check_duplicate_qc_act_log(self, file_name, employee, qc_type):
        """table_qc_act_logの重複チェックを行う"""
        try:
            result = self.conn.execute(
                "SELECT 1 FROM table_qc_act_log "
                "WHERE File_Name = ? AND Measurer = ? AND Type = ? LIMIT 1",
                (file_name, employee, qc_type),
            )
            return result.fetchone() is not None
        except duckdb.Error as e:
            logger.error("CAPA重複チェックエラー: %s", e)
            return False

    def insert_qc_act_log(self, file_name, employee, qc_type, cause, capa):
        try:
            self.conn.execute(
                "INSERT INTO table_qc_act_log (File_Name, Measurer, \
                    Type, Cause, CAPA) "
                "VALUES (?, ?, ?, ?, ?)",
                (file_name, employee, qc_type, cause, capa),
            )
            self.conn.commit()
            return True
        except duckdb.Error as e:
            logger.error("CAPA登録エラー: %s", e)
            return False


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

    # カラム名の確認とフォールバック処理
    if employee_df.empty:
        measurer_list = [""]
        st.sidebar.warning("担当者マスターデータがありません。マスターテーブル管理ページでデータを登録してください。")
    elif "Member's_Name" in employee_df.columns:
        measurer_list = [""] + employee_df["Member's_Name"].dropna().tolist()
    else:
        # 代替カラム名を探す
        name_col = None
        for col in employee_df.columns:
            if "Name" in col or "名前" in col or "氏名" in col:
                name_col = col
                break

        if name_col:
            measurer_list = [""] + employee_df[name_col].dropna().tolist()
        else:
            measurer_list = [""]
            st.sidebar.warning("担当者名のカラムが見つかりません。マスターテーブル管理ページでデータを確認してください。")

    st.sidebar.selectbox(
        "担当者を選択",
        options=measurer_list,
        key="sidebar_implementor",
    )

    # サイドバーに直近で読み込んだファイル名5件をセレクトボックスで表示
    @st.cache_data(ttl=300)  # 5分間キャッシュ
    def get_file_name_options(_conn: duckdb.DuckDBPyConnection) -> List[str]:
        """ファイル名リストを取得（キャッシュ付き）"""
        try:
            query = (
                "SELECT DISTINCT File_Name "
                "FROM table_qc_file_info "
                "ORDER BY Date_Time DESC "
                "LIMIT 5"
            )
            file_name_df = pd.read_sql_query(query, _conn)
            if not file_name_df.empty:
                return file_name_df["File_Name"].tolist()
            return []
        except (
            duckdb.Error,
            pd.errors.DatabaseError,
            FileNotFoundError,
        ) as e:
            logger.error("ファイル名の取得エラー: %s", e)
            return []

    # データベース接続を先に取得
    try:
        db_manager = DatabaseManager(Config.db_path)
        conn = db_manager.get_connection()
    except (duckdb.Error, FileNotFoundError) as e:
        st.error(f"データベース接続エラー: {e}")
        logger.error("データベース接続エラー: %s", e)
        return

    file_name_options = get_file_name_options(conn)
    if not file_name_options:
        st.sidebar.warning("ファイル名の取得に失敗しました。")

    def file_name_format(x):
        return x if x in file_name_options else "Unknown"

    st.sidebar.selectbox(
        "測定ファイル名を選択して下さい",
        file_name_options,
        format_func=file_name_format,
        key="sidebar_file_name",
    )
    # サイドバーに「表示」ボタンを追加
    if st.sidebar.button("表示", key="show_status_log"):
        st.session_state.show_data = True

    # ファイル選択が変更された場合、データ表示をリセット
    current_file = st.session_state.get("sidebar_file_name", None)
    if "previous_file" not in st.session_state:
        st.session_state.previous_file = current_file
    elif st.session_state.previous_file != current_file:
        st.session_state.show_data = False
        st.session_state.previous_file = current_file

    # セッション状態で表示フラグを管理
    show_status_log = st.session_state.get("show_data", False)

    # アプリケーション設定
    st.markdown(f"### {Config.page_title}")

    # データベース初期化（接続は既に取得済み）
    try:
        initializer = DatabaseInitializer()
        if not initializer.create_tables(conn):
            st.error("データベースの初期化に失敗しました。ログを確認してください。")
            return

        data_access = QCDataAccess(conn)
    except (duckdb.Error, FileNotFoundError) as e:
        st.error(f"データベースの初期化エラー: {e}")
        logger.error("データベースの初期化エラー: %s", e)
        return

    # マスターデータ読み込み
    measurement_df = MasterDataLoader.load_measurement_items()
    employee_df = MasterDataLoader.load_employee_data()

    if measurement_df[0].empty:
        st.warning("検査項目マスターの読み込みに失敗しました。")
    if employee_df.empty:
        st.warning("従業員マスターの読み込みに失敗しました。")

    # --- データ表示部（測定情報・検査実施状況・QCマルチルール情報）ここまで ---

    # データ取得用の変数を初期化
    status_log_df = pd.DataFrame()
    file_info_df = pd.DataFrame()
    multi_rule_df = pd.DataFrame()

    if show_status_log:
        selected_file_name = st.session_state.get("sidebar_file_name", None)
        if selected_file_name:
            try:
                # バッチでデータを一括取得（パフォーマンス向上）
                (
                    status_log_df,
                    file_info_df,
                    multi_rule_df,
                ) = data_access.get_file_data_batch(selected_file_name)

                # --- 測定情報 ---
                if not file_info_df.empty:
                    st.subheader("測定情報")
                    display_file_info = file_info_df.copy()
                    display_file_info.columns = [
                        "日時",
                        "バッチ",
                        "項目コード",
                        "モデル",
                        "測定者",
                    ]
                    st.dataframe(display_file_info, hide_index=True)
                else:
                    st.info("該当ファイルのファイル情報はありません。")

                # --- 検査実施状況 ---
                if not status_log_df.empty:
                    st.subheader("検査実施状況")
                    columns_to_show = [
                        "Date_Time",
                        "Item_Code",
                        "Batch",
                        "standard_usage",
                        "control_usage",
                        "reagents_usage",
                        "measuring_instrument_usage",
                    ]
                    available_cols = [
                        col for col in columns_to_show if
                        col in status_log_df.columns
                    ]
                    display_status_log = status_log_df[available_cols]
                    display_status_log.columns = [
                        "日時",
                        "項目コード",
                        "バッチ",
                        "標準物質使用状況",
                        "管理試料使用状況",
                        "測定試薬使用状況",
                        "測定機器使用状況",
                    ][: len(display_status_log.columns)]
                    st.dataframe(display_status_log, hide_index=True)
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
                        "Judgment",
                        "Error_type",
                        "Type_error",
                        "Violated_rule",
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
                    display_multi_rule = filtered_multi_rule_df[available_cols]
                    jp_columns = [
                        "判定",
                        "誤差タイプ",
                        "エラータイプ",
                        "違反ルール",
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
                        st.dataframe(display_multi_rule, hide_index=True)
                    else:
                        st.info("該当するデータがありません。")
                else:
                    msg = "該当ファイルのQCマルチルール情報はありません。"
                    st.info(msg)

                # --- 品質管理法セクション ---
                st.subheader("品質管理法")

                # QCマルチルール情報からTypeの値を取得
                type_options = ["違反したマルチルールを選択してください"]
                if "Type" in multi_rule_df.columns:
                    unique_types = multi_rule_df["Type"].dropna().unique(
                        ).tolist()
                    type_options.extend(unique_types)

                qc_type = st.selectbox("タイプ", type_options)

                cause = st.text_area("Cause（原因と推測されること）")
                capa = st.text_area("CAPA（是正処置・予防処置）")

                if st.button("CAPAを登録"):
                    # データベースのtable_qc_act_logに重複をチェック
                    duplicate_check = data_access.check_duplicate_qc_act_log(
                        selected_file_name,
                        st.session_state.get("sidebar_implementor", ""),
                        qc_type,
                    )
                    if not duplicate_check:
                        # 重複がなければCAPAを登録
                        data_access.insert_qc_act_log(
                            selected_file_name,
                            st.session_state.get("sidebar_implementor", ""),
                            qc_type,
                            cause,
                            capa,
                        )
                        st.success("CAPAが正常に登録されました。")
                    else:
                        st.error("同じ条件のCAPAが既に登録されています。")

            except (
                duckdb.Error,
                pd.errors.DatabaseError,
                FileNotFoundError,
            ) as e:
                err_msg = f"データの取得に失敗しました: {e}"
                st.error(err_msg)


if __name__ == "__main__":
    main()
