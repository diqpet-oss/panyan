import { useState, useEffect, useCallback } from 'react';
import { MarketData, WSMessage, Alert, StockAnalysis, Prediction } from './types';
import { nowStr } from './utils/format';
import { useWebSocket } from './hooks/useWebSocket';
import Header from './components/Header';
import MarketOverview from './components/MarketOverview';
import Watchlist from './components/Watchlist';
import StockDetailPanel from './components/StockDetailPanel';
import AnalysisPanel from './components/AnalysisPanel';
import HealthMonitor from './components/HealthMonitor';
import AlertBanner from './components/AlertBanner';
import KnowledgeAnalysis from './components/KnowledgeAnalysis';

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
const MARKET_API = '/api/v1/market/overview';

export default function App() {
  const [data, setData] = useState<MarketData>({
    indices: {}, stocks: {}, health: [], alerts: [], timestamp: '',
  });
  const [selectedStock, setSelectedStock] = useState<string | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
  const [isOnline, setIsOnline] = useState(false);
  const [activeTab, setActiveTab] = useState<'quote' | 'analysis' | 'knowledge'>('quote');

  // Analysis state
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [klineData, setKlineData] = useState<any[]>([]);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  // Initial load
  useEffect(() => {
    fetch(MARKET_API)
      .then((r) => r.json())
      .then((d) => {
        setData(d);
        setIsOnline(true);
      })
      .catch(() => setIsOnline(false));
  }, []);

  // Load analysis when stock selected
  useEffect(() => {
    if (!selectedStock || activeTab !== 'analysis') return;
    setAnalysisLoading(true);
    Promise.all([
      fetch(`/api/v1/analysis/${selectedStock}`).then(r => r.json()),
      fetch(`/api/v1/analysis/${selectedStock}/predict`).then(r => r.json()),
      fetch(`/api/v1/analysis/${selectedStock}/kline?days=40`).then(r => r.json()),
    ]).then(([a, p, k]) => {
      if (a.error) {
        console.warn('Analysis error:', a.error);
        setAnalysis(null);
      } else {
        setAnalysis(a as StockAnalysis);
      }
      setPrediction(p as Prediction);
      setKlineData(Array.isArray(k) ? k : []);
    }).catch(e => {
      console.warn('Failed to load analysis:', e);
    }).finally(() => setAnalysisLoading(false));
  }, [selectedStock, activeTab]);

  // WebSocket
  const onMessage = useCallback((msg: WSMessage) => {
    setData((prev) => {
      const next = { ...prev };
      if (msg.type === 'market_quote') {
        const s = (msg.data as { stocks?: Record<string, unknown> }).stocks;
        if (s) next.stocks = { ...prev.stocks, ...s } as typeof prev.stocks;
      }
      if (msg.type === 'index_quote') {
        const idx = (msg.data as { indices?: Record<string, unknown> }).indices;
        if (idx) next.indices = { ...prev.indices, ...idx } as typeof prev.indices;
      }
      if (msg.type === 'health_status') {
        const h = (msg.data as { sources?: unknown[] }).sources;
        if (h) next.health = h as typeof prev.health;
      }
      if (msg.type === 'alert') {
        const a = (msg.data as { alerts?: Alert[] }).alerts;
        if (a) {
          next.alerts = a;
          setRecentAlerts((prevAlerts) => {
            const combined = [...a, ...prevAlerts];
            return combined.slice(0, 20);
          });
        }
      }
      next.timestamp = msg.timestamp || nowStr();
      return next;
    });
    setIsOnline(true);
  }, []);

  useWebSocket(WS_URL, onMessage);

  const selectedStockData = selectedStock ? data.stocks[selectedStock] : null;

  return (
    <div className="app">
      <Header
        isOnline={isOnline}
        timestamp={data.timestamp}
        alertCount={recentAlerts.length}
      />
      <AlertBanner alerts={recentAlerts} onDismiss={() => setRecentAlerts([])} />
      <div className="app-body">
        <aside className="app-sidebar">
          <HealthMonitor sources={data.health} />
          <Watchlist
            stocks={data.stocks}
            selectedCode={selectedStock}
            onSelect={(code) => {
              setSelectedStock(code);
              setActiveTab('quote');
            }}
          />
        </aside>
        <main className="app-main">
          {selectedStock && (
            <div style={{ display: 'flex', gap: 0, marginBottom: 0 }}>
              <button
                className={`tab-btn ${activeTab === 'quote' ? 'active' : ''}`}
                onClick={() => setActiveTab('quote')}
              >
                实时行情
              </button>
              <button
                className={`tab-btn ${activeTab === 'analysis' ? 'active' : ''}`}
                onClick={() => setActiveTab('analysis')}
              >
                技术分析
              </button>
              <button
                className={`tab-btn ${activeTab === 'knowledge' ? 'active' : ''}`}
                onClick={() => setActiveTab('knowledge')}
              >
                知识库
              </button>
            </div>
          )}
          <MarketOverview indices={data.indices} stocks={data.stocks} />
          {activeTab === 'quote' && selectedStockData && (
            <StockDetailPanel stock={selectedStockData} />
          )}
          {activeTab === 'analysis' && (
            <AnalysisPanel
              analysis={analysis}
              prediction={prediction}
              kline={klineData}
              loading={analysisLoading}
            />
          )}
          {activeTab === 'knowledge' && selectedStock && (
            <KnowledgeAnalysis
              stockCode={selectedStock}
              stockName={selectedStockData?.name || ''}
            />
          )}
          {selectedStock && !selectedStockData && <StockDetailPanel stock={null} />}
        </main>
      </div>
    </div>
  );
}
