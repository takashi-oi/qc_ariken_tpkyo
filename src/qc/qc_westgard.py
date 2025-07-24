"""
QC Westgardルールモジュール
"""

import streamlit as st

from src.config import Config
from src.database.connection import get_db_connection


class QCWestgard:
    """QC Westgardルールクラス"""

    async def get_westgard_checker(self):
        """データベース接続を持つ MultiRule インスタンスを取得"""
        from src.models.westgard_rules import MultiRule

        async with get_db_connection(Config.DATABASE_PATH) as conn:
            return MultiRule(
                type_conditions={
                    "IC": [{"Type": "sd_conversion", "value": 2.0}],
                    "NC": [{"Type": "sd_conversion", "value": 3.0}],
                    "PC": [{"Type": "sd_conversion", "value": 2.5}],
                },
                db_connection=conn,
            )

    def _handle_specific_error(self, error: Exception) -> None:
        """特定のエラータイプに応じたエラーメッセージを表示"""
        ERROR_MESSAGES = {
            "database": "データベース操作中にエラーが発生しました: {}",
            "data_processing": "データ処理中にエラーが発生しました: {}",
            "io": "入出力処理中にエラーが発生しました: {}",
            "runtime": "実行時エラーが発生しました: {}",
        }

        if isinstance(error, (ValueError, TypeError, AttributeError)):
            st.error(ERROR_MESSAGES["data_processing"].format(error))
        elif isinstance(error, (OSError, IOError)):
            st.error(ERROR_MESSAGES["io"].format(error))
        elif isinstance(error, RuntimeError):
            st.error(ERROR_MESSAGES["runtime"].format(error))
        else:
            st.error(f"予期しないエラーが発生しました: {error}")
