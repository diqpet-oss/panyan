export interface StockQuote {
  code: string;
  name: string;
  price: number;
  prev_close: number;
  open_price: number;
  high: number;
  low: number;
  volume: number;
  amount: number;
  change: number;
  change_pct: number;
  turnover_rate: number;
  amplitude: number;
  pe_ttm: number;
  market_cap: number;
  circulating_cap: number;
  timestamp: string;
  source: string;
}

export interface IndexQuote {
  code: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  open_price: number;
  high: number;
  low: number;
  volume: number;
  amount: number;
  timestamp: string;
}

export interface HealthStatus {
  source: string;
  status: string;
  latency_ms: number;
  last_success: string;
  last_error: string;
  error_count: number;
}

export interface Alert {
  type: string;
  code: string;
  name: string;
  message: string;
  value: number;
  threshold: number;
  timestamp: string;
}

export interface WSMessage {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface MarketData {
  indices: Record<string, IndexQuote>;
  stocks: Record<string, StockQuote>;
  health: HealthStatus[];
  alerts: Alert[];
  timestamp: string;
}

export interface StockAnalysis {
  code: string;
  name: string;
  price: number;
  change_pct: number;
  volume: number;
  trend: string;
  macd_signal: string;
  rsi: number;
  boll_position: string;
  support: number;
  resistance: number;
  patterns: string[];
  score: number;
  综合评分?: number;
  [key: string]: any;
}

export interface Prediction {
  direction: string;
  confidence: number;
  target_price: number;
  stop_loss: number;
  reason: string;
  综合评分?: number;
  大概率情景?: any;
  次概率情景?: any;
  小概率情景?: any;
  关键支撑位?: number[];
  关键阻力位?: number[];
  [key: string]: any;
}


export interface KLineItem {
  date: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
}
