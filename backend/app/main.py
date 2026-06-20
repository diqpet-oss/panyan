"""
盘眼 (PanYan) - 五工具统一实时分析系统
FastAPI 后端入口

P0 实现：实时行情面板 + 数据源健康监控
"""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    DEFAULT_WATCHLIST, QUOTE_REFRESH_INTERVAL, ALERT_CHANGE_PCT, ALERT_VOLUME_SURGE, ALERT_AMPLITUDE,
    BACKEND_PORT,
)
from .models import (
    StockQuote, IndexQuote, Alert, WSMessage, MarketSnapshot,
)
from .quote import (
    fetch_all_quotes, fetch_index_quotes, fetch_index_quotes_yf,
    get_health_snapshot,
)
from .knowledge_base import (
    KnowledgeEngine, BehavioralFinanceFramework, HistoryLessonsFramework,
)
from .db import init_db, load_watchlist, save_watchlist, add_watchlist_item, remove_watchlist_item

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("panyan")

app = FastAPI(title="盘眼 PanYan", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AppState:
    def __init__(self):
        db_codes = load_watchlist()
        self.watchlist: List[str] = db_codes if db_codes else list(DEFAULT_WATCHLIST)
        self.last_quotes: Dict[str, StockQuote] = {}
        self.last_indices: Dict[str, IndexQuote] = {}
        self.last_snapshot: Optional[MarketSnapshot] = None
        self.ws_clients: Set[WebSocket] = set()
        self.previous_quotes: Dict[str, StockQuote] = {}


state = AppState()


def is_trading_hours() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.hour * 60 + now.minute
    return 9 * 60 + 15 <= t <= 15 * 60 + 30


def now_str() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ==================== REST API ====================

@app.get("/api/v1/health")
async def api_health():
    return {"status": "ok", "version": "0.1.0", "timestamp": now_str()}


@app.get("/api/v1/market/overview")
async def api_market_overview():
    indices = await fetch_index_quotes()
    yf_indices = await fetch_index_quotes_yf()
    indices.update(yf_indices)
    stocks = await fetch_all_quotes(state.watchlist)
    health = get_health_snapshot()
    state.last_indices = indices
    state.last_quotes = stocks
    alerts = await _detect_alerts(stocks)
    return {
        "indices": {k: v.dict() for k, v in indices.items()},
        "stocks": {k: v.dict() for k, v in stocks.items()},
        "health": [h.dict() for h in health],
        "alerts": [a.dict() for a in alerts],
        "timestamp": now_str(),
    }






# ==================== Analysis Routes ====================

@app.get("/api/v1/analysis/{code}")
async def api_analysis(code: str):
    """综合技术分析"""
    from .analysis import comprehensive_analysis
    try:
        result = comprehensive_analysis(code)
        return result
    except Exception as e:
        logger.error("Analysis error for %s: %s", code, e)
        return {"error": str(e), "code": code}


@app.get("/api/v1/analysis/{code}/predict")
async def api_analysis_predict(code: str):
    """明日走势预测"""
    from .analysis import comprehensive_analysis, predict_tomorrow
    try:
        result = comprehensive_analysis(code)
        if "error" not in result:
            prediction = predict_tomorrow(result)
            return prediction
        return {"error": result.get("error")}
    except Exception as e:
        logger.error("Prediction error for %s: %s", code, e)
        return {"error": str(e), "code": code}


@app.get("/api/v1/analysis/{code}/kline")
async def api_analysis_kline(code: str, days: int = 40):
    """获取K线数据（含MA5/MA10/MA20）"""
    from .analysis import fetch_kline_data, calc_sma
    try:
        kline = fetch_kline_data(code, days=days)
        if not kline:
            return []
        closes = [float(k[2]) for k in kline]
        ma5 = calc_sma(closes, 5)
        ma10 = calc_sma(closes, 10)
        ma20 = calc_sma(closes, 20)
        result = []
        for i, k in enumerate(kline):
            item = {
                "date": k[0],
                "open": float(k[1]),
                "close": float(k[2]),
                "high": float(k[3]),
                "low": float(k[4]),
                "volume": int(float(k[5])),
            }
            if ma5[i] is not None:
                item["ma5"] = round(ma5[i], 2)
            if ma10[i] is not None:
                item["ma10"] = round(ma10[i], 2)
            if ma20[i] is not None:
                item["ma20"] = round(ma20[i], 2)
            result.append(item)
        return result
    except Exception as e:
        logger.error("Kline error for %s: %s", code, e)
        return {"error": str(e), "code": code}


@app.get("/api/v1/analysis/{code}/quote")
async def api_analysis_quote(code: str):
    """获取实时行情所有字段"""
    from .analysis import fetch_all_quote_fields
    try:
        result = fetch_all_quote_fields(code)
        return result
    except Exception as e:
        logger.error("Quote error for %s: %s", code, e)
        return {"error": str(e), "code": code}

# ==================== Knowledge Base Routes ====================

@app.get("/api/v1/knowledge/book-list")
async def api_knowledge_books():
    """获取知识库书单(按类别)"""
    reading_path = {
        k: v for k, v in KnowledgeEngine().get_reading_path().items()
    }

    categories = {
        "价值投资": [
            {"title": "聪明的投资者", "author": "本杰明·格雷厄姆"},
            {"title": "证券分析", "author": "本杰明·格雷厄姆"},
            {"title": "怎样选择成长股", "author": "菲利普·费雪"},
            {"title": "巴菲特致股东的信", "author": "沃伦·巴菲特"},
            {"title": "投资最重要的事", "author": "霍华德·马克斯"},
            {"title": "安全边际", "author": "赛斯·卡拉曼"},
            {"title": "彼得·林奇的成功投资", "author": "彼得·林奇"},
            {"title": "股市稳赚", "author": "乔尔·格林布拉特"},
            {"title": "价值", "author": "张磊"},
        ],
        "技术分析": [
            {"title": "日本蜡烛图技术", "author": "史蒂夫·尼森"},
            {"title": "股市趋势技术分析", "author": "爱德华兹/迈吉"},
            {"title": "期货市场技术分析", "author": "约翰·墨菲"},
            {"title": "笑傲股市", "author": "威廉·欧奈尔"},
            {"title": "量价分析", "author": "安娜·库林"},
        ],
        "市场与周期": [
            {"title": "周期", "author": "霍华德·马克斯"},
            {"title": "非理性繁荣", "author": "罗伯特·席勒"},
            {"title": "金融炼金术", "author": "乔治·索罗斯"},
            {"title": "黑天鹅", "author": "纳西姆·塔勒布"},
            {"title": "反脆弱", "author": "纳西姆·塔勒布"},
        ],
        "行为金融": [
            {"title": "思考，快与慢", "author": "丹尼尔·卡尼曼"},
            {"title": "错误的行为", "author": "理查德·塞勒"},
            {"title": "乌合之众", "author": "古斯塔夫·勒庞"},
        ],
        "交易实战": [
            {"title": "股票大作手回忆录", "author": "埃德温·勒费弗"},
            {"title": "海龟交易法则", "author": "柯蒂斯·费思"},
            {"title": "以交易为生", "author": "亚历山大·埃尔德"},
        ],
        "基金与指数": [
            {"title": "共同基金常识", "author": "约翰·博格"},
            {"title": "指数基金投资指南", "author": "银行螺丝钉"},
        ],
        "财务与估值": [
            {"title": "巴菲特教你读财报", "author": "玛丽·巴菲特"},
            {"title": "财报就像一本故事书", "author": "刘顺仁"},
            {"title": "手把手教你读财报", "author": "唐朝"},
        ],
        "经典传记": [
            {"title": "滚雪球", "author": "艾丽斯·施罗德"},
            {"title": "伟大的博弈", "author": "约翰·戈登"},
            {"title": "激荡三十年", "author": "吴晓波"},
        ],
    }
    return {"categories": categories, "reading_path": reading_path}


@app.get("/api/v1/knowledge/analyze/{code}")
async def api_knowledge_analyze(code: str):
    """基于知识库对个股进行多维分析"""
    from .quote import fetch_all_quotes
    quotes = await fetch_all_quotes([code])
    stock = quotes.get(code)
    if not stock:
        return {"error": f"Stock {code} not found", "code": code}

    qd = stock.dict()
    engine = KnowledgeEngine()
    result = engine.analyze_stock(qd)

    # 行为偏差
    bf = BehavioralFinanceFramework()
    biases = bf.detect_biases(
        recent_return=qd.get("change_pct", 0),
        portfolio_turnover=50,
        has_stop_loss=True, avg_holding_days=20, max_drawdown=15,
    )
    result["behavioral_biases"] = biases

    # 历史教训
    hf = HistoryLessonsFramework()
    result["historical_lessons"] = hf.historical_lessons()

    return result


@app.get("/api/v1/knowledge/principles")
async def api_knowledge_principles():
    """获取知识库核心原则索引"""
    return {
        "principles": [
            {"category": "价值投资", "principle": "永远以低于内在价值的价格买入", "book": "《聪明的投资者》"},
            {"category": "价值投资", "principle": "投资具有持久竞争优势的企业", "book": "《巴菲特致股东的信》"},
            {"category": "价值投资", "principle": "按低PE和高ROE排序分散买入", "book": "《股市稳赚》"},
            {"category": "价值投资", "principle": "PEG<1是最佳买入点", "book": "《彼得·林奇的成功投资》"},
            {"category": "技术分析", "principle": "趋势是你的朋友，不逆势交易", "book": "《股市趋势技术分析》"},
            {"category": "技术分析", "principle": "成交量是价格的先行指标", "book": "《量价分析》"},
            {"category": "市场与周期", "principle": "在别人恐惧时贪婪，在别人贪婪时恐惧", "book": "《周期》"},
            {"category": "市场与周期", "principle": "黑天鹅不可预测，但可以做好准备", "book": "《黑天鹅》"},
            {"category": "行为金融", "principle": "认识自己的认知偏差是克服它们的第一步", "book": "《思考，快与慢》"},
            {"category": "交易实战", "principle": "计划你的交易，交易你的计划", "book": "《股票大作手回忆录》"},
            {"category": "交易实战", "principle": "使用分仓凯利公式控制仓位", "book": "《通向财务自由之路》"},
            {"category": "基金与指数", "principle": "控制成本是你能做的唯一确定的事", "book": "《共同基金常识》"},
            {"category": "财务与估值", "principle": "现金为王，负债是刀", "book": "《巴菲特教你读财报》"},
            {"category": "财务与估值", "principle": "持续高ROE是优秀企业的核心特征", "book": "《手把手教你读财报》"},
            {"category": "宏观金融", "principle": "不要与美联储对抗", "book": "《金融的本质》"},
        ],
        "reading_path": KnowledgeEngine().get_reading_path(),
    }


@app.get("/api/v1/stock/{code}")
async def api_stock_detail(code: str):
    q = await fetch_all_quotes([code])
    stock = q.get(code)
    if not stock:
        return {"error": f"Stock {code} not found", "code": code}
    return stock.dict()


@app.get("/api/v1/watchlist")
async def api_get_watchlist():
    return {"watchlist": state.watchlist}


@app.post("/api/v1/watchlist/add")
async def api_watchlist_add(code: str = Query(...)):
    code = code.strip()
    if code not in state.watchlist:
        state.watchlist.append(code)
        add_watchlist_item(code)
    return {"watchlist": state.watchlist, "added": code}


@app.post("/api/v1/watchlist/remove")
async def api_watchlist_remove(code: str = Query(...)):
    code = code.strip()
    if code in state.watchlist:
        state.watchlist.remove(code)
        remove_watchlist_item(code)
    return {"watchlist": state.watchlist, "removed": code}


@app.post("/api/v1/watchlist/sync")
async def api_watchlist_sync(codes: List[str] = None):
    """批量同步自选股（用于前端全量同步）"""
    if codes is None:
        codes = []
    state.watchlist = list(codes)
    save_watchlist(state.watchlist)
    return {"watchlist": state.watchlist, "synced": len(state.watchlist)}


@app.get("/api/v1/health/sources")
async def api_health_sources():
    return {"sources": [h.dict() for h in get_health_snapshot()]}



@app.get("/api/v1/stock/search/{keyword}")
async def api_stock_search(keyword: str):
    """搜索股票 — 支持代码/名称/拼音首字母模糊匹配"""
    from .db import get_cached_search, set_cached_search
    from .quote import fetch_all_quotes

    kw = keyword.strip()
    if len(kw) < 1:
        return {"keyword": keyword, "results": []}

    # 查缓存
    cached = get_cached_search(kw)
    if cached:
        return {"keyword": keyword, "results": cached, "source": "cache"}

    results = []
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                code_str = str(row.get("代码", ""))
                name_str = str(row.get("名称", ""))
                # 匹配：代码包含 or 名称包含 or 拼音首字母包含
                if kw.lower() in code_str.lower() \
                        or kw in name_str \
                        or _pinyin_match(name_str, kw):
                    full_code = f"sz{code_str}" if code_str.startswith(("0", "2", "3")) else f"sh{code_str}"
                    results.append({
                        "code": full_code,
                        "name": name_str,
                        "price": float(row.get("最新价", 0)),
                        "change_pct": float(row.get("涨跌幅", 0)),
                    })
    except Exception as e:
        logger.warning("akshare搜索失败，使用腾讯行情: %s", e)
        # 降级：尝试直接用腾讯行情查
        try:
            pure_kw = kw.lower()
            for prefix in ["sh", "sz"]:
                for suffix in [pure_kw, pure_kw.zfill(6)]:
                    try:
                        q = await fetch_all_quotes([f"{prefix}{suffix}"])
                        for _, sq in q.items():
                            if sq.price > 0:
                                results.append({
                                    "code": sq.code,
                                    "name": sq.name,
                                    "price": sq.price,
                                    "change_pct": sq.change_pct,
                                })
                    except Exception:
                        continue
        except Exception:
            pass

    # 限制结果数
    results = results[:20]

    # 写入缓存
    if results:
        set_cached_search(kw, results)

    return {"keyword": keyword, "results": results}


def _pinyin_match(name: str, keyword: str) -> bool:
    """检查股票名称的拼音首字母是否匹配关键字"""
    try:
        _PINYIN_MAP = {
            "阿": "a", "安": "a", "巴": "b", "百": "b", "半": "b", "保": "b",
            "北": "b", "比": "b", "波": "b", "玻": "b", "材": "c", "产": "c",
            "长": "c", "超": "c", "车": "c", "池": "c", "传": "c", "创": "c",
            "达": "d", "导": "d", "的": "d", "迪": "d", "地": "d", "电": "d",
            "顶": "d", "东": "d", "动": "d", "抖": "d", "多": "d", "尔": "e",
            "发": "f", "方": "f", "纺": "f", "汾": "f", "风": "f", "服": "f",
            "福": "f", "伏": "f", "份": "f", "港": "g", "钢": "g", "格": "g",
            "工": "g", "公": "g", "股": "g", "光": "g", "广": "g", "国": "g",
            "海": "h", "杭": "h", "航": "h", "河": "h", "恒": "h", "互": "h",
            "华": "h", "化": "h", "环": "h", "汇": "h", "货": "h", "机": "j",
            "集": "j", "技": "j", "家": "j", "建": "j", "件": "j", "江": "j",
            "金": "j", "京": "j", "酒": "j", "军": "j", "科": "k", "空": "k",
            "口": "k", "快": "k", "来": "l", "老": "l", "理": "l", "力": "l",
            "联": "l", "料": "l", "粮": "l", "疗": "l", "液": "y", "隆": "l",
            "泸": "l", "路": "l", "绿": "l", "旅": "l", "络": "l", "璃": "l",
            "迈": "m", "茅": "m", "媒": "m", "煤": "m", "美": "m", "米": "m",
            "牧": "m", "能": "n", "宁": "n", "南": "n", "鹏": "p", "片": "p",
            "拼": "p", "品": "p", "平": "p", "器": "q", "庆": "q", "券": "q",
            "瑞": "r", "软": "r", "赛": "s", "三": "s", "色": "s", "上": "s",
            "商": "s", "深": "s", "生": "s", "胜": "s", "石": "s", "食": "s",
            "市": "s", "手": "s", "司": "s", "斯": "s", "台": "t", "炭": "t",
            "腾": "t", "体": "t", "天": "t", "铁": "t", "通": "t", "投": "t",
            "万": "w", "网": "w", "微": "w", "为": "w", "韦": "w", "蔚": "w",
            "温": "w", "物": "w", "五": "w", "西": "x", "限": "x", "险": "x",
            "想": "x", "小": "x", "械": "x", "芯": "x", "新": "x", "信": "x",
            "行": "x", "徐": "x", "讯": "x", "亚": "y", "洋": "y", "药": "y",
            "耀": "y", "业": "y", "一": "y", "医": "y", "易": "y", "银": "y",
            "饮": "y", "音": "y", "油": "y", "游": "y", "有": "y", "源": "y",
            "运": "y", "展": "z", "招": "z", "证": "z", "织": "z", "中": "z",
            "重": "z", "州": "z", "筑": "z", "装": "z", "卓": "z", "资": "z",
        }
        first_letters = "".join([_PINYIN_MAP.get(c, c.lower()) for c in name])
        return keyword.lower() in first_letters.lower()
    except Exception:
        return False

# ==================== Alert Detection ====================

async def _detect_alerts(current: Dict[str, StockQuote]) -> List[Alert]:
    alerts: List[Alert] = []
    now = now_str()
    prev = state.previous_quotes
    state.previous_quotes = dict(current)

    for code, sq in current.items():
        if sq.price <= 0:
            continue

        # 涨跌幅告警
        if abs(sq.change_pct) >= ALERT_CHANGE_PCT:
            direction = "大涨" if sq.change_pct > 0 else "大跌"
            alerts.append(Alert(
                type="change_pct",
                code=code, name=sq.name,
                message=f"{sq.name} ({code}) {direction} {sq.change_pct:+.2f}%",
                value=sq.change_pct, threshold=ALERT_CHANGE_PCT,
                timestamp=now,
            ))

        # 振幅告警
        if sq.amplitude >= ALERT_AMPLITUDE:
            alerts.append(Alert(
                type="amplitude",
                code=code, name=sq.name,
                message=f"{sq.name} ({code}) 振幅 {sq.amplitude:.2f}%",
                value=sq.amplitude, threshold=ALERT_AMPLITUDE,
                timestamp=now,
            ))

        # 成交量异动
        if code in prev and prev[code].volume > 0:
            ratio = sq.volume / max(prev[code].volume, 1)
            if ratio >= ALERT_VOLUME_SURGE:
                alerts.append(Alert(
                    type="volume_surge",
                    code=code, name=sq.name,
                    message=f"{sq.name} ({code}) 成交量激增 {ratio:.1f}x",
                    value=ratio, threshold=ALERT_VOLUME_SURGE,
                    timestamp=now,
                ))

        # 涨停/跌停检测
        if sq.prev_close > 0:
            limit_up = round(sq.prev_close * 1.1, 2)
            limit_down = round(sq.prev_close * 0.9, 2)
            if abs(sq.price - limit_up) <= 0.01:
                alerts.append(Alert(
                    type="limit_up", code=code, name=sq.name,
                    message=f"{sq.name} ({code}) 涨停！",
                    value=sq.price, threshold=limit_up,
                    timestamp=now,
                ))
            elif abs(sq.price - limit_down) <= 0.01:
                alerts.append(Alert(
                    type="limit_down", code=code, name=sq.name,
                    message=f"{sq.name} ({code}) 跌停！",
                    value=sq.price, threshold=limit_down,
                    timestamp=now,
                ))

    return alerts


# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    state.ws_clients.add(ws)
    logger.info("WebSocket client connected (%d total)", len(state.ws_clients))

    try:
        while True:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=30)
            try:
                msg = json.loads(raw)
                msg_type = msg.get("type", "")
                if msg_type == "subscribe":
                    stocks = msg.get("stocks", [])
                    for s in stocks:
                        if s not in state.watchlist:
                            state.watchlist.append(s)
                    logger.info("Client subscribed to %d stocks", len(stocks))
                elif msg_type == "unsubscribe":
                    stocks = msg.get("stocks", [])
                    for s in stocks:
                        if s in state.watchlist:
                            state.watchlist.remove(s)
            except (json.JSONDecodeError, Exception):
                pass
    except asyncio.TimeoutError:
        pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
    finally:
        state.ws_clients.discard(ws)
        logger.info("WebSocket client disconnected (%d remaining)", len(state.ws_clients))


