#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""顺络电子(002138) 盘中监控脚本

用法:
    python3 顺络电子盘中监控.py            # 单次刷新
    python3 顺络电子盘中监控.py 120        # 每120秒自动刷新一次

关键价位（8/17 按用户计划更新）:
    53.20  = 卖半线（冲高 >=53.20 卖一半，冲高 3-5% 清完）
    51.07  = 止损线（跌破无条件走）
    52.21  = 券商成本价（8/14 尾盘买入价 52.112）
    持仓   = 400 股
"""

import sys
import time
import urllib.request

CODE = "sz002138"
COST = 52.21          # 券商成本价（含费）
BUY = 52.112          # 8/14 尾盘买入价
STOP = 51.07          # 无条件止损线（用户指定）
SELL_HALF = 53.20     # 卖半线（用户指定）
SHARES = 400          # 持仓股数


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
    print(f"[{ts}] 顺络电子 现价 {price} ({pct:+.2f}%) | 开 {opn} (高开{gap:+.2f}%) | 高 {high} 低 {low} | 昨收 {pre}")
    print(f"    对照: 成本 {COST} | 止损 {STOP} | 卖半线 {SELL_HALF} | 浮动盈亏 {pnl:+.0f} 元")
    if price <= STOP:
        print("    ⚠️ 触发止损线：建议立即卖出，无条件执行")
    elif price >= SELL_HALF:
        print("    ✅ 卖半线达标：可先卖一半，冲高 3-5% 清完")
    elif price < COST:
        print("    ⚠️ 已跌破成本：冲高乏力则走，破止损线必须走")
    else:
        print("    持有观察中：按 10:00 前不冲高即走 / 破 51.07 止损 执行")


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
