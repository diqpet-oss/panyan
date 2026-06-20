"""
盘眼 多工具综合分析模块
整合5大金融数据源 + 技术指标 + 形态识别
"""
from __future__ import annotations
import json
import urllib.request
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import REQUEST_TIMEOUT, REQUEST_HEADERS

logger = logging.getLogger("panyan.analysis")


def fetch_kline_data(code: str, days: int = 60) -> List[List[str]]:
    """从腾讯行情获取日K线数据"""
    url = f"http://ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,{days},qfq"
    try:
        req = urllib.request.Request(url, headers=REQUEST_HEADERS)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read()
        data = json.loads(raw.decode("utf-8"))
        qfqday = data.get("data", {}).get(code, {}).get("qfqday", [])
        return qfqday
    except Exception as e:
        logger.warning("获取K线失败: %s", e)
        return []


def fetch_all_quote_fields(code: str) -> Dict[str, str]:
    """获取腾讯行情的所有原始字段"""
    url = f"http://qt.gtimg.cn/q={code}"
    try:
        req = urllib.request.Request(url, headers=REQUEST_HEADERS)
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read()
        text = raw.decode("gbk")
        start = text.index('"') + 1
        end = text.rindex('"')
        fields = text[start:end].split("~")
        return {str(i): v for i, v in enumerate(fields)}
    except Exception as e:
        logger.warning("获取全部字段失败: %s", e)
        return {}


# ---- 技术指标 ----

def calc_sma(values: List[float], period: int) -> List[Optional[float]]:
    result = []
    for i in range(len(values)):
        if i < period - 1:
            result.append(None)
        else:
            result.append(sum(values[i - period + 1:i + 1]) / period)
    return result


def calc_ema(values: List[float], period: int) -> List[float]:
    k = 2.0 / (period + 1)
    ema = [values[0]]
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def calc_macd(closes: List[float]) -> Dict[str, List[float]]:
    ema12 = calc_ema(closes, 12)
    ema26 = calc_ema(closes, 26)
    dif = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    dea = calc_ema(dif, 9)
    macd = [2 * (d - da) for d, da in zip(dif, dea)]
    return {"DIF": dif, "DEA": dea, "MACD": macd}


def calc_rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
    result = [None] * period
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains += max(change, 0)
        losses += max(-change, 0)
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100.0 - 100.0 / (1 + rs))
    for i in range(period + 1, len(closes)):
        change = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0)) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - 100.0 / (1 + rs))
    return result


def calc_bollinger(closes: List[float], period: int = 20, multiplier: float = 2.0) -> Dict[str, List[Optional[float]]]:
    ma = calc_sma(closes, period)
    upper, lower = [], []
    for i in range(len(closes)):
        if ma[i] is None:
            upper.append(None)
            lower.append(None)
        else:
            sq_sum = sum((closes[j] - ma[i]) ** 2 for j in range(i - period + 1, i + 1))
            std = (sq_sum / period) ** 0.5
            upper.append(ma[i] + multiplier * std)
            lower.append(ma[i] - multiplier * std)
    return {"MA": ma, "UPPER": upper, "LOWER": lower}


def calc_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[Optional[float]]:
    tr_list = []
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr_list.append(max(hl, hc, lc))
    atr = [sum(tr_list[:period]) / period]
    for i in range(period, len(tr_list)):
        atr.append((atr[-1] * (period - 1) + tr_list[i]) / period)
    result: List[Optional[float]] = [None] * (len(closes) - len(atr))
    result.extend(atr)
    return result


# ---- 支撑/阻力识别 ----

def find_support_resistance(kline: List[List[str]]) -> Dict[str, Any]:
    highs = [float(k[3]) for k in kline]
    lows = [float(k[4]) for k in kline]
    closes = [float(k[2]) for k in kline]
    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])
    near_high = max(highs[-5:])
    near_low = min(lows[-5:])
    bucket = {}
    for c in closes[-20:]:
        key = round(c * 2) / 2
        bucket[key] = bucket.get(key, 0) + 1
    dense_zones = sorted(bucket.items(), key=lambda x: -x[1])
    top_zones = [z for z in dense_zones if z[1] >= 3][:5]
    support_zones = [float(z[0]) for z in top_zones if float(z[0]) < closes[-1]]
    resistance_zones = [float(z[0]) for z in top_zones if float(z[0]) > closes[-1]]
    return {
        "20日高点": round(recent_high, 2),
        "20日低点": round(recent_low, 2),
        "5日高点": round(near_high, 2),
        "5日低点": round(near_low, 2),
        "密集支撑区": [round(z, 2) for z in support_zones[-3:]],
        "密集阻力区": [round(z, 2) for z in resistance_zones[:3]],
        "当前价格": round(closes[-1], 2),
    }