async def _broadcast(msg: WSMessage):
    payload = json.dumps({
        "type": msg.type,
        "data": msg.data,
        "timestamp": msg.timestamp or now_str(),
    })
    disconnected: list[WebSocket] = []
    for ws in state.ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        state.ws_clients.discard(ws)


# ==================== Background Tasks ====================

async def _quote_updater():
    while True:
        try:
            if not is_trading_hours():
                await asyncio.sleep(60)
                continue

            stocks = await fetch_all_quotes(state.watchlist)
            indices = await fetch_index_quotes()
            yf_indices = await fetch_index_quotes_yf()
            indices.update(yf_indices)
            health = get_health_snapshot()
            alerts = await _detect_alerts(stocks)

            state.last_quotes = stocks
            state.last_indices = indices

            snapshot = MarketSnapshot(
                stocks={k: v.dict() for k, v in stocks.items()},
                indices={k: v.dict() for k, v in indices.items()},
                health=[h.dict() for h in health],
                alerts=[a.dict() for a in alerts],
                timestamp=now_str(),
            )
            state.last_snapshot = snapshot

            if stocks:
                await _broadcast(WSMessage(type="market_quote", data={
                    "stocks": {k: v.dict() for k, v in stocks.items()},
                }))
            if indices:
                await _broadcast(WSMessage(type="index_quote", data={
                    "indices": {k: v.dict() for k, v in indices.items()},
                }))
            if health:
                await _broadcast(WSMessage(type="health_status", data={
                    "sources": [h.dict() for h in health],
                }))
            if alerts:
                await _broadcast(WSMessage(type="alert", data={
                    "alerts": [a.dict() for a in alerts],
                }))

        except Exception as e:
            logger.error("quote_updater error: %s", e)

        await asyncio.sleep(QUOTE_REFRESH_INTERVAL)


@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(_quote_updater())
    logger.info("盘眼 PanYan 后端启动完成 (port=%d)", BACKEND_PORT)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=BACKEND_PORT, reload=True)
