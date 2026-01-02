import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import Config

logger = logging.getLogger(__name__)


class ReagentDatabaseManager:
    """試薬管理システムのデータベース操作を行うクラス"""

    def __init__(self, db_path: str = None):
        """初期化"""
        self.db_path = db_path or Config.REAGENT_DATABASE_PATH
        self.init_db()

    def get_connection(self):
        """データベース接続を取得"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """データベーステーブルの初期化"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 試薬マスタ
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reagent_master (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        group_name TEXT,
                        stock_limit INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # 発注テーブル
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        reagent_id TEXT NOT NULL,
                        order_date DATE NOT NULL,
                        quantity INTEGER NOT NULL,
                        requester TEXT NOT NULL,
                        status TEXT DEFAULT 'ORDERED', -- ORDERED, DELIVERED, CANCELLED
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (reagent_id) REFERENCES reagent_master(id)
                    )
                """
                )

                # 在庫テーブル (Lot単位)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS stock (
                        lot_no TEXT,
                        reagent_id TEXT NOT NULL,
                        expiry_date DATE,
                        current_quantity INTEGER NOT NULL,
                        initial_quantity INTEGER NOT NULL,
                        status TEXT DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED, EMPTY
                        delivery_date DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (lot_no, reagent_id),
                        FOREIGN KEY (reagent_id) REFERENCES reagent_master(id)
                    )
                """
                )

                # 操作ログ
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        action_type TEXT NOT NULL, -- ORDER, DELIVER, USE, DISCARD, UPDATE_MASTER
                        reagent_id TEXT,
                        lot_no TEXT,
                        quantity INTEGER,
                        operator_id TEXT NOT NULL,
                        details TEXT
                    )
                """
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    # --- Master Operations ---
    def get_all_reagents(self, active_only=True):
        query = "SELECT * FROM reagent_master"
        if active_only:
            query += " WHERE is_active = 1"
        with self.get_connection() as conn:
            return pd.read_sql(query, conn)

    def upsert_reagent(self, r_id, name, group, limit, active=True):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO reagent_master (id, name, group_name, stock_limit, is_active)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    group_name=excluded.group_name,
                    stock_limit=excluded.stock_limit,
                    is_active=excluded.is_active
            """,
                (r_id, name, group, limit, 1 if active else 0),
            )
            conn.commit()

    # --- Order Operations ---
    def create_order(self, reagent_id, date, qty, requester):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO orders (reagent_id, order_date, quantity, requester, status)
                VALUES (?, ?, ?, ?, 'ORDERED')
            """,
                (reagent_id, date, qty, requester),
            )
            conn.commit()
            return cursor.lastrowid

    def get_pending_orders(self):
        query = """
            SELECT o.id, o.order_date, r.name as reagent_name, o.quantity, o.requester, o.reagent_id
            FROM orders o
            JOIN reagent_master r ON o.reagent_id = r.id
            WHERE o.status = 'ORDERED'
            ORDER BY o.order_date
        """
        with self.get_connection() as conn:
            return pd.read_sql(query, conn)

    def mark_order_delivered(self, order_id):
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE orders SET status = 'DELIVERED' WHERE id = ?", (order_id,)
            )

    # --- Stock Operations ---
    def add_stock(self, lot_no, reagent_id, expiry, qty, delivery_date):
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO stock (lot_no, reagent_id, expiry_date, current_quantity, initial_quantity, delivery_date, status)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """,
                (lot_no, reagent_id, expiry, qty, qty, delivery_date),
            )

    def get_active_stock(self, reagent_id=None):
        query = """
            SELECT s.*, r.name as reagent_name 
            FROM stock s
            JOIN reagent_master r ON s.reagent_id = r.id
            WHERE s.current_quantity > 0 AND s.status != 'EMPTY'
        """
        params = []
        if reagent_id:
            query += " AND s.reagent_id = ?"
            params.append(reagent_id)

        query += " ORDER BY s.expiry_date ASC"

        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=params)

    def update_stock_quantity(self, lot_no, reagent_id, used_qty):
        """在庫数を更新（使用で減らす）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 現在の在庫を取得
            cursor.execute(
                "SELECT current_quantity FROM stock WHERE lot_no = ? AND reagent_id = ?",
                (lot_no, reagent_id),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("Stock not found")

            current = row[0]
            if current < used_qty:
                raise ValueError("Insufficient stock")

            new_qty = current - used_qty
            status = "ACTIVE"
            if new_qty == 0:
                status = "EMPTY"

            cursor.execute(
                """
                UPDATE stock 
                SET current_quantity = ?, status = ? 
                WHERE lot_no = ? AND reagent_id = ?
            """,
                (new_qty, status, lot_no, reagent_id),
            )
            conn.commit()

    # --- Log Operations ---
    def add_log(self, action, reagent_id, lot_no, qty, operator, details=""):
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO logs (action_type, reagent_id, lot_no, quantity, operator_id, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (action, reagent_id, lot_no, qty, operator, details),
            )

    def get_logs(self, limit=100):
        query = """
            SELECT l.timestamp, l.action_type, r.name as reagent_name, l.lot_no, l.quantity, l.operator_id, l.details
            FROM logs l
            LEFT JOIN reagent_master r ON l.reagent_id = r.id
            ORDER BY l.timestamp DESC
            LIMIT ?
        """
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=(limit,))

    # --- Dashboard Utils ---
    def get_kpi_data(self):
        with self.get_connection() as conn:
            total_stock = (
                conn.execute(
                    "SELECT SUM(current_quantity) FROM stock WHERE status='ACTIVE'"
                ).fetchone()[0]
                or 0
            )

            # 期限切れ（ACTIVEなのに期限過ぎてる）
            expired_sql = "SELECT COUNT(*) FROM stock WHERE status='ACTIVE' AND expiry_date < date('now')"
            expired_count = conn.execute(expired_sql).fetchone()[0]

            # 30日以内
            near_expiry_sql = "SELECT COUNT(*) FROM stock WHERE status='ACTIVE' AND expiry_date >= date('now') AND expiry_date <= date('now', '+30 days')"
            near_expiry_count = conn.execute(near_expiry_sql).fetchone()[0]

            return {
                "total_stock": total_stock,
                "expired_count": expired_count,
                "near_expiry_count": near_expiry_count,
            }
