"""
マスターデータ読み込みユーティリティ
データベースからマスターデータを読み込む共通モジュール
SQLite3を使用してマスターデータを管理
"""

import sqlite3
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from src.config import Config
from src.config import global_logger as logger

# データベース設定（SQLite3）
DB_PATH = Config.MASTER_DATABASE_PATH

# マスターテーブル名
MASTER_TABLES = {
    "measurement_item": "master_measurement_item",
    "measuring_model": "master_measuring_model",
    "employee_code": "master_employee_code",
    "qc_control": "master_qc_control",
}


class MasterDataLoader:
    """マスターデータ読み込みクラス（データベースから読み込み）"""

    _cache: Dict[str, pd.DataFrame] = {}
    _item_mapping_cache: Optional[Dict[str, str]] = None

    @classmethod
    def _get_connection(cls) -> sqlite3.Connection:
        """データベース接続を取得（SQLite3）"""
        db_path = Path(DB_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能にする
        return conn

    @classmethod
    def load_measurement_items(
        cls, force_reload: bool = False
    ) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """検査項目マスターの読み込み

        Returns:
            Tuple[pd.DataFrame, Dict[str, str]]: (データフレーム, 項目コード→項目名のマッピング)
        """
        cache_key = "measurement_item"

        if cache_key in cls._cache and not force_reload:
            df = cls._cache[cache_key]
        else:
            try:
                conn = cls._get_connection()
                table_name = MASTER_TABLES["measurement_item"]

                # テーブルが存在するか確認
                try:
                    query = f"SELECT * FROM {table_name}"
                    df = pd.read_sql_query(query, conn)

                    # 列名の正規化（日本語列名を英語列名に変換）
                    column_mapping = {
                        "項目コード": "Item_Code",
                        "測定項目": "Measurement_Item",
                    }
                    for old_col, new_col in column_mapping.items():
                        if old_col in df.columns and new_col not in df.columns:
                            df.rename(columns={old_col: new_col}, inplace=True)

                    # Item_CodeとMeasurement_Itemが存在することを確認
                    if "Item_Code" not in df.columns:
                        # 代替列名を探す
                        for col in df.columns:
                            if "コード" in col or "Code" in col:
                                df.rename(columns={col: "Item_Code"}, inplace=True)
                                break

                    if "Measurement_Item" not in df.columns:
                        # 代替列名を探す
                        for col in df.columns:
                            if "項目" in col or "Item" in col:
                                if col != "Item_Code":
                                    df.rename(
                                        columns={col: "Measurement_Item"},
                                        inplace=True,
                                    )
                                    break

                    cls._cache[cache_key] = df
                    logger.info("検査項目マスター読み込み成功（DB）: %d件", len(df))
                except Exception as e:
                    logger.warning("データベースからの読み込みに失敗: %s", e)
                    df = pd.DataFrame()

                conn.close()
            except Exception as e:
                logger.error("検査項目マスターの読み込みエラー: %s", e)
                df = pd.DataFrame()

        # マッピング辞書を作成
        if (
            not df.empty
            and "Item_Code" in df.columns
            and "Measurement_Item" in df.columns
        ):
            item_mapping = dict(zip(df["Item_Code"], df["Measurement_Item"]))
            return df, item_mapping
        else:
            logger.warning("検査項目マスターのデータが空または列が不足しています")
            return df, {}

    @classmethod
    def load_employee_data(cls, force_reload: bool = False) -> pd.DataFrame:
        """検査要員マスタの読み込み

        Returns:
            pd.DataFrame: 従業員データフレーム
        """
        cache_key = "employee_code"

        if cache_key in cls._cache and not force_reload:
            return cls._cache[cache_key]

        try:
            conn = cls._get_connection()
            table_name = MASTER_TABLES["employee_code"]

            try:
                query = f"SELECT * FROM {table_name}"
                df = pd.read_sql_query(query, conn)

                # 列名の正規化
                if "Member's_Name" not in df.columns:
                    # 代替列名を探す
                    for col in df.columns:
                        if "Name" in col or "名前" in col or "氏名" in col:
                            df.rename(columns={col: "Member's_Name"}, inplace=True)
                            break

                cls._cache[cache_key] = df
                logger.info("検査要員マスタ読み込み成功（DB）: %d件", len(df))
            except Exception as e:
                logger.warning("データベースからの読み込みに失敗: %s", e)
                df = pd.DataFrame()

            conn.close()
            return df
        except Exception as e:
            logger.error("検査要員マスタの読み込みエラー: %s", e)
            return pd.DataFrame()

    @classmethod
    def load_measuring_model(cls, force_reload: bool = False) -> pd.DataFrame:
        """測定機器マスタの読み込み

        Returns:
            pd.DataFrame: 測定機器データフレーム
        """
        cache_key = "measuring_model"

        if cache_key in cls._cache and not force_reload:
            return cls._cache[cache_key]

        try:
            conn = cls._get_connection()
            table_name = MASTER_TABLES["measuring_model"]

            try:
                query = f"SELECT * FROM {table_name}"
                df = pd.read_sql_query(query, conn)
                cls._cache[cache_key] = df
                logger.info("測定機器マスタ読み込み成功（DB）: %d件", len(df))
            except Exception as e:
                logger.warning("データベースからの読み込みに失敗: %s", e)
                df = pd.DataFrame()

            conn.close()
            return df
        except Exception as e:
            logger.error("測定機器マスタの読み込みエラー: %s", e)
            return pd.DataFrame()

    @classmethod
    def load_qc_control(cls, force_reload: bool = False) -> pd.DataFrame:
        """QC Controlマスタの読み込み

        Returns:
            pd.DataFrame: QC Controlデータフレーム
        """
        cache_key = "qc_control"

        if cache_key in cls._cache and not force_reload:
            return cls._cache[cache_key]

        try:
            conn = cls._get_connection()
            table_name = MASTER_TABLES["qc_control"]

            try:
                query = f"SELECT * FROM {table_name}"
                df = pd.read_sql_query(query, conn)
                cls._cache[cache_key] = df
                logger.info("QC Controlマスタ読み込み成功（DB）: %d件", len(df))
            except Exception as e:
                logger.warning("データベースからの読み込みに失敗: %s", e)
                df = pd.DataFrame()

            conn.close()
            return df
        except Exception as e:
            logger.error("QC Controlマスタの読み込みエラー: %s", e)
            return pd.DataFrame()

    @classmethod
    def clear_cache(cls):
        """キャッシュをクリア"""
        cls._cache.clear()
        cls._item_mapping_cache = None
        logger.info("マスターデータキャッシュをクリアしました")
