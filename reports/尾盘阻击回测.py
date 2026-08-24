#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""尾盘阻击策略历史回测（日线近似版）

数据源:
  - 新浪全市场快照: 当前代码/名称/流通市值(万元)/价格 -> 推算流通股本底数
  - 腾讯日K (不复权, OHLCV, 量单位为手): 历史日线
  - 上证指数日K: 大盘涨跌分组

回测口径（日线代理，与盘中版"尾盘阻击选股.py"对齐）:
  pct         当日涨幅 2.0% ~ 9.8%（剔除涨停/一字板）
  near_high   收盘距当日最高回撤 < 1.5%（代理"尾盘贴顶"）
  amount_est  成交额估算 >= 3 亿
  turnover_est 换手率估算 >= 4.5%
  mcap_est    流通市值估算 50 ~ 600 亿
  up6         近6个交易日上涨天数 >= 4/6
  last_up     收阳 close > open（代理"最后一根分钟K收阳"）
  备注: 盘中版独有指标(尾6分钟涨幅/14:00后涨幅/最后1分钟收阳)无法用日线还原,
        以"收盘贴近最高 + 收阳"近似，成功率属于"日线可观测口径"的估计。

用法:
    python3 reports/尾盘阻击回测.py            # 全流程: 拉数据(带缓存) + 回测 + 输出报告
    python3 reports/尾盘阻击回测.py --reuse   # 复用已有缓存直接回测
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.request
from bisect import bisect_left
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(BASE, "reports")
CACHE = os.path.join(REPORTS, ".weipan_cache")
START = "20250901"
END = "20260821"
TODAY = datetime.now().strftime("%Y%m%d")
KSTART = f"{START[:4]}-{START[4:6]}-{START[6:]}"
KEND = f"{END[:4]}-{END[4:6]}-{END[6:]}"

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "http://quote.eastmoney.com/"}
SINA_LIST_URL = (
    "http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeData?page={page}&num=100&sort=symbol&asc=1&node=hs_a"
)


def http_json(url: str, retries: int = 3):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if i < retries:
                time.sleep(0.5 * (i + 1))
    return {}


def fetch_market() -> list[dict]:
    """新浪 hs_a 分页拉全市场快照（含代码/名称/现价/流通市值万元）"""
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


def tx_symbol(code: str) -> str:
    return "sh" + code if code.startswith("6") else "sz" + code


def fetch_tx_kline(code: str) -> list[list]:
    """腾讯日K（不复权），返回 [date, open, close, high, low, volume(手)]"""
    sym = tx_symbol(code)
    url = (
        f"http://ifzq.gtimg.cn/appstock/app/fqkline/get?"
        f"param={sym},day,{KSTART},{KEND},2000,"
    )
    data = http_json(url)
    try:
        node = data["data"][sym]
        rows = node.get("day") or node.get("qfqday") or []
    except (KeyError, TypeError):
        rows = []
    out = []
    for r in rows:
        try:
            out.append([r[0], float(r[1]), float(r[2]), float(r[3]),
                        float(r[4]), float(r[5])])
        except (IndexError, TypeError, ValueError):
            continue
    return out


def load_or_fetch_kline(code: str, force: bool = False) -> list[list] | None:
    path = os.path.join(CACHE, f"{code}.json")
    if not force and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    rows = fetch_tx_kline(code)
    if rows:
        try:
            os.makedirs(CACHE, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False)
        except OSError:
            pass
    return rows or None