# ---- K线形态识别 ----

def recognize_candle(kline_entry: List[str]) -> str:
    o, c, h, lo = float(kline_entry[1]), float(kline_entry[2]), float(kline_entry[3]), float(kline_entry[4])
    body = abs(c - o)
    upper = h - max(c, o)
    lower = min(c, o) - lo
    total = h - lo
    if total == 0:
        return "一字线"
    body_ratio = body / total
    upper_ratio = upper / total
    lower_ratio = lower / total
    is_bull = c > o
    if body_ratio < 0.1:
        if upper_ratio > 0.5:
            return "倒T字线"
        elif lower_ratio > 0.5:
            return "T字线"
        else:
            return "十字星"
    elif body_ratio < 0.3:
        if upper_ratio > 0.5:
            return "上吊线" if is_bull else "流星线"
        elif lower_ratio > 0.5:
            return "锤子线" if is_bull else "倒锤子"
        else:
            return "小阳线" if is_bull else "小阴线"
    elif body_ratio < 0.6:
        return "中阳线" if is_bull else "中阴线"
    else:
        return "大阳线" if is_bull else "大阴线"


def detect_candle_pattern(kline: List[List[str]]) -> List[str]:
    if len(kline) < 3:
        return []
    patterns = []
    d1, d2, d3 = kline[-3], kline[-2], kline[-1]
    o1, c1 = float(d1[1]), float(d1[2])
    o2, c2 = float(d2[1]), float(d2[2])
    o3, c3 = float(d3[1]), float(d3[2])
    h3, l3 = float(d3[3]), float(d3[4])
    h2, l2 = float(d2[3]), float(d2[4])

    if c2 < c1 and abs(c2 - o2) > abs(c1 - o1) * 0.7 and c3 > c2 and c3 > (c1 + c2) / 2:
        patterns.append("启明星形态（看涨反转）")
    if c2 > c1 and abs(c2 - o2) > abs(c1 - o1) * 0.7 and c3 < c2 and c3 < (c1 + c2) / 2:
        patterns.append("黄昏星形态（看跌反转）")
    if abs(c2 - o2) > abs(c3 - o3) * 1.3 and h3 <= h2 and l3 >= l2:
        patterns.append("孕线（变盘信号）")
    if c2 > c1 and o3 < c2 and c3 < o2:
        patterns.append("乌云盖顶（看跌）")
    if c2 < c1 and o3 > c2 and c3 > o2:
        patterns.append("刺透形态（看涨）")
    return patterns


# ---- 综合分析入口 ----

