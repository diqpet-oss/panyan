#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""老顾持仓监控（盯盘）

用法:
    python3 reports/老顾持仓监控.py            # 单次快照
    python3 reports/老顾持仓监控.py 300        # 每300秒刷新一次（盘中）
    python3 reports/老顾持仓监控.py --cron     # 定时任务用：仅交易时段输出一次

持仓与警报线从 reports/老顾持仓.csv 读取（code,name,cost,shares,stop,sell_half,note）。
仅交易时段（9:30-11:30, 13:00-15:00，周一至周五）输出；其他时间静默退出。
"""

import csv
import sys
import time
import urllib.request
from datetime import datetime

POS_FILE = "reports/老顾持仓.csv"


def load_positions() -> list[dict]:
    rows = []
    with open(POS_FILE, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            r["cost"] = float(r["cost"])
            r["shares"] = int(r["shares"])
            r["stop"] = float(r["stop"])
            r["sell_half"] = float(r["sell_half"])
            r["tshares"] = int(float(r.get("today_shares") or 0))
            r["tcost"] = float(r.get("today_cost") or 0) or r["cost"]
            rows.append(r)
    return rows


def in_trading_hours(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    hm = now.strftime("%H:%M")
    return ("09:30" <= hm <= "11:30") or ("13:00" <= hm <= "15:00")


def fetch_quotes(codes: list[str]) -> dict:
    syms = []
    for c in codes:
        syms.append(("sh" if c.startswith("6") else "sz") + c)
    raw = urllib.request.urlopen("http://qt.gtimg.cn/q=" + ",".join(syms), timeout=10).read().decode("gbk", "ignore")
    out = {}
    for line in raw.strip().split(";"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        f = line.split('"')[1].split("~")
        out[f[2]] = {
            "name": f[1],
            "price": float(f[3]),
            "prev": float(f[4]),
            "pct": float(f[32]),
            "high": float(f[33]),
            "low": float(f[34]),
            "amount_yi": float(f[37]) / 1e4,
        }
    return out


def snapshot() -> None:
    pos = load_positions()
    q = fetch_quotes([p["code"] for p in pos])
    total_value = 0.0
    total_cost = 0.0
    total_today = 0.0
    total_account = 0.0
    print(f"\n===== 老顾持仓盯盘 [{datetime.now():%m-%d %H:%M:%S}] =====")
    print(f"{'名称':<8}{'现价':>8}{'今日':>8}{'成本':>8}{'市值':>10}{'浮盈亏':>10}{'今日盈亏':>10}{'账户当日':>10}  信号")
    for p in pos:
        qd = q.get(p["code"])
        if not qd:
            continue
        price = qd["price"]
        value = price * p["shares"]
        cost_v = p["cost"] * p["shares"]
        pnl = value - cost_v
        tsh = p["tshares"]
        today_pnl = (price - qd["prev"]) * p["shares"]
        account_pnl = (price - qd["prev"]) * (p["shares"] - tsh) + (price - p["tcost"]) * tsh
        total_value += value
        total_cost += cost_v
        total_today += today_pnl
        total_account += account_pnl
        sig = ""
        if price <= p["stop"]:
            sig = "⚠️ 触发止损线"
        elif price >= p["sell_half"]:
            sig = "✅ 达到卖半/止盈线"
        elif pnl < 0:
            sig = "⚪ 浮亏持有"
        else:
            sig = "🟢 浮盈持有"
        print(f"{qd['name']:<8}{price:>8.2f}{qd['pct']:>+7.2f}%{p['cost']:>8.3f}"
              f"{value:>10,.0f}{pnl:>+10,.0f}{today_pnl:>+10,.0f}{account_pnl:>+10,.0f}{'*' if tsh else '':>1}  {sig}")
    print(f"{'合计':<8}{'':>8}{'':>8}{'':>8}{total_value:>10,.0f}{total_value - total_cost:>+10,.0f}"
          f"{total_today:>+10,.0f}{total_account:>+10,.0f}*")
    print(f"总市值 {total_value:,.0f} 元 | 总浮盈 {total_value - total_cost:+,.0f} 元"
          f" ({(total_value/total_cost-1)*100:+.1f}%) | 今日(盘面) {total_today:+,.0f} | 账户当日(估) {total_account:+,.0f} 元")


def main() -> int:
    args = sys.argv[1:]
    cron_mode = "--cron" in args
    interval = int(args[0]) if args and args[0].isdigit() else 0
    while True:
        now = datetime.now()
        if in_trading_hours(now) or (not cron_mode and interval == 0):
            try:
                snapshot()
            except Exception as e:
                print(f"[{now:%H:%M:%S}] 获取行情失败: {e}")
        if interval <= 0:
            break
        time.sleep(interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