def build_signals(market: list[dict]) -> pd.DataFrame:
    """逐股计算日线代理信号 + 次日结果"""
    float_shares = {}
    for s in market:
        code = str(s.get("code", ""))
        try:
            price = float(s.get("trade") or s.get("settlement") or 0)
            nmc = float(s.get("nmc") or 0) * 1e4  # 万元 -> 元
        except (ValueError, TypeError):
            continue
        if price > 0 and nmc > 0:
            float_shares[code] = nmc / price

    recs = []
    codes = [str(s["code"]) for s in market]
    done = 0
    with ThreadPoolExecutor(max_workers=24) as pool:
        futs = {pool.submit(load_or_fetch_kline, c): c for c in codes}
        for fut in as_completed(futs):
            code = futs[fut]
            done += 1
            if done % 300 == 0:
                print(f"  K线 {done}/{len(codes)}")
            try:
                rows = fut.result()
            except Exception:
                rows = None
            if not rows:
                continue
            fs = float_shares.get(code, np.nan)
            if not np.isfinite(fs) or fs <= 0:
                continue
            dates = [r[0] for r in rows]
            arr = np.array([r[1:] for r in rows], dtype=float)  # [o, c, h, l, vol]
            o = arr[:, 0]
            c = arr[:, 1]
            h = arr[:, 2]
            l = arr[:, 3]
            v = arr[:, 4] * 100.0  # 手 -> 股
            prev_c = np.roll(c, 1)
            prev_c[0] = np.nan
            pct = (c / prev_c - 1.0) * 100.0
            near_high = (h - c) / h * 100.0
            typ_price = (o + h + l + c) / 4.0
            amount = v * typ_price
            turnover = v / fs * 100.0
            mcap = fs * c
            up = c > prev_c
            up6 = pd.Series(up).rolling(6).sum().to_numpy()
            n = len(c)
            for i in range(7, n - 1):
                if not (2.0 <= pct[i] < 9.8):
                    continue
                if near_high[i] >= 1.5:
                    continue
                if amount[i] < 3e8 or turnover[i] < 4.5:
                    continue
                if not (50e8 <= mcap[i] <= 600e8):
                    continue
                if up6[i] < 4:
                    continue
                if c[i] <= o[i]:  # 收阳
                    continue
                recs.append({
                    "date": dates[i],
                    "code": code,
                    "close_buy": c[i],
                    "pct": pct[i],
                    "near_high_pct": near_high[i],
                    "amount_yi": amount[i] / 1e8,
                    "turnover": turnover[i],
                    "mcap_yi": mcap[i] / 1e8,
                    "up6": up6[i],
                    "next_open": o[i + 1],
                    "next_high": h[i + 1],
                    "next_close": c[i + 1],
                    "next_date": rows[i + 1][0],
                })
    return pd.DataFrame(recs)


def load_index() -> pd.DataFrame:
    url = (f"http://ifzq.gtimg.cn/appstock/app/fqkline/get?"
           f"param=sh000001,day,{KSTART},{KEND},2000,")
    data = http_json(url)
    node = data["data"]["sh000001"]
    krows = node.get("day") or node.get("qfqday") or []
    df = pd.DataFrame(
        [[r[0], float(r[2])] for r in krows], columns=["date", "close"]
    )
    return df


def pct_str(x: float, nd: int = 1) -> str:
    return f"{x * 100:.{nd}f}%"


def add_stats(sdf: pd.DataFrame) -> dict:
    n = len(sdf)
    if n == 0:
        return {}
    buy = sdf["close_buy"].to_numpy()
    o = sdf["next_open"].to_numpy()
    h = sdf["next_high"].to_numpy()
    c = sdf["next_close"].to_numpy()
    ret_open = o / buy - 1.0
    ret_max = h / buy - 1.0
    ret_close = c / buy - 1.0
    return {
        "n": n,
        "次日高开率": (o > buy).mean(),
        "次日收涨率": (c > buy).mean(),
        "盘中可盈利卖出率": (h > buy).mean(),
        "含费可卖出率": (h > buy * 1.001).mean(),
        "次日冲高1%率": (h >= buy * 1.01).mean(),
        "次日冲高2%率": (h >= buy * 1.02).mean(),
        "次日冲高3%率": (h >= buy * 1.03).mean(),
        "收盘亏超1%率": (c <= buy * 0.99).mean(),
        "平均最大可卖收益": ret_max.mean(),
        "中位最大可卖收益": np.median(ret_max),
        "平均次日收盘收益": ret_close.mean(),
        "中位次日收盘收益": np.median(ret_close),
        "平均次日开盘收益": ret_open.mean(),
    }


