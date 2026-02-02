"""設定とロギング設定"""

import logging
from logging.handlers import RotatingFileHandler


class Config:
    """設定とロギングを管理するクラス"""

    # データベース設定
    # QCデータ用（DuckDB）
    QC_DATABASE_PATH = "db_folder/qc_data_base.db"
    # マスタデータ用（SQLite3）
    MASTER_DATABASE_PATH = "db_folder/master_data.db"
    # 試薬管理データ用（SQLite3） - マスタデータと統合
    REAGENT_DATABASE_PATH = MASTER_DATABASE_PATH
    # 後方互換性のため（QCデータ用）
    DATABASE_PATH = QC_DATABASE_PATH
    MASTER_FOLDER = "master_folder"
    MAX_RECORDS_PER_TYPE = 10

    # ロギング設定
    LOG_LEVEL = logging.INFO
    LOG_FILE = "qc_check.log"
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    @classmethod
    def setup_logging(cls):
        """高度なロギング設定"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        # コンソール出力用ハンドラ
        console_handler = logging.StreamHandler()
        console_handler.setLevel(cls.LOG_LEVEL)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)

        # ファイル出力用ハンドラ（ローテーション付き）
        file_handler = RotatingFileHandler(
            cls.LOG_FILE, maxBytes=cls.LOG_MAX_BYTES, backupCount=cls.LOG_BACKUP_COUNT
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger


# グローバルロガーを初期化
global_logger = Config.setup_logging()