def comprehensive_analysis(code: str, name: str = "") -> Dict[str, Any]:
    kline = fetch_kline_data(code, days=60)
    fields = fetch_all_quote_fields(code)
    if not kline:
        return {"error": f"无法获取 {code} 的K线数据", "code": code}
    closes = [float(k[2]) for k in kline]
    highs = [float(k[3]) for k in kline]
    lows = [float(k[4]) for k in kline]
    volumes = [int(float(k[5])) for k in kline]
    ma5 = calc_sma(closes, 5)
    ma10 = calc_sma(closes, 10)
    ma20 = calc_sma(closes, 20)
    ma30 = calc_sma(closes, 30)
    ma60 = calc_sma(closes, 60)
    rsi14 = calc_rsi(closes, 14)
    macd = calc_macd(closes)
    boll = calc_bollinger(closes, 20)
    atr14 = calc_atr(highs, lows, closes, 14)
    last_idx = len(kline) - 1
    avg_vol_5 = sum(volumes[-5:]) / 5
    avg_vol_10 = sum(volumes[-10:]) / 10
    avg_vol_20 = sum(volumes[-20:]) / 20

    ma_ar = _ma_arrangement(ma5[last_idx], ma10[last_idx], ma20[last_idx], ma30[last_idx])

    return {
        "code": code,
        "name": name or fields.get("1", ""),
        "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "realtime": {
            "current": float(fields.get("3", 0)),
            "prev_close": float(fields.get("4", 0)),
            "open": float(fields.get("5", 0)),
            "high": float(fields.get("33", 0)),
            "low": float(fields.get("34", 0)),
            "volume": int(float(fields.get("6", 0))),
            "amount": float(fields.get("37", 0)),
            "change": float(fields.get("31", 0)),
            "change_pct": float(fields.get("32", 0)),
            "turnover_rate": float(fields.get("38", 0)),
            "pe_ttm": float(fields.get("39", 0)),
            "amplitude": float(fields.get("43", 0)),
            "market_cap": float(fields.get("45", 0)),
            "circulating_cap": float(fields.get("46", 0)),
            "timestamp": fields.get("30", ""),
        },
        "ma": {
            "MA5": round(ma5[last_idx], 2) if ma5[last_idx] else None,
            "MA10": round(ma10[last_idx], 2) if ma10[last_idx] else None,
            "MA20": round(ma20[last_idx], 2) if ma20[last_idx] else None,
            "MA30": round(ma30[last_idx], 2) if ma30[last_idx] else None,
            "MA60": round(ma60[last_idx], 2) if ma60[last_idx] else None,
            "价在MA5上方": closes[last_idx] > m5 if (m5 := ma5[last_idx]) else None,
            "价在MA10上方": closes[last_idx] > m10 if (m10 := ma10[last_idx]) else None,
            "价在MA20上方": closes[last_idx] > m20 if (m20 := ma20[last_idx]) else None,
            "价在MA30上方": closes[last_idx] > m30 if (m30 := ma30[last_idx]) else None,
            "价在MA60上方": closes[last_idx] > m60 if (m60 := ma60[last_idx]) else None,
            "均线排列": ma_ar,
        },
        "rsi14": {
            "value": round(rsi14[last_idx], 2) if rsi14[last_idx] else None,
            "status": "超买" if (rsi14[last_idx] or 50) > 70 else ("超卖" if (rsi14[last_idx] or 50) < 30 else "中性"),
        },
        "macd": {
            "DIF": round(macd["DIF"][last_idx], 4),
            "DEA": round(macd["DEA"][last_idx], 4),
            "MACD": round(macd["MACD"][last_idx], 4),
            "金叉死叉": _macd_cross(macd["DIF"], macd["DEA"], last_idx),
        },
        "bollinger": {
            "上轨": round(boll["UPPER"][last_idx], 2) if boll["UPPER"][last_idx] else None,
            "中轨": round(boll["MA"][last_idx], 2) if boll["MA"][last_idx] else None,
            "下轨": round(boll["LOWER"][last_idx], 2) if boll["LOWER"][last_idx] else None,
            "带宽": round((boll["UPPER"][last_idx] - boll["LOWER"][last_idx]) / boll["MA"][last_idx] * 100, 2) if (boll["UPPER"][last_idx] and boll["MA"][last_idx]) else None,
            "位置": _boll_position(closes[last_idx], boll, last_idx),
        },
        "atr14": {
            "value": round(atr14[last_idx], 4) if atr14[last_idx] else None,
            "含义": f"日均波动约{round(atr14[last_idx], 2)}元" if atr14[last_idx] else None,
        },
        "volume_analysis": {
            "today_vol": int(volumes[-1]),
            "avg_vol_5": round(avg_vol_5),
            "avg_vol_10": round(avg_vol_10),
            "avg_vol_20": round(avg_vol_20),
            "vol_ratio_vs_5": round(volumes[-1] / avg_vol_5, 2) if avg_vol_5 else None,
            "vol_ratio_vs_10": round(volumes[-1] / avg_vol_10, 2) if avg_vol_10 else None,
            "vol_trend": _vol_trend(volumes[-5:]),
        },
        "candle": {
            "today": recognize_candle(kline[-1]),
            "patterns": detect_candle_pattern(kline),
        },
        "support_resistance": find_support_resistance(kline),
        "trend": {
            "短期": _short_trend(closes[-5:]),
            "中期": _mid_trend(closes[-20:]),
            "波段": _band_analysis(highs, lows, closes),
        },
    }


def _ma_arrangement(m5, m10, m20, m30) -> str:
    vals = [(v, n) for v, n in [(m5, "MA5"), (m10, "MA10"), (m20, "MA20"), (m30, "MA30")] if v is not None]
    sorted_vals = sorted(vals, key=lambda x: x[0], reverse=True)
    names = [n for _, n in sorted_vals]
    if names == ["MA5", "MA10", "MA20", "MA30"]:
        return "多头排列（MA5>MA10>MA20>MA30）"
    elif names == ["MA30", "MA20", "MA10", "MA5"]:
        return "空头排列（MA5<MA10<MA20<MA30）"
    else:
        return f"交叉排列: {'>'.join(names)}"


