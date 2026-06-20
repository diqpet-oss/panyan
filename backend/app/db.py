"""
盘眼 数据库持久化模块
SQLite 存储自选股、搜索缓存等
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger("panyan.db")

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "panyan.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist (
            code TEXT PRIMARY KEY,
            added_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            keyword TEXT PRIMARY KEY,
            results_json TEXT NOT NULL,
            cached_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()
    logger.info("数据库初始化完成: %s", DB_PATH)


def load_watchlist() -> List[str]:
    """从数据库加载自选股列表"""
    try:
        conn = _get_conn()
        rows = conn.execute("SELECT code FROM watchlist ORDER BY added_at").fetchall()
        conn.close()
        codes = [r[0] for r in rows]
        logger.info("从数据库加载 %d 只自选股", len(codes))
        return codes
    except Exception as e:
        logger.warning("加载自选股失败: %s", e)
        return []


def save_watchlist(codes: List[str]):
    """全量保存自选股列表到数据库"""
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM watchlist")
        for code in codes:
            conn.execute("INSERT OR IGNORE INTO watchlist (code) VALUES (?)", (code,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("保存自选股失败: %s", e)


def add_watchlist_item(code: str):
    """添加单个自选股"""
    try:
        conn = _get_conn()
        conn.execute("INSERT OR IGNORE INTO watchlist (code) VALUES (?)", (code,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("添加自选股失败: %s", e)


def remove_watchlist_item(code: str):
    """删除单个自选股"""
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM watchlist WHERE code = ?", (code,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("删除自选股失败: %s", e)


def get_cached_search(keyword: str) -> List[dict]:
    """获取缓存的搜索结果（1小时有效）"""
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT results_json FROM search_cache WHERE keyword = ? "
            "AND datetime(cached_at) > datetime('now', 'localtime', '-1 hour')",
            (keyword,)
        ).fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception:
        pass
    return []


def set_cached_search(keyword: str, results: List[dict]):
    """缓存搜索结果"""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO search_cache (keyword, results_json, cached_at) "
            "VALUES (?, ?, datetime('now','localtime'))",
            (keyword, json.dumps(results, ensure_ascii=False))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("缓存搜索结果失败: %s", e)
