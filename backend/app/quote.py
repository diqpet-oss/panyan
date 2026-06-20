"""
盘眼 行情数据获取模块
多数据源接入：腾讯行情(primary), efinance, baostock, akshare, yfinance, mootdx
"""
from __future__ import annotations
import asyncio
import logging
import time
import urllib.request
from typing import Dict, List, Optional

import pandas as pd

from .config import (
    TENCNET_QUOTE_URL, REQUEST_TIMEOUT, REQUEST_HEADERS,
    INDEX_CODES, DATA_SOURCES,
)
from .models import StockQuote, IndexQuote, HealthStatus

logger = logging.getLogger("panyan.quote")

_health_cache: Dict[str, HealthStatus] = {}


# ==================== 腾讯行情 ====================

async def fetch_tencent_quote(codes: List[str]) -> Dict[str, StockQuote]:
    """从腾讯行情接口批量获取实时行情"""
    if not codes:
        return {}
    url = TENCNET_QUOTE_URL.format(codes=",".join(codes))
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, headers=REQUEST_HEADERS)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read()
        latency = (time.monotonic() - start) * 1000
        text = raw.decode("gbk")

        results: Dict[str, StockQuote] = {}
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or "=" not in line:
                continue
            try:
                start_idx = line.index('"') + 1
                end_idx = line.rindex('"')
                fields = line[start_idx:end_idx].split("~")
            except (ValueError, IndexError):
                continue

            if len(fields) < 44:
                continue

            code_raw = fields[2] if fields[2] else ""
            if not code_raw:
                continue

            market_prefix = ""
            if line.startswith("v_sh"):
                market_prefix = "sh"
            elif line.startswith("v_sz"):
                market_prefix = "sz"
            elif line.startswith("v_hk"):
                market_prefix = "hk"
            elif line.startswith("v_us"):
                market_prefix = "us"
            full_code = f"{market_prefix}{code_raw}" if market_prefix else code_raw

            def sf(i: int, default="0") -> str:
                return fields[i] if i < len(fields) and fields[i] else default

            q = StockQuote(
                code=full_code,
                name=sf(1),
                price=float(sf(3)),
                prev_close=float(sf(4)),
                open_price=float(sf(5)),
                volume=int(float(sf(6))),
                bid_prices=[float(sf(9)), float(sf(11)), float(sf(13)), float(sf(15)), float(sf(17))],
                bid_volumes=[int(float(sf(10))), int(float(sf(12))), int(float(sf(14))), int(float(sf(16))), int(float(sf(18)))],
                ask_prices=[float(sf(19)), float(sf(21)), float(sf(23)), float(sf(25)), float(sf(27))],
                ask_volumes=[int(float(sf(20))), int(float(sf(22))), int(float(sf(24))), int(float(sf(26))), int(float(sf(28)))],
                timestamp=sf(30),
                change=float(sf(31)),
                change_pct=float(sf(32)),
                high=float(sf(33)),
                low=float(sf(34)),
                amount=float(sf(37)),
                turnover_rate=float(sf(38)),
                pe_ttm=float(sf(39)),
                amplitude=float(sf(43)),
                market_cap=float(sf(45)) if len(fields) > 45 and sf(45, "") else 0.0,
                circulating_cap=float(sf(46)) if len(fields) > 46 and sf(46, "") else 0.0,
                source="腾讯行情",
            )
            results[q.code] = q

        _update_health("腾讯行情", latency=latency, error=None)
        return results
    except Exception as e:
        _update_health("腾讯行情", latency=None, error=str(e))
        return {}


# ==================== efinance ====================

