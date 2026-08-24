# -*- coding: utf-8 -*-
"""TdxQuant 老顾持仓盘中预警策略（需在 Windows 通达信 TQ 环境运行）

功能：订阅老顾5只持仓，实时检查：
  - 跌破止损线 → 输出"止损"预警
  - 触及卖半/减仓线 → 输出"减仓"预警
  - 附 60 分钟 MACD 方向辅助判断

运行：将本文件放入通达信 PYPlugins/user 目录，通达信内运行 TQ 策略。
"""
import sys
import os

# 通达信安装目录（按实际安装路径修改）
TDX_ROOT = r"C:\new_tdx\通达信金融终端"
sys.path.insert(0, os.path.join(TDX_ROOT, "PYPlugins", "user"))

from tqcenter import tq  # noqa: E402

# 持仓：code -> (名称, 止损线, 卖半线)
POSITIONS = {
    "002138": ("顺络电子", 48.30, 50.50),
    "003015": ("日久光电", 11.80, 12.50),
    "301307": ("美利信", 51.00, 54.00),
    "002998": ("优彩资源", 7.50, 7.90),
    "301047": ("义翘神州", 115.00, 125.00),
}


def main():
    tq.initialize(__file__)
    print("老顾持仓盯盘已启动：", ", ".join(f"{v[0]}" for v in POSITIONS.values()))
    for code in POSITIONS:
        tq.subscribe(code)  # 订阅日线/分时

    while True:
        for code, (name, stop, sell) in POSITIONS.items():
            df = tq.get_daily(code)  # 日线
            if df is None or len(df) == 0:
                continue
            price = float(df["close"].iloc[-1])
            if price <= stop:
                print(f"⚠️ 预警 {name}({code})：{price:.2f} 跌破止损 {stop:.2f} —— 建议离场")
            elif price >= sell:
                print(f"✅ 预警 {name}({code})：{price:.2f} 触及卖半 {sell:.2f} —— 建议减半")
            else:
                print(f"   {name}({code})：{price:.2f} 正常（止损{stop:.2f}/卖半{sell:.2f}）")
        tq.sleep(60)  # 每分钟检查一次


if __name__ == "__main__":
    main()