def fmt_stats_row(label: str, st: dict) -> list:
    if not st:
        return [label, 0, "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-"]
    return [
        label,
        st["n"],
        pct_str(st["次日高开率"]),
        pct_str(st["次日收涨率"]),
        pct_str(st["盘中可盈利卖出率"]),
        pct_str(st["含费可卖出率"]),
        pct_str(st["次日冲高1%率"]),
        pct_str(st["次日冲高2%率"]),
        pct_str(st["次日冲高3%率"]),
        pct_str(st["收盘亏超1%率"]),
        pct_str(st["平均最大可卖收益"]),
        pct_str(st["中位最大可卖收益"]),
        pct_str(st["平均次日收盘收益"]),
        pct_str(st["中位次日收盘收益"]),
        pct_str(st["平均次日开盘收益"]),
    ]


def main() -> int:
    reuse = "--reuse" in sys.argv
    if not reuse:
        print("[1/4] 拉取全市场快照…")
        market = fetch_market()
        if not market:
            print("全市场快照失败")
            return 1
        print(f"  共 {len(market)} 只（沪深A）")
    else:
        market = []
        snap = os.path.join(CACHE, "_market.json")
        if os.path.exists(snap):
            with open(snap, encoding="utf-8") as f:
                market = json.load(f)
            print(f"[1/4] 复用快照 {len(market)} 只")
        else:
            print("无快照缓存，请先不带 --reuse 运行")
            return 1

    if not reuse:
        os.makedirs(CACHE, exist_ok=True)
        with open(os.path.join(CACHE, "_market.json"), "w", encoding="utf-8") as f:
            json.dump(market, f, ensure_ascii=False)

    print("[2/4] 拉取/加载日K并计算信号…")
    sig = build_signals(market)
    if sig.empty:
        print("无信号")
        return 1

    print(f"[3/4] 信号共 {len(sig)} 条，关联大盘…")
    idx = load_index()
    idx_dates = idx["date"].tolist()
    idx_close = dict(zip(idx["date"], idx["close"]))
    sig["mkt_buy"] = np.nan
    sig["mkt_next"] = np.nan
    for i, row in sig.iterrows():
        d = row["date"]
        j = bisect_left(idx_dates, d)
        if j == 0 or j >= len(idx_dates) or idx_dates[j] != d:
            j = min(j, len(idx_dates) - 1)
        prev_date = idx_dates[j - 1] if j > 0 else None
        cur = idx_close.get(idx_dates[j])
        prev = idx_close.get(prev_date) if prev_date else None
        if cur and prev and prev > 0:
            sig.at[i, "mkt_buy"] = cur / prev - 1.0
        jn = j + 1
        if jn < len(idx_dates):
            cur2 = idx_close.get(idx_dates[jn])
            if cur and cur2:
                sig.at[i, "mkt_next"] = cur2 / cur - 1.0

    # 只统计有次日数据的信号（剔除最后一天）
    back = sig.dropna(subset=["next_close"]).copy()
    back["date"] = pd.to_datetime(back["date"])
    print(f"  回测样本 {len(back)} 条 / 交易日 {back['date'].nunique()} 天 / "
          f"个股 {back['code'].nunique()} 只")

    overall = add_stats(back)

    def bucket(df, mask, label):
        st = add_stats(df[mask])
        return fmt_stats_row(label, st)

    rows = []
    rows.append(fmt_stats_row("全部样本", overall))
    rows.append(fmt_stats_row("次日大盘: 上涨", add_stats(back[back["mkt_next"] > 0])))
    rows.append(fmt_stats_row("次日大盘: 下跌", add_stats(back[back["mkt_next"] < 0])))
    rows.append(fmt_stats_row("次日大盘: 大跌≤-1%", add_stats(back[back["mkt_next"] <= -0.01])))
    rows.append(fmt_stats_row("次日大盘: 平盘|±0.3%", add_stats(
        back[back["mkt_next"].abs() <= 0.003])))
    rows.append(fmt_stats_row("买入日大盘: 上涨", add_stats(back[back["mkt_buy"] > 0])))
    rows.append(fmt_stats_row("买入日大盘: 下跌", add_stats(back[back["mkt_buy"] < 0])))
    rows.append(fmt_stats_row("买入日跌×次日跌", add_stats(
        back[(back["mkt_buy"] < 0) & (back["mkt_next"] < 0)])))
    rows.append(fmt_stats_row("买入日涨×次日跌", add_stats(
        back[(back["mkt_buy"] > 0) & (back["mkt_next"] < 0)])))

    cols = ["分组", "样本数", "次日高开率", "次日收涨率", "盘中可盈利卖出率",
            "含费可卖出率", "冲高1%率", "冲高2%率", "冲高3%率", "收盘亏超1%率",
            "平均最大可卖收益", "中位最大可卖收益", "平均次日收盘收益",
            "中位次日收盘收益", "平均次日开盘收益"]
    stat_df = pd.DataFrame(rows, columns=cols)

    # 按日汇总
    daily = back.groupby("date").apply(
        lambda g: pd.Series({
            "信号数": len(g),
            "次日收涨率": (g["next_close"] > g["close_buy"]).mean(),
            "可盈利卖出率": (g["next_high"] > g["close_buy"]).mean(),
            "平均最大可卖收益": (g["next_high"] / g["close_buy"] - 1).mean(),
            "平均次日收盘收益": (g["next_close"] / g["close_buy"] - 1).mean(),
            "次日大盘涨跌": g["mkt_next"].mean(),
        })
    ).reset_index()

    # 月度汇总
    bm = back.copy()
    bm["ym"] = bm["date"].dt.strftime("%Y-%m")
    monthly = bm.groupby("ym").apply(
        lambda g: pd.Series({
            "信号数": len(g),
            "次日收涨率": (g["next_close"] > g["close_buy"]).mean(),
            "盘中可盈利卖出率": (g["next_high"] > g["close_buy"]).mean(),
            "平均最大可卖收益": (g["next_high"] / g["close_buy"] - 1).mean(),
            "平均次日收盘收益": (g["next_close"] / g["close_buy"] - 1).mean(),
            "平均次日大盘涨跌": g["mkt_next"].mean(),
        })
    ).reset_index()

    # 次日收益分布
    close_ret = back["next_close"] / back["close_buy"] - 1.0
    high_ret = back["next_high"] / back["close_buy"] - 1.0
    close_buckets = [
        ("<-3%", (close_ret < -0.03).mean()),
        ("-3%~-1%", ((close_ret >= -0.03) & (close_ret < -0.01)).mean()),
        ("-1%~0%", ((close_ret >= -0.01) & (close_ret < 0)).mean()),
        ("0%~1%", ((close_ret >= 0) & (close_ret < 0.01)).mean()),
        ("1%~3%", ((close_ret >= 0.01) & (close_ret < 0.03)).mean()),
        (">3%", (close_ret >= 0.03).mean()),
    ]
    high_buckets = [
        ("<0%", (high_ret < 0).mean()),
        ("0%~1%", ((high_ret >= 0) & (high_ret < 0.01)).mean()),
        ("1%~2%", ((high_ret >= 0.01) & (high_ret < 0.02)).mean()),
        ("2%~3%", ((high_ret >= 0.02) & (high_ret < 0.03)).mean()),
        ("3%~5%", ((high_ret >= 0.03) & (high_ret < 0.05)).mean()),
        (">5%", (high_ret >= 0.05).mean()),
    ]

    out_md = os.path.join(REPORTS, f"尾盘阻击回测_{TODAY}.md")
    out_csv = os.path.join(REPORTS, f"尾盘阻击回测明细_{TODAY}.csv")
    out_daily = os.path.join(REPORTS, f"尾盘阻击回测_按日_{TODAY}.csv")

    with open(out_md, "w", encoding="utf-8") as f:
        f.write(f"# 尾盘阻击策略回测（日线近似版）· {TODAY}\n\n")
        f.write(f"> 回测区间 {START[:4]}-{START[4:6]}-{START[6:]} ~ {END[:4]}-{END[4:6]}-{END[6:]}"
                f"｜数据源: 腾讯日K(不复权)+新浪快照｜口径: 日线代理\n\n")
        f.write("## 一、总体成功率\n\n")
        f.write("买入价=当日收盘价（尾盘买入），统计次日表现：\n\n")
        f.write("| 指标 | 数值 |\n|---|---|\n")
        for k, v in [
            ("回测信号数", overall["n"]),
            ("次日高开率", overall["次日高开率"]),
            ("次日收涨率", overall["次日收涨率"]),
            ("次日盘中可盈利卖出率(最高价>买入价)", overall["盘中可盈利卖出率"]),
            ("含手续费可卖出率(最高价>买入价+0.1%)", overall["含费可卖出率"]),
            ("次日冲高≥1%", overall["次日冲高1%率"]),
            ("次日冲高≥2%", overall["次日冲高2%率"]),
            ("次日冲高≥3%", overall["次日冲高3%率"]),
            ("平均最大可卖收益(次日最高/买入-1)", overall["平均最大可卖收益"]),
            ("平均次日收盘收益", overall["平均次日收盘收益"]),
            ("收盘亏超1%比例", overall["收盘亏超1%率"]),
        ]:
            if isinstance(v, float):
                f.write(f"| {k} | {pct_str(v)} |\n")
            else:
                f.write(f"| {k} | {v} |\n")
        f.write("\n## 二、大盘环境分组\n\n")
        f.write(stat_df.to_markdown(index=False) + "\n\n")
        f.write("## 三、结论\n\n")
        f.write("- 盘中可盈利卖出率与次日收涨率是判断策略有效性的两个核心数字；"
                "若可盈利卖出率显著高于收涨率，说明策略适合'次日冲高止盈'而非持有。\n")
        f.write("- 对比'次日大盘下跌'分组的各项比率，可判断大盘环境对尾盘阻击成功率的拖累程度。\n")
        f.write("- 注意：日线代理口径无法还原盘中版'尾6分钟涨幅/14:00后涨幅'两个精确过滤条件，"
                "实际盘中策略的成功率通常高于或等于此日线口径的估计。\n")
        f.write("\n## 四、月度表现\n\n")
        f.write(monthly.to_markdown(index=False) + "\n\n")
        f.write("## 五、次日收益分布（全部样本）\n\n")
        f.write("| 次日收盘收益区间 | 占比 |\n|---|---|\n")
        for label, ratio in close_buckets:
            f.write(f"| {label} | {pct_str(ratio)} |\n")
        f.write("\n| 次日盘中最高可卖收益区间 | 占比 |\n|---|---|\n")
        for label, ratio in high_buckets:
            f.write(f"| {label} | {pct_str(ratio)} |\n")
        f.write("\n## 六、大盘环境占比\n\n")
        f.write(f"- 信号日中次日大盘下跌占比: {pct_str((back['mkt_next'] < 0).mean())}\n")
        f.write(f"- 信号日中次日大盘大跌(≤-1%)占比: {pct_str((back['mkt_next'] <= -0.01).mean())}\n")
        f.write(f"- 信号日中买入日大盘下跌占比: {pct_str((back['mkt_buy'] < 0).mean())}\n")
        f.write(f"\n明细: {os.path.basename(out_csv)}｜按日: {os.path.basename(out_daily)}\n")

    back.to_csv(out_csv, index=False, encoding="utf-8-sig")
    daily.to_csv(out_daily, index=False, encoding="utf-8-sig")

    print("\n=== 回测结果 ===")
    print(stat_df.to_string(index=False))
    print("\n=== 月度 ===")
    print(monthly.to_string(index=False))
    print("\n=== 次日收盘收益分布 ===")
    for label, ratio in close_buckets:
        print(f"  {label}: {pct_str(ratio)}")
    print("=== 次日盘中最高收益分布 ===")
    for label, ratio in high_buckets:
        print(f"  {label}: {pct_str(ratio)}")
    print(f"\n报告: {out_md}")

    # 有效性校验: 8/18 的实盘候选是否被日线口径选中
    aug18 = back[pd.to_datetime(back["date"]).dt.strftime("%Y%m%d") == "20260818"]
    if not aug18.empty:
        print("\n8/18 回测信号:", sorted(aug18["code"].tolist()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
