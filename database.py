"""
Apt Price Tracker - SQLite Database Management (WAL Mode & Concurrency Safe)
"""
import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import DB_PATH, DEFAULT_COMPLEXES


def get_connection():
    """Get a database connection with WAL mode and long busy timeout."""
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
    except Exception:
        pass
    return conn


def init_db():
    """Initialize database tables and default watchlist if empty."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Watchlist Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complex_name TEXT NOT NULL UNIQUE,
                region_code TEXT NOT NULL,
                region_name TEXT NOT NULL,
                dong TEXT,
                build_year INTEGER,
                total_households INTEGER,
                target_area_sqm REAL,
                memo TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complex_name TEXT NOT NULL,
                region_code TEXT,
                region_name TEXT,
                dong TEXT,
                deal_year INTEGER NOT NULL,
                deal_month INTEGER NOT NULL,
                deal_day INTEGER NOT NULL,
                deal_date TEXT NOT NULL,
                deal_amount INTEGER NOT NULL,  -- 만원 단위
                exclusive_area REAL NOT NULL,   -- 전용면적 ㎡
                floor INTEGER,
                build_year INTEGER,
                cancel_deal_type TEXT,
                is_cancel INTEGER DEFAULT 0,
                req_gbn TEXT DEFAULT '중개거래',
                rdealer_lawdnm TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(deal_date, complex_name, exclusive_area, floor, deal_amount)
            )
        """)
        
        # Schema migration check for req_gbn and rdealer_lawdnm
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN req_gbn TEXT DEFAULT '중개거래'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN rdealer_lawdnm TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Price Alerts / Highlights Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complex_name TEXT NOT NULL,
                alert_type TEXT NOT NULL,  -- '신고가', '하락거래', '거래급증', '관심단지_신규거래'
                message TEXT NOT NULL,
                deal_date TEXT NOT NULL,
                deal_amount INTEGER NOT NULL,
                exclusive_area REAL NOT NULL,
                floor INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        
        # Seed watchlist if empty, or update region_code
        cursor.execute("SELECT COUNT(*) FROM watchlist")
        if cursor.fetchone()[0] == 0:
            for item in DEFAULT_COMPLEXES:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO watchlist 
                    (complex_name, region_code, region_name, dong, build_year, total_households, memo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["name"],
                        item["region_code"],
                        item["region_name"],
                        item["dong"],
                        item["build_year"],
                        item["total_households"],
                        "기본 프리셋 관심 단지"
                    )
                )
        else:
            # 기존 DB에 남아있는 구형 코드(41590) 갱신
            for item in DEFAULT_COMPLEXES:
                cursor.execute(
                    "UPDATE watchlist SET region_code = ? WHERE complex_name = ?",
                    (item["region_code"], item["name"])
                )
        conn.commit()


def get_watchlist() -> List[Dict[str, Any]]:
    """Retrieve all watchlist complexes."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watchlist ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def add_to_watchlist(complex_name: str, region_code: str, region_name: str, dong: str = "", build_year: int = 0, total_households: int = 0, memo: str = "") -> bool:
    """Add a new complex to the watchlist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO watchlist (complex_name, region_code, region_name, dong, build_year, total_households, memo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (complex_name.strip(), region_code, region_name, dong, build_year, total_households, memo))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def remove_from_watchlist(complex_id: int) -> bool:
    """Remove a complex from the watchlist by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE id = ?", (complex_id,))
        conn.commit()
        return cursor.rowcount > 0


def insert_transactions(transactions: List[Dict[str, Any]]) -> int:
    """Batch insert transactions safely and return count of inserted rows."""
    if not transactions:
        return 0
    
    inserted_count = 0
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for tx in transactions:
                try:
                    c_name = tx.get("complex_name", "")
                    if not c_name:
                        continue
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO transactions 
                        (complex_name, region_code, region_name, dong, deal_year, deal_month, deal_day, deal_date, deal_amount, exclusive_area, floor, build_year, cancel_deal_type, is_cancel, req_gbn, rdealer_lawdnm)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        c_name,
                        tx.get("region_code", ""),
                        tx.get("region_name", ""),
                        tx.get("dong", ""),
                        int(tx.get("deal_year", 2024)),
                        int(tx.get("deal_month", 1)),
                        int(tx.get("deal_day", 1)),
                        tx.get("deal_date", ""),
                        int(tx.get("deal_amount", 0)),
                        round(float(tx.get("exclusive_area", 0)), 2),
                        int(tx.get("floor", 0)),
                        int(tx.get("build_year", 0)),
                        tx.get("cancel_deal_type", ""),
                        1 if tx.get("cancel_deal_type") else 0,
                        tx.get("req_gbn", "중개거래"),
                        tx.get("rdealer_lawdnm", "현지 중개사")
                    ))
                    if cursor.rowcount > 0:
                        inserted_count += 1
                except Exception:
                    continue
            conn.commit()
    except Exception as e:
        print(f"Error in insert_transactions: {e}")
        
    return inserted_count


def get_transactions_df(complex_name: Optional[str] = None, min_area: Optional[float] = None, max_area: Optional[float] = None) -> pd.DataFrame:
    """Get transactions as a Pandas DataFrame with optional filters."""
    query = "SELECT * FROM transactions WHERE is_cancel = 0"
    params = []
    
    if complex_name:
        query += " AND complex_name = ?"
        params.append(complex_name)
        
    if min_area is not None:
        query += " AND exclusive_area >= ?"
        params.append(min_area)
        
    if max_area is not None:
        query += " AND exclusive_area <= ?"
        params.append(max_area)
        
    query += " ORDER BY deal_date ASC, id ASC"
    
    with get_connection() as conn:
        df = pd.read_sql_query(query, conn, params=params)
        
    if not df.empty:
        df["deal_date"] = pd.to_datetime(df["deal_date"])
        
    return df


def add_alert(complex_name: str, alert_type: str, message: str, deal_date: str, deal_amount: int, exclusive_area: float, floor: int):
    """Add a price alert log."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO price_alerts (complex_name, alert_type, message, deal_date, deal_amount, exclusive_area, floor)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (complex_name, alert_type, message, deal_date, deal_amount, exclusive_area, floor))
        conn.commit()


def get_recent_alerts(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve latest alerts."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM price_alerts 
            ORDER BY deal_date DESC, id DESC 
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
