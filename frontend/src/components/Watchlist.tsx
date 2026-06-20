import { useState, useCallback, useRef, useEffect } from 'react';
import { StockQuote } from '../types';
import { formatPrice, formatChangePct, colorForChange } from '../utils/format';

interface SearchResult {
  code: string;
  name: string;
  price: number;
  change_pct: number;
}

interface Props {
  stocks: Record<string, StockQuote>;
  selectedCode: string | null;
  onSelect: (code: string | null) => void;
}

export default function Watchlist({ stocks, selectedCode, onSelect }: Props) {
  const list = Object.values(stocks);
  const [searchKw, setSearchKw] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const doSearch = useCallback(async (kw: string) => {
    if (!kw.trim() || kw.trim().length < 1) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }
    setSearching(true);
    try {
      const res = await fetch(`/api/v1/stock/search/${encodeURIComponent(kw.trim())}`);
      const data = await res.json();
      setSearchResults(data.results || []);
      setShowResults(true);
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, []);

  const onSearchInput = useCallback((val: string) => {
    setSearchKw(val);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => doSearch(val), 300);
  }, [doSearch]);

  const addStock = useCallback(async (code: string) => {
    try {
      await fetch(`/api/v1/watchlist/add?code=${encodeURIComponent(code)}`, { method: 'POST' });
      setShowResults(false);
      setSearchKw('');
      setSearchResults([]);
    } catch (e) {
      console.warn('添加失败:', e);
    }
  }, []);

  const removeStock = useCallback(async (code: string) => {
    try {
      await fetch(`/api/v1/watchlist/remove?code=${encodeURIComponent(code)}`, { method: 'POST' });
      if (selectedCode === code) {
        onSelect(null);
      }
    } catch (e) {
      console.warn('移除失败:', e);
    }
  }, [selectedCode, onSelect]);

  // 点击外部关闭搜索结果
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  return (
    <div className="panel watchlist" ref={containerRef}>
      <div className="panel-header">
        自选股
        <span style={{ fontWeight: 400, fontSize: '0.75rem' }}>{list.length} 只</span>
      </div>

      {/* 搜索框 */}
      <div style={{ padding: '6px 8px 0 8px', position: 'relative' }}>
        <input
          className="wl-search"
          type="text"
          placeholder="搜索股票代码/名称/拼音..."
          value={searchKw}
          onChange={(e) => onSearchInput(e.target.value)}
          onFocus={() => { if (searchResults.length > 0) setShowResults(true); }}
        />
        {searching && (
          <span style={{ position: 'absolute', right: 14, top: 10, fontSize: '0.7rem', color: 'var(--text2)' }}>
            ...
          </span>
        )}

        {/* 搜索结果下拉 */}
        {showResults && searchResults.length > 0 && (
          <div className="wl-search-results">
            {searchResults.map((r) => (
              <div
                key={r.code}
                className="wl-search-item"
                onClick={() => addStock(r.code)}
              >
                <span>
                  <span style={{ fontWeight: 600 }}>{r.name}</span>
                  <span style={{ marginLeft: 8, color: 'var(--text2)', fontSize: '0.75rem' }}>{r.code}</span>
                  <span style={{ marginLeft: 8 }}>{formatPrice(r.price)}</span>
                </span>
                <span style={{ color: colorForChange(r.change_pct) }}>
                  {formatChangePct(r.change_pct)}
                </span>
                <span className="add-btn">+</span>
              </div>
            ))}
          </div>
        )}
        {showResults && searchResults.length === 0 && searchKw.trim() && !searching && (
          <div className="wl-search-results" style={{ padding: '10px', textAlign: 'center', color: 'var(--text2)', fontSize: '0.8rem' }}>
            未找到匹配股票
          </div>
        )}
      </div>

      {/* 自选列表 */}
      <div className="panel-body" style={{ maxHeight: 'calc(100vh - 360px)', overflowY: 'auto' }}>
        {list.length === 0 ? (
          <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text2)', fontSize: '0.85rem' }}>
            暂无自选股，搜索股票添加
          </div>
        ) : (
          list.map((s) => (
            <div
              key={s.code}
              className={`watchlist-item${selectedCode === s.code ? ' selected' : ''}`}
              onClick={() => onSelect(s.code)}
            >
              <div className="wl-name">{s.name}</div>
              <div className="wl-price">{formatPrice(s.price)}</div>
              <div className="wl-change" style={{ color: colorForChange(s.change_pct) }}>
                {formatChangePct(s.change_pct)}
              </div>
              <button
                className="dismiss-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  removeStock(s.code);
                }}
                title="移除"
                style={{
                  background: 'none', border: 'none', color: 'var(--text2)',
                  cursor: 'pointer', fontSize: '0.9rem', padding: '0 4px',
                  opacity: 0.4,
                }}
                onMouseEnter={(e) => { (e.target as HTMLElement).style.opacity = '1'; }}
                onMouseLeave={(e) => { (e.target as HTMLElement).style.opacity = '0.4'; }}
              >
                ✕
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
