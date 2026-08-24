#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""尾盘阻击选股（2026-08-17 版，口径对齐 8/14 尾盘阻击 CSV）

用法:
    python3 reports/尾盘阻击选股.py            # 全市场扫描，输出 CSV 到 reports/
    python3 reports/尾盘阻击选股.py --limit 30 # 只输出前30只（调试用）

策略口径（对应 CSV 列）:
    pct          当日涨幅 2.0% ~ 9.8%（剔除涨停/一字板）
    near_high_pct 现价距当日最高价回撤 < 1.5%
    amount_yi    成交额 >= 3 亿
    turnover     换手率 >= 4.5%
    mcap_yi      流通市值 50 ~ 600 亿
    up6          近6个交易日上涨天数 >= 4/6
    tail6_gain   最后6分钟累计涨幅 >= -0.25%
    14h_gain     14:00 后涨幅 > 0.3%（盘中未到14:00时用"近30分钟涨幅"代理，输出标注）
    last_up      最后一根分钟K收阳
"""

from __future__ import annotations

import csv
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

SINA_LIST_URL = (
    "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeData?page={page}&num=100&sort=symbol&asc=1&node=hs_a"
)
SINA_KLINE_URL = (
    "http://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
    "?symbol={symbol}&scale={scale}&ma=no&datalen={datalen}"
)

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "http://quote.eastmoney.com/"}


def http_json(url: str, retries: int = 2):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if i < retries:
                time.sleep(0.4 * (i + 1))
    return {}


def symbol_of(code: str) -> str:
    return "sh" + code if code.startswith("6") else "sz" + code


def fetch_market() -> list[dict]:
    """新浪 hs_a 分页拉全市场快照（单页最多100条，含北交所，需过滤 bj）"""
    rows: list[dict] = []
    page = 1
    while True:
        data = http_json(SINA_LIST_URL.format(page=page))
        if not isinstance(data, list) or not data:
            break
        rows.extend(data)
        if len(data) < 100:
            break
        page += 1
        if page > 80:
            break
    return [r for r in rows if str(r.get("symbol", "")).startswith(("sh", "sz"))]


def fetch_trends(code: str) -> list[tuple[str, float]]:
    data = http_json(SINA_KLINE_URL.format(symbol=symbol_of(code), scale=1, datalen=240))
    if not isinstance(data, list):
        return []
    rows = []
    today = datetime.now().strftime("%Y-%m-%d")
    for bar in data:
        try:
            day = bar.get("day", "")
            if not day.startswith(today):
                continue
            rows.append((day, float(bar["close"])))
        except ValueError:
            continue
    return rows


def fetch_daily_closes(code: str) -> list[float]:
    data = http_json(SINA_KLINE_URL.format(symbol=symbol_of(code), scale=240, datalen=10))
    if not isinstance(data, list):
        return []
    closes = []
    for bar in data:
        try:
            closes.append(float(bar["close"]))
        except (ValueError, KeyError, TypeError):
            continue
    return closes


def probe_stock(stock: dict) -> dict | None:
    code = stock["code"]
    price = stock["price"]
    high = stock["high"]
    pct = stock["pct"]
    near_high_pct = (high - price) / high * 100 if high > 0 else 999.0

    rows = fetch_trends(code)
    closes = fetch_daily_closes(code)
    if len(rows) < 8 or len(closes) < 7:
        return None

    prices = [p for _, p in rows]
    last_up = prices[-1] > prices[-2]
    tail6_gain = (prices[-1] / prices[-7] - 1) * 100

    # 14:00 后涨幅；盘中未到 14:00 时用"近30分钟涨幅"代理
    proxy_14h = False
    base_idx = None
    for i, (ts, _) in enumerate(rows):
        if ts[11:16] >= "14:00":
            base_idx = i
            break
    if base_idx is None:
        proxy_14h = True
        base_idx = max(0, len(rows) - 31)
    gain_14h = (prices[-1] / prices[base_idx] - 1) * 100 if prices[base_idx] > 0 else -999.0

    last6 = closes[-7:]
    up6 = sum(1 for i in range(1, 7) if last6[i] > last6[i - 1])

    return {
        "code": code,
        "name": stock["name"],
        "price": price,
        "pct": pct,
        "near_high_pct": near_high_pct,
        "up6": f"{up6}/6",
        "tail6_gain": tail6_gain,
        "14h_gain": gain_14h,
        "last_up": last_up,
        "amount_yi": stock["amount"] / 1e8,
        "turnover": stock["turnover"],
        "mcap_yi": stock["mcap_yi"],
        "proxy_14h": proxy_14h,
    }


def main() -> int:
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    print(f"[{datetime.now():%H:%M:%S}] 拉取全市场快照…")
    market = fetch_market()
    if not market:
        print("获取全市场快照失败")
        return 1
    print(f"全市场 {len(market)} 只，开始初筛…")

    candidates = []
    for s in market:
        name = s.get("name", "")
        if any(x in name for x in ("ST", "退", "N", "C")):
            continue
        try:
            pct = float(s.get("changepercent") or 0)
            price = float(s.get("trade") or 0)
            high = float(s.get("high") or 0)
            amount = float(s.get("amount") or 0)
            turnover = float(s.get("turnoverratio") or 0)
            mcap = float(s.get("nmc") or 0) * 1e4  # 新浪流通市值单位为万元
        except (ValueError, TypeError):
            continue
        if price <= 0:
            continue
        near_high = (high - price) / high * 100 if high > 0 else 999.0
        if not (2.0 <= pct < 9.8):
            continue
        if near_high > 1.5:
            continue
        if amount < 3e8 or turnover < 4.5 or not (50e8 <= mcap <= 600e8):
            continue
        candidates.append({
            "code": s.get("code"),
            "name": name,
            "price": price,
            "pct": pct,
            "high": high,
            "amount": amount,
            "turnover": turnover,
            "mcap_yi": mcap / 1e8,
        })

    print(f"初筛通过 {len(candidates)} 只，拉取分时/日K…")
    results = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futs = {pool.submit(probe_stock, s): s for s in candidates}
        done = 0
        for fut in as_completed(futs):
            done += 1
            if done % 20 == 0:
                print(f"  进度 {done}/{len(candidates)}")
            try:
                r = fut.result()
            except Exception:
                r = None
            if r is not None:
                results.append(r)

    final = [r for r in results
             if r["up6"].startswith(("4", "5", "6"))
             and r["last_up"]
             and r["tail6_gain"] >= -0.25
             and r["14h_gain"] > 0.3]
    final.sort(key=lambda r: r["tail6_gain"], reverse=True)

    if limit:
        final = final[:limit]

    today = datetime.now().strftime("%Y%m%d")
    out_path = f"reports/尾盘阻击_{today}.csv"
    fields = ["code", "name", "price", "pct", "near_high_pct", "up6",
              "tail6_gain", "14h_gain", "last_up", "amount_yi", "turnover", "mcap_yi"]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(final)

    print(f"\n=== 尾盘阻击候选 {len(final)} 只（保存: {out_path}）===")
    for r in final:
        tag = " [代理指标]" if r.get("proxy_14h") else ""
        print(f"{r['code']} {r['name']:<6} 价{r['price']:<8.2f} 涨{r['pct']:+.2f}% "
              f"距高{r['near_high_pct']:.2f}% 6日{r['up6']} 尾6分{r['tail6_gain']:+.2f}% "
              f"14h后{r['14h_gain']:+.2f}% 收阳{r['last_up']} "
              f"额{r['amount_yi']:.1f}亿 换手{r['turnover']:.1f}% 市值{r['mcap_yi']:.0f}亿{tag}")
    if any(r.get("proxy_14h") for r in final):
        print("\n注: 当前未到 14:00，'14h_gain' 用的是近30分钟涨幅代理，"
              "建议 14:30-14:50 重新运行做最终确认。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