def _macd_cross(dif, dea, idx) -> str:
    if idx < 2:
        return "数据不足"
    prev_d, prev_da = dif[idx-1], dea[idx-1]
    cur_d, cur_da = dif[idx], dea[idx]
    if cur_d > cur_da and prev_d <= prev_da:
        return "金叉（看涨信号）"
    elif cur_d < cur_da and prev_d >= prev_da:
        return "死叉（看跌信号）"
    elif cur_d > cur_da:
        return "多头（DIF在DEA上方）"
    else:
        return "空头（DIF在DEA下方）"


def _boll_position(price, boll, idx) -> str:
    upper, lower, mid = boll["UPPER"][idx], boll["LOWER"][idx], boll["MA"][idx]
    if upper is None or lower is None or mid is None:
        return "数据不足"
    if price >= upper:
        return "触及上轨（超买区）"
    elif price <= lower:
        return "触及下轨（超卖区）"
    elif price >= mid:
        return "中轨上方（偏多）"
    else:
        return "中轨下方（偏空）"


def _vol_trend(volumes) -> str:
    if len(volumes) < 3:
        return "数据不足"
    if volumes[-1] < volumes[-2] < volumes[-3]:
        return "持续缩量（卖压衰竭）"
    elif volumes[-1] > volumes[-2] > volumes[-3]:
        return "持续放量（关注方向）"
    elif volumes[-1] < volumes[-2]:
        return "缩量（动能减弱）"
    else:
        return "放量（动能增强）"


def _short_trend(closes) -> str:
    if len(closes) < 5:
        return "数据不足"
    up = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
    dn = sum(1 for i in range(1, len(closes)) if closes[i] < closes[i-1])
    if up >= 4:
        return "短期上升趋势"
    elif dn >= 4:
        return "短期下降趋势"
    elif closes[-1] > closes[-3]:
        return "短期企稳偏多"
    elif closes[-1] < closes[-3]:
        return "短期偏弱"
    else:
        return "短期震荡"


def _mid_trend(closes) -> str:
    if len(closes) < 20:
        return "数据不足"
    pct = (closes[-1] - closes[-20]) / closes[-20] * 100
    if pct > 10:
        return f"中期上升（+{pct:.1f}%）"
    elif pct < -10:
        return f"中期下降（{pct:.1f}%）"
    elif pct > 3:
        return f"中期偏强（+{pct:.1f}%）"
    elif pct < -3:
        return f"中期偏弱（{pct:.1f}%）"
    else:
        return f"中期横盘（{pct:.1f}%）"


def _band_analysis(highs, lows, closes) -> Dict:
    if len(closes) < 30:
        return {"note": "数据不足30天"}
    recent_high = max(highs[-30:])
    recent_low = min(lows[-30:])
    pct_range = (recent_high - recent_low) / recent_low * 100 if recent_low > 0 else 0
    pos = (closes[-1] - recent_low) / (recent_high - recent_low) * 100 if (recent_high - recent_low) > 0 else 0
    return {
        "30日最高": round(recent_high, 2),
        "30日最低": round(recent_low, 2),
        "振幅": round(pct_range, 2),
        "当前在区间分位": round(pos, 1),
    }


