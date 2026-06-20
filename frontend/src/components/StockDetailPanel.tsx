import { StockQuote } from '../types';
import { formatPrice, formatChangePct, formatVolume, formatAmount, colorForChange } from '../utils/format';

interface Props {
  stock: StockQuote | null;
}

const fields: { label: string; key: keyof StockQuote; fmt?: (v: number) => string; isNumber?: boolean }[] = [
  { label: '现价', key: 'price', fmt: formatPrice },
  { label: '涨跌幅', key: 'change_pct', fmt: formatChangePct },
  { label: '涨跌额', key: 'change', fmt: (v) => v >= 0 ? `+${v.toFixed(2)}` : v.toFixed(2) },
  { label: '今开', key: 'open_price', fmt: formatPrice },
  { label: '昨收', key: 'prev_close', fmt: formatPrice },
  { label: '最高', key: 'high', fmt: formatPrice },
  { label: '最低', key: 'low', fmt: formatPrice },
  { label: '成交量', key: 'volume', fmt: formatVolume },
  { label: '成交额', key: 'amount', fmt: formatAmount },
  { label: '换手率', key: 'turnover_rate', fmt: (v) => `${v.toFixed(2)}%` },
  { label: '振幅', key: 'amplitude', fmt: (v) => `${v.toFixed(2)}%` },
  { label: '市盈率', key: 'pe_ttm', fmt: (v) => v > 0 ? v.toFixed(2) : '-' },
  { label: '总市值', key: 'market_cap', fmt: formatAmount },
  { label: '流通市值', key: 'circulating_cap', fmt: formatAmount },
];

export default function StockDetailPanel({ stock }: Props) {
  if (!stock) {
    return (
      <div className="panel stock-detail">
        <div className="panel-header">个股详情</div>
        <div className="stock-detail-empty">点击左侧自选股查看详情</div>
      </div>
    );
  }

  return (
    <div className="panel stock-detail">
      <div className="panel-header">
        {stock.name}
        <span style={{ fontWeight: 400, fontSize: '0.75rem', color: 'var(--text2)' }}>
          {stock.code} · {stock.source}
        </span>
      </div>
      <div className="detail-grid">
        {fields.map((f) => {
          const val = stock[f.key];
          const numVal = typeof val === 'number' ? val : 0;
          const display = f.fmt ? f.fmt(numVal) : String(val ?? '-');
          const isChange = f.key === 'change_pct' || f.key === 'change';
          return (
            <div className="detail-item" key={f.key}>
              <div className="label">{f.label}</div>
              <div
                className="value"
                style={isChange ? { color: colorForChange(numVal) } : undefined}
              >
                {display}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
