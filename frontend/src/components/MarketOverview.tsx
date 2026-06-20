import { IndexQuote, StockQuote } from '../types';
import { formatPrice, formatChangePct, colorForChange, bgColorForChange } from '../utils/format';

interface Props {
  indices: Record<string, IndexQuote>;
  stocks: Record<string, StockQuote>;
}

export default function MarketOverview({ indices, stocks }: Props) {
  const hasData = Object.keys(indices).length > 0 || Object.keys(stocks).length > 0;

  return (
    <div className="panel market-overview">
      <div className="panel-header">大盘指数</div>
      {!hasData ? (
        <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text2)' }}>
          等待行情数据...
        </div>
      ) : (
        <div className="index-grid">
          {Object.values(indices).map((idx) => (
            <div
              key={idx.code}
              className="index-card"
              style={{ background: bgColorForChange(idx.change_pct) }}
            >
              <div className="idx-name">{idx.name}</div>
              <div className="idx-price" style={{ color: colorForChange(idx.change_pct) }}>
                {formatPrice(idx.price)}
              </div>
              <div className="idx-change" style={{ color: colorForChange(idx.change_pct) }}>
                {formatChangePct(idx.change_pct)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
