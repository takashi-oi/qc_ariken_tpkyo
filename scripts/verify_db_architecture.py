import asyncio
import logging
import sys
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import Config
from src.database.connection import get_db_connection
from src.database.optimized_queries import OptimizedQueryManager
from src.reagent_db import ReagentDatabaseManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def verify_master_db():
    logger.info("--- Verifying Master Data Database (SQLite) ---")
    try:
        db_path = Config.MASTER_DATABASE_PATH
        logger.info(f"Connecting to {db_path}...")

        manager = (
            ReagentDatabaseManager()
        )  # Uses Config.REAGENT_DATABASE_PATH -> MASTER_DATABASE_PATH

        # Check tables
        with manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            logger.info(f"Tables found: {tables}")

            required = ["reagent_master", "orders", "stock", "logs"]
            missing = [t for t in required if t not in tables]
            if missing:
                logger.error(f"Missing reagent tables: {missing}")
            else:
                logger.info("All reagent tables present.")

    except Exception as e:
        logger.error(f"Master DB verification failed: {e}")


async def verify_qc_db():
    logger.info("--- Verifying QC Data Database (DuckDB) ---")
    try:
        db_path = Config.QC_DATABASE_PATH
        logger.info(f"Connecting to {db_path}...")

        # Test OptimizedQueryManager
        # Note: OptimizedQueryManager creates its own connection.
        # Ensure it works.
        query_manager = OptimizedQueryManager(db_path)
        stats = query_manager.get_performance_metrics()
        logger.info(f"DB Performance Metrics: {stats}")

        # Test raw connection via get_db_connection
        async with get_db_connection(db_path) as conn:
            # Check for tables
            df = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'qc_%'"
            ).df()
            tables = df["table_name"].tolist()
            logger.info(f"QC Optimized Tables found: {tables}")

            required = [
                "qc_file_info",
                "qc_measurements",
                "qc_activity_log",
                "qc_westgard_results",
            ]
            missing = [t for t in required if t not in tables]
            if missing:
                logger.error(f"Missing QC tables: {missing}")
            else:
                logger.info("All QC tables present.")

    except Exception as e:
        logger.error(f"QC DB verification failed: {e}")


if __name__ == "__main__":
    verify_master_db()
    asyncio.run(verify_qc_db())
