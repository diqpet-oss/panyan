"""
盘眼系统配置
"""
import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TENCNET_QUOTE_URL = "http://qt.gtimg.cn/q={codes}"
REQUEST_TIMEOUT = 5
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://qt.gtimg.cn/",
}

QUOTE_REFRESH_INTERVAL = 3
HEALTH_CHECK_INTERVAL = 15

INDEX_CODES = [
    "sh000001",
    "sz399001",
    "sz399006",
    "sz399300",
    "sh000688",
    "sh000016",
]

DEFAULT_WATCHLIST = [
    "sz000333",
    "sh600519",
    "sz000858",
    "sh600036",
    "sz300750",
    "sh601318",
    "sz002594",
    "sh600900",
    "sh601012",
    "sz002415",
]

ALERT_CHANGE_PCT = 5.0
ALERT_VOLUME_SURGE = 3.0
ALERT_AMPLITUDE = 8.0

DATA_SOURCES = [
    {"name": "腾讯行情",   "type": "tencent",  "priority": 1, "enabled": True},
    {"name": "efinance",   "type": "efinance", "priority": 2, "enabled": True},
    {"name": "akshare",    "type": "akshare",  "priority": 3, "enabled": True},
    {"name": "baostock",   "type": "baostock", "priority": 4, "enabled": True},
    {"name": "mootdx",     "type": "mootdx",   "priority": 5, "enabled": True},
    {"name": "yfinance",   "type": "yfinance", "priority": 6, "enabled": True},
]

BACKEND_PORT = int(os.environ.get("PANYAN_PORT", 9090))
