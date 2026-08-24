#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主力资金监控 — 老顾持仓（2026-08-21 版）

五路数据源（东财 push2his/北向持股明细已因规则与代理不可用，改用以下通道）:
  1. 新浪 MoneyFlow        个股主力/超大单净流入（近10个交易日）
  2. 深交所/上交所         融资融券余额（最新两日对比）
  3. 东财 datacenter       股东户数变化（筹码集中/分散）
  4. 东财 datacenter       基金持仓榜（持有基金家数 + 加减仓）
  5. 新浪 龙虎榜个股统计    上榜次数 + 净买入额

输出:
  - reports/主力资金监控_YYYYMMDD.md   详细报告
  - reports/主力资金监控_YYYYMMDD.json 结构化数据
  - 注入 reports/老顾盯盘.html          盘面资金面板
"""

from __future__ import annotations

import csv
import json
import os
import socket
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

socket.setdefaulttimeout(15)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(BASE, "reports")
POS_FILE = os.path.join(REPORTS, "老顾持仓.csv")
HTML_FILE = os.path.join(REPORTS, "老顾盯盘.html")
TODAY = datetime.now().strftime("%Y%m%d")

H = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"}


def http_json(url: str, retries: int = 2):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=H)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if i < retries:
                import time
                time.sleep(0.4 * (i + 1))
    return {}


def load_positions() -> list[dict]:
    with open(POS_FILE, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def tx_symbol(code: str) -> str:
    return ("sh" if code.startswith("6") else "sz") + code


def last_trading_dates(n: int = 10) -> list[str]:
    """从腾讯指数日K取最近 n 个交易日 YYYY-MM-DD"""
    end = datetime.now()
    start = end - timedelta(days=120)
    url = ("http://ifzq.gtimg.cn/appstock/app/fqkline/get?"
           f"param=sh000001,day,{start:%Y-%m-%d},{end:%Y-%m-%d},200,")
    data = http_json(url)
    try:
        rows = data["data"]["sh000001"]["day"]
    except (KeyError, TypeError):
        return []
    return [r[0] for r in rows][-n:]


def sina_money_flow(code: str) -> list[dict]:
    """新浪个股资金流历史（10日）: netamount=主力净流入, r0_net=超大单净流入"""
    url = ("http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
           f"MoneyFlow.ssl_qsfx_zjlrqs?page=1&num=20&sort=opendate&asc=0&daima={tx_symbol(code)}")
    data = http_json(url)
    if not isinstance(data, list):
        return []
    out = []
    for r in data:
        try:
            out.append({
                "date": r["opendate"],
                "net": float(r["netamount"]),
                "r0": float(r.get("r0_net") or 0),
                "pct": float(r.get("changeratio") or 0) * 100,
            })
        except (KeyError, ValueError, TypeError):
            continue
    out.reverse()  # 接口返回最新在前，翻转为时间正序
    return out[-10:]


def lhb_stat_sina(code: str) -> dict:
    """新浪龙虎榜个股统计（近60日口径）"""
    try:
        import akshare as ak
        df = ak.stock_lhb_ggtj_sina(symbol=code)
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    row = df.iloc[0]
    try:
        return {
            "times": int(row["上榜次数"]),
            "net": float(row["净额"]),
            "buy": float(row["累积购买额"]),
            "sell": float(row["累积卖出额"]),
            "buy_seats": int(row["买入席位数"]),
            "sell_seats": int(row["卖出席位数"]),
        }
    except (KeyError, ValueError, TypeError):
        return {}


def margin_balance(code: str, date: str) -> float | None:
    """取某交易日融资余额（深交所/上交所）"""
    try:
        import akshare as ak
        d = date.replace("-", "")
        if code.startswith("6"):
            df = ak.stock_margin_detail_sse(date=d)
        else:
            df = ak.stock_margin_detail_szse(date=d)
        col = "融资余额"
        hit = df[df["证券代码"].astype(str) == code]
        if hit.empty:
            return None
        return float(hit.iloc[0][col])
    except Exception:
        return None


def gdhs_latest(code: str) -> dict:
    """东财股东户数：取最新一期增减比例"""
    try:
        import akshare as ak
        df = ak.stock_zh_a_gdhs_detail_em(symbol=code)
    except Exception:
        return {}
    if df is None or df.empty:
        return {}
    row = df.iloc[-1]
    try:
        return {
            "date": str(row["股东户数统计截止日"]),
            "holders": int(row["股东户数-本次"]),
            "chg_pct": float(row["股东户数-增减比例"]),
            "per_hold": float(row["户均持股数量"]),
        }
    except (KeyError, ValueError, TypeError):
        return {}


def fund_hold(code: str) -> dict:
    """东财基金持仓榜：最新季度基金家数与加减仓"""
    try:
        import akshare as ak
        for q in ("20260630", "20260331"):
            df = ak.stock_report_fund_hold(symbol="基金持仓", date=q)
            if df is None or df.empty:
                continue
            hit = df[df["股票代码"].astype(str) == code]
            if not hit.empty:
                row = hit.iloc[0]
                return {
                    "quarter": q,
                    "funds": int(row["持有基金家数"]),
                    "trend": str(row["持股变化"]),
                    "chg_pct": float(row["持股变动比例"]),
                }
    except Exception:
        pass
    return {}


def score_label(signals: dict) -> tuple[int, str]:
    score = 0
    if signals.get("主力5日净流入") == "流入":
        score += 1
    elif signals.get("主力5日净流入") == "流出":
        score -= 1
    if signals.get("超大单5日净流入") == "流入":
        score += 1
    elif signals.get("超大单5日净流入") == "流出":
        score -= 1
    if signals.get("两融5日") == "加杠杆":
        score += 1
    elif signals.get("两融5日") == "降杠杆":
        score -= 1
    if signals.get("股东户数") == "集中":
        score += 1
    elif signals.get("股东户数") == "分散":
        score -= 1
    if signals.get("基金持仓") == "加仓":
        score += 1
    elif signals.get("基金持仓") == "减仓":
        score -= 1
    if signals.get("龙虎榜") == "净买":
        score += 1
    elif signals.get("龙虎榜") == "净卖":
        score -= 1
    if score >= 3:
        label = "主力增持"
    elif score >= 1:
        label = "偏多"
    elif score == 0:
        label = "中性"
    elif score >= -2:
        label = "偏空"
    else:
        label = "主力减持"
    return score, label


def analyze_stock(pos: dict, margin_dates: list[str]) -> dict:
    code = pos["code"]
    name = pos["name"]
    mf = sina_money_flow(code)
    mf5 = mf[-5:] if mf else []
    mf10 = mf[-10:] if mf else []
    net5 = sum(x["net"] for x in mf5)
    r0_5 = sum(x["r0"] for x in mf5)
    net10 = sum(x["net"] for x in mf10)
    last = mf[-1] if mf else None

    # 两融：从最新日往回找两个有效交易日
    margin = {}
    for d in reversed(margin_dates):
        v = margin_balance(code, d)
        if v is not None:
            margin[d] = v
        if len(margin) >= 2:
            break
    if len(margin) >= 2:
        dates = sorted(margin.keys())
        m_old, m_new = margin[dates[-2]], margin[dates[-1]]
        margin_chg = (m_new - m_old) / m_old * 100 if m_old else 0
        margin_signal = "加杠杆" if margin_chg > 0 else "降杠杆"
    else:
        margin_chg = None
        margin_signal = "数据不足"

    gd = gdhs_latest(code)
    if gd and gd.get("chg_pct") is not None:
        gd_signal = "集中" if gd["chg_pct"] < 0 else "分散"
    else:
        gd_signal = "数据不足"

    fh = fund_hold(code)
    if fh:
        fh_signal = ("加仓" if fh["trend"] in ("加仓", "增持", "新进", "增仓")
                     else "减仓" if fh["trend"] in ("减仓", "减持", "退出")
                     else "持平")
    else:
        fh_signal = "数据不足"

    lhb = lhb_stat_sina(code)
    if lhb:
        lhb_signal = "净买" if lhb["net"] > 0 else "净卖"
    else:
        lhb_signal = "未上榜"

    signals = {
        "主力5日净流入": "流入" if net5 > 0 else ("流出" if net5 < 0 else "持平"),
        "超大单5日净流入": "流入" if r0_5 > 0 else ("流出" if r0_5 < 0 else "持平"),
        "两融5日": margin_signal,
        "股东户数": gd_signal,
        "基金持仓": fh_signal,
        "龙虎榜": lhb_signal,
    }
    score, label = score_label(signals)

    if last:
        last_note = (f"最近交易日({last['date']})主力净流入 "
                     f"{last['net'] / 1e8:+.2f}亿")
    else:
        last_note = "资金流数据缺失"

    return {
        "code": code,
        "name": name,
        "score": score,
        "label": label,
        "note": last_note,
        "net5_yi": net5 / 1e8,
        "r0_5_yi": r0_5 / 1e8,
        "net10_yi": net10 / 1e8,
        "margin_chg_pct": margin_chg,
        "gd_chg_pct": gd.get("chg_pct") if gd else None,
        "gd_holders": gd.get("holders") if gd else None,
        "fund_funds": fh.get("funds") if fh else None,
        "fund_trend": fh.get("trend") if fh else None,
        "lhb_times": lhb.get("times", 0),
        "lhb_net_yi": lhb.get("net", 0) / 1e8 if lhb else 0,
        "signals": signals,
    }


def build_html_panel(results: list[dict], meta: str) -> str:
    def cls(x: float) -> str:
        return "up" if x > 0 else ("down" if x < 0 else "")
    rows = []
    for r in results:
        lbl = r["label"]
        lbl_cls = {"主力增持": "up", "偏多": "up", "中性": "", "偏空": "down", "主力减持": "down"}[lbl]
        gd = f"{r['gd_chg_pct']:+.1f}%" if r["gd_chg_pct"] is not None else "—"
        fh = r["fund_trend"] or "—"
        if r["fund_funds"] is not None:
            fh += f"({r['fund_funds']}家)"
        lhb = "未上榜"
        if r["lhb_times"]:
            lhb = f"{r['lhb_times']}次 {r['lhb_net_yi']:+.2f}亿"
        if r["margin_chg_pct"] is not None:
            margin_cell = (f"<td class='{cls(r['margin_chg_pct'])}'>"
                           f"{r['margin_chg_pct']:+.1f}%</td>")
        else:
            margin_cell = "<td>—</td>"
        rows.append(
            f"<tr><td>{r['name']}</td>"
            f"<td class='{lbl_cls}' style='font-weight:700'>{lbl}({r['score']:+d})</td>"
            f"<td class='{cls(r['net5_yi'])}'>{r['net5_yi']:+.2f}亿</td>"
            f"<td class='{cls(r['r0_5_yi'])}'>{r['r0_5_yi']:+.2f}亿</td>"
            f"{margin_cell}"
            f"<td class='{cls(r['gd_chg_pct'] or 0)}'>{gd}</td>"
            f"<td>{fh}</td><td>{lhb}</td></tr>"
        )
    return (
        "<!--FUNDS_START--><div id='fundsPanel' style='margin-top:16px;"
        "border-top:1px solid #232830;padding-top:10px'>"
        "<div style='font-size:15px;font-weight:700'>主力资金监控</div>"
        f"<div class='meta'>{meta}</div>"
        "<table style='margin-top:6px'><thead><tr>"
        "<th>股票</th><th>主力判断</th><th>5日主力净流入</th><th>5日超大单</th>"
        "<th>两融余额变化</th><th>股东户数变化</th><th>基金持仓</th><th>龙虎榜(60日)</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        "<div class='foot'>口径: 新浪主力资金流 · 两融(交易所) · 股东户数(东财) · 基金季报 · 新浪龙虎榜；"
        "北向个股持股明细自2024-08起停止披露，已剔除该维度。综合分≥3=主力增持 / ≥1=偏多 / 0=中性 / ≤-1=偏空 / ≤-3=减持。</div>"
        "</div><!--FUNDS_END-->"
    )


def main() -> int:
    positions = load_positions()
    dates = last_trading_dates(8)
    if len(dates) < 6:
        print("交易日历获取失败")
        return 1
    # 最新两个已完成交易日做两融对比
    margin_dates = dates[-2:]
    print(f"持仓 {len(positions)} 只，两融对比日期: {margin_dates}")

    results = []
    for pos in positions:
        print(f"分析 {pos['name']} ({pos['code']}) …")
        r = analyze_stock(pos, dates)
        results.append(r)
        s = r["signals"]
        print(f"  {r['label']}({r['score']:+d}) 5日主力{r['net5_yi']:+.2f}亿 "
              f"超大单{r['r0_5_yi']:+.2f}亿 两融{s['两融5日']} 户数{s['股东户数']} "
              f"基金{s['基金持仓']} 龙虎榜{s['龙虎榜']}")

    md = os.path.join(REPORTS, f"主力资金监控_{TODAY}.md")
    js = os.path.join(REPORTS, f"主力资金监控_{TODAY}.json")
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# 主力资金监控 · 老顾持仓（{TODAY}）\n\n")
        f.write("| 股票 | 主力判断 | 5日主力净流入 | 5日超大单 | 10日主力 | 两融余额变化 | 股东户数 | 基金持仓 | 龙虎榜 |\n|---|---|---|---|---|---|---|---|---|\n")
        for r in results:
            gd = f"{r['gd_chg_pct']:+.1f}%" if r["gd_chg_pct"] is not None else "—"
            fh = r["fund_trend"] or "—"
            if r["fund_funds"] is not None:
                fh += f"({r['fund_funds']}家)"
            lhb = "未上榜"
            if r["lhb_times"]:
                lhb = f"{r['lhb_times']}次 {r['lhb_net_yi']:+.2f}亿"
            mg = f"{r['margin_chg_pct']:+.1f}%" if r["margin_chg_pct"] is not None else "—"
            f.write(f"| {r['name']} | {r['label']}({r['score']:+d}) | "
                    f"{r['net5_yi']:+.2f}亿 | {r['r0_5_yi']:+.2f}亿 | {r['net10_yi']:+.2f}亿 | "
                    f"{mg} | {gd} | {fh} | {lhb} |\n")
        f.write(f"\n{r['note']}\n" if results else "")
        f.write("\n> 北向个股持股明细自2024-08起停止披露；东财行情接口受限。数据仅供研究参考。\n")
    with open(js, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    # 注入盯盘页
    meta = f"盘后更新 {datetime.now():%m-%d %H:%M}｜五路口径：主力资金流/两融/股东户数/基金持仓/龙虎榜"
    panel = build_html_panel(results, meta)
    with open(HTML_FILE, encoding="utf-8") as f:
        html = f.read()
    if "<!--FUNDS_START-->" in html:
        start = html.find("<!--FUNDS_START-->")
        end = html.find("<!--FUNDS_END-->", start)
        if end != -1:
            end += len("<!--FUNDS_END-->")
        if start != -1 and end != -1:
            html = html[:start] + panel + html[end:]
    else:
        html = html.replace("</body>", panel + "\n</body>")
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n报告: {md}\nJSON: {js}\n已注入: {HTML_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