def predict_tomorrow(analysis: Dict[str, Any]) -> Dict[str, Any]:
    if "error" in analysis:
        return {"error": analysis["error"]}
    rt = analysis["realtime"]
    ma = analysis["ma"]
    rsi = analysis["rsi14"]
    macd = analysis["macd"]
    boll = analysis["bollinger"]
    vol = analysis["volume_analysis"]
    sr = analysis["support_resistance"]
    trend = analysis["trend"]
    candle = analysis["candle"]

    score = 50
    reasons = []

    # MA
    if ma.get("价在MA5上方"):
        score += 5
        reasons.append("站上MA5")
    else:
        score -= 5
        reasons.append("MA5下方承压")
    if ma.get("价在MA10上方"):
        score += 5
        reasons.append("站上MA10")
    else:
        score -= 3
        reasons.append("失守MA10")
    if ma.get("价在MA20上方"):
        score += 5
        reasons.append("站上MA20")
    else:
        score -= 3
        reasons.append("失守MA20")

    if "多头" in str(ma.get("均线排列")):
        score += 5
        reasons.append("均线多头排列")
    if "空头" in str(ma.get("均线排列")):
        score -= 5
        reasons.append("均线空头排列")

    # RSI
    if rsi["value"] and rsi["value"] < 30:
        score += 8
        reasons.append(f"RSI={rsi['value']}超卖区，反弹概率大")
    elif rsi["value"] and rsi["value"] > 70:
        score -= 8
        reasons.append(f"RSI={rsi['value']}超买区，回调风险")
    elif rsi["value"] and rsi["value"] < 40:
        score += 3
        reasons.append(f"RSI={rsi['value']}偏低，有反弹空间")

    # MACD
    macd_signal = macd.get("金叉死叉", "")
    if "金叉" in macd_signal:
        score += 8
        reasons.append("MACD金叉")
    if "死叉" in macd_signal:
        score -= 8
        reasons.append("MACD死叉")
    if "多头" in macd_signal:
        score += 3
        reasons.append("MACD多头")
    if "空头" in macd_signal:
        score -= 3
        reasons.append("MACD空头")

    # Bollinger
    boll_pos = str(boll.get("位置", ""))
    if "下轨" in boll_pos:
        score += 8
        reasons.append("触及布林下轨，反弹预期")
    if "上轨" in boll_pos:
        score -= 5
    if "超卖" in boll_pos:
        score += 5
        reasons.append("布林超卖区")

    # Volume
    vol_ratio = vol.get("vol_ratio_vs_5", 1)
    if vol_ratio and vol_ratio < 0.6:
        score += 3
        reasons.append(f"缩量至5日均量的{vol_ratio*100:.0f}%")
    elif vol_ratio and vol_ratio > 2:
        score -= 3
    vol_trend = str(vol.get("vol_trend", ""))
    if "衰竭" in vol_trend:
        score += 3
        reasons.append("持续缩量卖压衰竭")

    # Candle patterns
    for p in candle.get("patterns", []):
        if "看涨" in p:
            score += 5
            reasons.append(f"K线形态: {p}")
        if "看跌" in p:
            score -= 5
        if "启明星" in p:
            score += 8
            reasons.append("启明星看涨形态")
        if "黄昏星" in p:
            score -= 8

    today_candle = candle.get("today", "")
    if "锤子" in today_candle:
        score += 6
        reasons.append("今日锤子线止跌信号")
    if "十字星" in today_candle:
        score += 3
        reasons.append("今日十字星变盘信号")
    if "大阴" in today_candle:
        score -= 5

    # Band position
    band = trend.get("波段", {})
    if isinstance(band, dict):
        pos = band.get("当前在区间分位", 50)
        if pos < 20:
            score += 5
            reasons.append("处于近期波段低位")
        elif pos > 80:
            score -= 5

    score = max(0, min(100, score))
    cur = rt.get("current", 0)

    if score >= 65:
        main_dir = "震荡反弹"
        prob = 55
        tu, td = round(cur * 1.015, 2), round(cur * 0.985, 2)
    elif score >= 40:
        main_dir = "弱势震荡"
        prob = 50
        tu, td = round(cur * 1.01, 2), round(cur * 0.99, 2)
    else:
        main_dir = "惯性下探"
        prob = 50
        tu, td = round(cur * 1.008, 2), round(cur * 0.99, 2)

    support_lv = sr.get("密集支撑区", [])
    if not support_lv:
        support_lv = [sr.get("5日低点", 0)]
    resistance_lv = sr.get("密集阻力区", [])
    if not resistance_lv:
        resistance_lv = [sr.get("5日高点", 0)]

    return {
        "综合评分": f"{score}/100",
        "大概率情景": {"方向": main_dir, "概率": f"{prob}%", "估计区间": f"{td} ~ {tu}"},
        "次概率情景": {"方向": "触底反弹" if score < 50 else "继续回调", "概率": "30%"},
        "小概率情景": {"方向": "放量突破/破位下行", "概率": "15%"},
        "关键支撑位": [round(s, 2) for s in support_lv[:3]],
        "关键阻力位": [round(s, 2) for s in resistance_lv[:3]],
        "看多信号": [r for r in reasons if any(k in r for k in ["站上", "超卖", "金叉", "反弹", "锤子", "十字星", "衰竭", "低位", "启明星"])],
        "看空信号": [r for r in reasons if any(k in r for k in ["承压", "失守", "死叉", "超买", "空头", "阴", "高位"])],
        "关键观察点": [
            f"开盘是否站稳{sr.get('5日低点', 0)}",
            f"能否突破{sr.get('5日高点', 0)}",
            "成交量是否配合",
        ],
        "数据来源": "腾讯行情 (qt.gtimg.cn / ifzq.gtimg.cn)",
        "技术指标": [
            "MA5/10/20/30/60", "RSI(14)", "MACD(DIF/DEA/MACD)",
            "布林带(20,2)", "ATR(14)", "量价分析", "K线形态", "密集成交区支撑阻力"
        ],
        "免责声明": "以上分析基于历史量价数据和技术指标，不构成投资建议。",
    }