async def fetch_efinance_quote(codes: List[str]) -> Dict[str, StockQuote]:
    if not codes:
        return {}
    start = time.monotonic()
    try:
        import efinance as ef
        pure_codes = [c[2:] if len(c) > 2 else c for c in codes]
        df = await asyncio.to_thread(ef.stock.get_realtime_quotes, pure_codes)
        latency = (time.monotonic() - start) * 1000

        results: Dict[str, StockQuote] = {}
        for _, row in df.iterrows():
            code_str = str(row.get("股票代码", ""))
            if code_str.startswith(("6", "9")):
                mkt = "sh"
            elif code_str.startswith(("0", "2", "3")):
                mkt = "sz"
            else:
                mkt = "sh"
            full_code = f"{mkt}{code_str}"

            results[full_code] = StockQuote(
                code=full_code,
                name=str(row.get("股票名称", "")),
                price=float(row.get("最新价", 0)),
                prev_close=float(row.get("昨收", 0)),
                open_price=float(row.get("今开", 0)),
                high=float(row.get("最高", 0)),
                low=float(row.get("最低", 0)),
                volume=int(float(row.get("成交量", 0))),
                amount=float(row.get("成交额", 0)) / 10000,
                change=float(row.get("涨跌额", 0)),
                change_pct=float(row.get("涨跌幅", 0)),
                turnover_rate=float(row.get("换手率", 0)),
                amplitude=float(row.get("振幅", 0)),
                pe_ttm=float(row.get("市盈率-动态", 0)),
                source="efinance",
            )
        _update_health("efinance", latency=latency, error=None)
        return results
    except Exception as e:
        _update_health("efinance", latency=None, error=str(e))
        return {}


# ==================== akshare ====================

async def fetch_akshare_quote(codes: List[str]) -> Dict[str, StockQuote]:
    if not codes:
        return {}
    start = time.monotonic()
    try:
        import akshare as ak
        df = await asyncio.to_thread(ak.stock_zh_a_spot_em)
        latency = (time.monotonic() - start) * 1000

        results: Dict[str, StockQuote] = {}
        for _, row in df.iterrows():
            code_str = str(row.get("代码", ""))
            full_code = f"sz{code_str}" if code_str.startswith(("0", "2", "3")) else f"sh{code_str}"
            if full_code not in codes:
                continue
            results[full_code] = StockQuote(
                code=full_code,
                name=str(row.get("名称", "")),
                price=float(row.get("最新价", 0)),
                change=float(row.get("涨跌额", 0)),
                change_pct=float(row.get("涨跌幅", 0)),
                volume=int(float(row.get("成交量", 0))),
                amount=float(row.get("成交额", 0)),
                high=float(row.get("最高", 0)),
                low=float(row.get("最低", 0)),
                open_price=float(row.get("今开", 0)),
                turnover_rate=float(row.get("换手率", 0)),
                pe_ttm=float(row.get("市盈率-动态", 0)),
                amplitude=float(row.get("振幅", 0)),
                source="akshare",
            )
        _update_health("akshare", latency=latency, error=None)
        return results
    except Exception as e:
        _update_health("akshare", latency=None, error=str(e))
        return {}


# ==================== yfinance ====================

async def fetch_yfinance_quote(codes: List[str]) -> Dict[str, StockQuote]:
    hk_codes = [c[2:] + ".HK" for c in codes if c.startswith("hk")]
    us_codes = [c[2:] for c in codes if c.startswith("us")]
    all_tickers = hk_codes + us_codes
    if not all_tickers:
        return {}
    start = time.monotonic()
    try:
        import yfinance as yf
        tkrs = await asyncio.to_thread(yf.Tickers, " ".join(all_tickers))
        latency = (time.monotonic() - start) * 1000

        results: Dict[str, StockQuote] = {}
        for tkr_name, tkr in tkrs.tickers.items():
            info = await asyncio.to_thread(lambda: tkr.info)
            if not info:
                continue
            mkt = "hk" if ".HK" in tkr_name else "us"
            code_str = tkr_name.replace(".HK", "")
            full_code = f"{mkt}{code_str}"

            results[full_code] = StockQuote(
                code=full_code,
                name=str(info.get("shortName", info.get("longName", tkr_name))),
                price=float(info.get("currentPrice", info.get("regularMarketPrice", 0))),
                prev_close=float(info.get("previousClose", 0)),
                open_price=float(info.get("open", 0)),
                high=float(info.get("dayHigh", 0)),
                low=float(info.get("dayLow", 0)),
                volume=int(info.get("volume", 0)),
                amount=float(info.get("marketCap", 0)) / 10000 if info.get("marketCap") else 0.0,
                change=float(info.get("regularMarketChange", 0)),
                change_pct=float(info.get("regularMarketChangePercent", 0)),
                market_cap=float(info.get("marketCap", 0)) / 10000,
                source="yfinance",
            )
        _update_health("yfinance", latency=latency, error=None)
        return results
    except Exception as e:
        _update_health("yfinance", latency=None, error=str(e))
        return {}


