"""
盘眼 Pydantic 数据模型
"""
from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel, Field


class StockQuote(BaseModel):
    """单只股票实时行情"""
    code: str = Field(..., description="股票代码（如 sz000333）")
    name: str = ""
    price: float = 0.0
    prev_close: float = 0.0
    open_price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: int = 0
    amount: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    turnover_rate: float = 0.0
    amplitude: float = 0.0
    pe_ttm: float = 0.0
    pb: float = 0.0
    market_cap: float = 0.0
    circulating_cap: float = 0.0
    bid_prices: List[float] = Field(default_factory=list)
    bid_volumes: List[int] = Field(default_factory=list)
    ask_prices: List[float] = Field(default_factory=list)
    ask_volumes: List[int] = Field(default_factory=list)
    timestamp: str = ""
    source: str = ""


class IndexQuote(BaseModel):
    """大盘指数行情"""
    code: str = ""
    name: str = ""
    price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    open_price: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: int = 0
    amount: float = 0.0
    timestamp: str = ""
    source: str = ""


class HealthStatus(BaseModel):
    """数据源健康状态"""
    source: str = ""
    status: str = "unknown"
    latency_ms: float = 0.0
    last_success: str = ""
    last_error: str = ""
    error_count: int = 0


class Alert(BaseModel):
    """异动告警"""
    type: str = ""
    code: str = ""
    name: str = ""
    message: str = ""
    value: float = 0.0
    threshold: float = 0.0
    timestamp: str = ""


class WSMessage(BaseModel):
    """WebSocket 消息"""
    type: str = ""
    data: Any = None
    timestamp: str = ""


class WSScubscribe(BaseModel):
    """WebSocket 订阅请求"""
    type: str = ""
    stocks: List[str] = Field(default_factory=list)


class MarketSnapshot(BaseModel):
    """全市场快照"""
    stocks: Dict[str, Any] = Field(default_factory=dict)
    indices: Dict[str, Any] = Field(default_factory=dict)
    health: List[Any] = Field(default_factory=list)
    alerts: List[Any] = Field(default_factory=list)
    timestamp: str = ""
