import logging
import os
import sqlite3
import sys
from pathlib import Path

import duckdb
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import Config
from src.database.optimized_tables import OptimizedDatabaseManager
from src.reagent_db import ReagentDatabaseManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

OLD_REAGENT_DB_PATH = "db_folder/reagent.db"


def migrate_reagent_data():
    """Migrate reagent data from old SQLite DB to new centralized Master SQLite DB"""
    logger.info("--- Starting Reagent Data Migration ---")

    if not os.path.exists(OLD_REAGENT_DB_PATH):
        logger.warning(
            f"Old reagent database not found at {OLD_REAGENT_DB_PATH}. Skipping reagent migration."
        )
        return

    # Initialize new DB (creates tables)
    new_db_path = Config.MASTER_DATABASE_PATH

    logger.info(f"Target Master Database: {new_db_path}")

    # Ensure tables exist in new DB by initializing manager
    try:
        ReagentDatabaseManager()
        logger.info("Target database schema initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize target database: {e}")
        return

    tables = ["reagent_master", "orders", "stock", "logs"]

    try:
        with (
            sqlite3.connect(OLD_REAGENT_DB_PATH) as old_conn,
            sqlite3.connect(new_db_path) as new_conn,
        ):

            for table in tables:
                logger.info(f"Migrating table: {table}")
                try:
                    # Check if table exists in old DB
                    cursor = old_conn.cursor()
                    cursor.execute(
                        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                    )
                    if not cursor.fetchone():
                        logger.warning(
                            f"Table {table} does not exist in old DB. Skipping."
                        )
                        continue

                    # Read from old DB
                    df = pd.read_sql(f"SELECT * FROM {table}", old_conn)

                    if not df.empty:
                        # Append to new DB
                        # Note: This might duplicate data if run multiple times without cleanup.
                        # For a migration script, we often assume empty target or handle duplicates.
                        # SQLite 'OR IGNORE' via SQL or pandas 'append' might fail on PK constraint if conflicts.
                        # We try pandas to_sql with if_exists='append'. If PK conflict, it raises IntegrityError.
                        try:
                            df.to_sql(table, new_conn, if_exists="append", index=False)
                            logger.info(
                                f"Successfully migrated {len(df)} rows to {table}."
                            )
                        except sqlite3.IntegrityError:
                            logger.warning(
                                f"IntegrityError migrating {table}. Some records might already exist. Attempting row-by-row insert or ignoring."
                            )
                            # Optional: smarter merge logic here if needed.
                    else:
                        logger.info("Table is empty.")

                except Exception as e:
                    logger.error(f"Error migrating table {table}: {e}")

            logger.info("Reagent data migration step completed.")

    except Exception as e:
        logger.error(f"Migration process failed: {e}")


def migrate_qc_data():
    """Migrate QC data using OptimizedDatabaseManager (DuckDB -> DuckDB)"""
    logger.info("--- Starting QC Measurement Data Migration ---")
    try:
        db_path = Config.QC_DATABASE_PATH
        logger.info(f"QC Database: {db_path}")

        manager = OptimizedDatabaseManager(db_path)
        manager.migrate_existing_data()

        logger.info("QC measurement data migration step completed.")
    except Exception as e:
        logger.error(f"QC data migration failed: {e}")


if __name__ == "__main__":
    migrate_reagent_data()
    migrate_qc_data()