# ==================== 统一数据总线 ====================

def _update_health(source: str, latency: Optional[float], error: Optional[str]):
    now = pd.Timestamp.now("Asia/Shanghai").strftime("%H:%M:%S")
    h = _health_cache.get(source, HealthStatus(source=source))
    h.source = source
    if error:
        h.status = "error"
        h.last_error = f"{now}: {error[:60]}"
        h.error_count += 1
    elif latency is not None:
        if latency > 3000:
            h.status = "slow"
        else:
            h.status = "ok"
        h.latency_ms = latency
        h.last_success = now
    _health_cache[source] = h


def get_health_snapshot() -> List[HealthStatus]:
    return [h for h in _health_cache.values()]


def get_primary_healthy_source() -> str:
    for ds in DATA_SOURCES:
        h = _health_cache.get(ds["name"])
        if h and h.status == "ok":
            return ds["name"]
    return "腾讯行情"


async def fetch_all_quotes(codes: List[str], primary_only: bool = True) -> Dict[str, StockQuote]:
    if not codes:
        return {}

    a_codes = [c for c in codes if c.startswith(("sh", "sz"))]
    hk_codes = [c for c in codes if c.startswith("hk")]
    us_codes = [c for c in codes if c.startswith("us")]

    results: Dict[str, StockQuote] = {}

    if a_codes:
        q = await fetch_tencent_quote(a_codes)
        if len(q) >= len(a_codes) * 0.5:
            results.update(q)
        else:
            logger.warning("tencent partial (%d/%d), falling back to efinance", len(q), len(a_codes))
            q2 = await fetch_efinance_quote(a_codes)
            if len(q2) >= len(a_codes) * 0.5:
                results.update(q2)
            else:
                q3 = await fetch_akshare_quote(a_codes)
                if q3:
                    results.update(q3)
            results.update(q)

    if hk_codes:
        q = await fetch_tencent_quote(hk_codes)
        if len(q) < len(hk_codes) * 0.5:
            q2 = await fetch_yfinance_quote(hk_codes)
            q.update(q2)
        results.update(q)

    if us_codes:
        q = await fetch_yfinance_quote(us_codes)
        results.update(q)

    return results


async def fetch_index_quotes() -> Dict[str, IndexQuote]:
    q = await fetch_tencent_quote(INDEX_CODES)
    results: Dict[str, IndexQuote] = {}
    for code, sq in q.items():
        results[code] = IndexQuote(
            code=code,
            name=sq.name,
            price=sq.price,
            change=sq.change,
            change_pct=sq.change_pct,
            open_price=sq.open_price,
            high=sq.high,
            low=sq.low,
            volume=sq.volume,
            amount=sq.amount,
            timestamp=sq.timestamp,
        )
    return results


US_INDEX_MAP = {
    "^GSPC": ("usSPX", "标普500"),
    "^DJI":  ("usDJI", "道琼斯"),
    "^IXIC": ("usIXIC", "纳斯达克"),
}


async def fetch_index_quotes_yf() -> Dict[str, IndexQuote]:
    results: Dict[str, IndexQuote] = {}
    for yf_code, (code, name) in US_INDEX_MAP.items():
        try:
            import yfinance as yf
            tkr = await asyncio.to_thread(yf.Ticker, yf_code)
            info = await asyncio.to_thread(lambda: tkr.history(period="1d"))
            if not info.empty:
                row = info.iloc[-1]
                close = float(row["Close"])
                open_p = float(row["Open"])
                results[code] = IndexQuote(
                    code=code,
                    name=name,
                    price=close,
                    open_price=open_p,
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    change=close - open_p,
                    change_pct=(close - open_p) / open_p * 100 if open_p else 0,
                    volume=int(row["Volume"]),
                    source="yfinance",
                )
        except Exception:
            continue
    return results
