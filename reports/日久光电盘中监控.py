#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日久光电(003015) 盘中监控脚本

用法:
    python3 日久光电盘中监控.py            # 单次刷新
    python3 日久光电盘中监控.py 120        # 每120秒自动刷新一次

关键价位（8/17 建立，成本取自券商持仓 12.036）:
    12.28  = 卖半线（冲高 >=12.28 卖一半；接近今日高点，注意冲高回落）
    11.80  = 止损线（跌破无条件走，成本-2%）
    12.036 = 券商成本价
    持仓   = 3,100 股（其中 2,500 股可卖，600 股 8/17 补仓）
"""

import sys
import time
import urllib.request

CODE = "sz003015"
COST = 12.036
STOP = 11.80
SELL_HALF = 12.28
SHARES = 3100


def fetch_quote() -> list:
    raw = urllib.request.urlopen(f"http://qt.gtimg.cn/q={CODE}", timeout=10).read().decode("gbk", errors="ignore")
    return raw.split("~")


def snapshot() -> None:
    f = fetch_quote()
    price = float(f[3])
    pct = float(f[32])
    high = float(f[33])
    low = float(f[34])
    opn = float(f[5])
    pre = float(f[4])
    gap = (opn / pre - 1) * 100 if pre else 0.0
    ts = f[30]
    pnl = (price - COST) * SHARES
    print(f"[{ts}] 日久光电 现价 {price} ({pct:+.2f}%) | 开 {opn} (高开{gap:+.2f}%) | 高 {high} 低 {low} | 昨收 {pre}")
    print(f"    对照: 成本 {COST} | 止损 {STOP} | 卖半线 {SELL_HALF} | 浮动盈亏 {pnl:+.0f} 元")
    if price <= STOP:
        print("    ⚠️ 触发止损线：建议立即卖出，无条件执行")
    elif price >= SELL_HALF:
        print("    ✅ 卖半线达标：可先卖一半，冲高 3-5% 清完")
    elif price < COST:
        print("    ⚠️ 已跌破成本：冲高乏力则走，破止损线必须走")
    else:
        print("    持有观察中：冲高到卖半线分批走 / 破 11.80 止损")


def main() -> None:
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    while True:
        try:
            snapshot()
        except Exception as e:
            print("获取行情失败:", e)
        if interval <= 0:
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
