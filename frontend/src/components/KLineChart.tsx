import { useMemo } from 'react';
import { KLineItem } from '../types';
import { formatShortDate } from '../utils/format';

interface Props {
  data: KLineItem[];
  width?: number;
  height?: number;
}

const PADDING = { top: 20, right: 20, bottom: 40, left: 50 };
const VOL_HEIGHT = 60;

export default function KLineChart({ data, width = 600, height = 400 }: Props) {
  const chartW = width - PADDING.left - PADDING.right;
  const priceH = height - PADDING.top - PADDING.bottom - VOL_HEIGHT;

  const { minP, maxP, maxV, candleW, gap } = useMemo(() => {
    if (!data.length) return { minP: 0, maxP: 0, maxV: 0, candleW: 0, gap: 0 };
    let minP = Infinity, maxP = -Infinity, maxV = 0;
    data.forEach(d => {
      if (d.low < minP) minP = d.low;
      if (d.high > maxP) maxP = d.high;
      if (d.volume > maxV) maxV = d.volume;
    });
    const range = maxP - minP || 1;
    minP = Math.max(0, minP - range * 0.05);
    maxP = maxP + range * 0.08;
    const totalW = chartW;
    const count = data.length;
    const cw = Math.min(12, (totalW / count) * 0.6);
    const g = (totalW - cw * count) / (count + 1);
    return { minP, maxP, maxV, candleW: cw, gap: g };
  }, [data, chartW]);

  const pScale = (p: number) => PADDING.top + priceH - ((p - minP) / (maxP - minP)) * priceH;
  const vScale = (v: number) => PADDING.top + priceH + VOL_HEIGHT - (v / maxV) * VOL_HEIGHT;

  if (!data.length) {
    return (
      <div style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text2)' }}>
        暂无K线数据
      </div>
    );
  }

  const lines = [
    { key: 'ma5' as const, color: '#f39c12', label: 'MA5' },
    { key: 'ma10' as const, color: '#3498db', label: 'MA10' },
    { key: 'ma20' as const, color: '#9b59b6', label: 'MA20' },
  ];

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map(r => {
        const y = pScale(minP + (maxP - minP) * r);
        return (
          <g key={r}>
            <line x1={PADDING.left} y1={y} x2={PADDING.left + chartW} y2={y} stroke="var(--border)" strokeWidth={0.5} />
            <text x={PADDING.left - 5} y={y + 4} textAnchor="end" fill="var(--text2)" fontSize={10}>
              {(minP + (maxP - minP) * r).toFixed(2)}
            </text>
          </g>
        );
      })}

      {/* Candlesticks */}
      {data.map((d, i) => {
        const x = PADDING.left + gap + i * (candleW + gap);
        const isUp = d.close >= d.open;
        const color = isUp ? 'var(--red)' : 'var(--green)';
        const bodyTop = pScale(Math.max(d.open, d.close));
        const bodyBot = pScale(Math.min(d.open, d.close));
        const bodyH = Math.max(1, bodyBot - bodyTop);
        const hlX = x + candleW / 2;

        return (
          <g key={i}>
            <line x1={hlX} y1={pScale(d.high)} x2={hlX} y2={pScale(d.low)} stroke={color} strokeWidth={1} />
            <rect x={x} y={bodyTop} width={candleW} height={bodyH} fill={color} />
            <rect
              x={x}
              y={vScale(d.volume)}
              width={candleW}
              height={PADDING.top + priceH + VOL_HEIGHT - vScale(d.volume)}
              fill={color}
              opacity={0.25}
            />
          </g>
        );
      })}

      {/* MA lines */}
      {lines.map(l => {
        const pts = data.map((d, i) => {
          const v = d[l.key];
          if (v === undefined) return null;
          const cx = PADDING.left + gap + i * (candleW + gap) + candleW / 2;
          return `${cx},${pScale(v)}`;
        }).filter((p): p is string => p !== null);
        if (pts.length < 2) return null;
        return <path key={l.key} d={`M${pts.join(' L')}`} fill="none" stroke={l.color} strokeWidth={1.2} />;
      })}

      {/* Date labels */}
      {data.filter((_, i) => i % Math.max(1, Math.floor(data.length / 8)) === 0).map((d, i) => {
        const idx = data.indexOf(d);
        const x = PADDING.left + gap + idx * (candleW + gap) + candleW / 2;
        return (
          <text key={i} x={x} y={height - 5} textAnchor="middle" fill="var(--text2)" fontSize={9}>
            {formatShortDate(d.date)}
          </text>
        );
      })}

      {/* Volume label */}
      <text x={PADDING.left} y={PADDING.top + priceH + VOL_HEIGHT - 4} fill="var(--text2)" fontSize={9}>
        量
      </text>

      {/* Legend */}
      <g transform={`translate(${PADDING.left}, 5)`}>
        {lines.map((l, i) => (
          <g key={i} transform={`translate(${i * 70}, 0)`}>
            <line x1={0} y1={0} x2={12} y2={0} stroke={l.color} strokeWidth={2} />
            <text x={16} y={4} fill={l.color} fontSize={10}>{l.label}</text>
          </g>
        ))}
      </g>
    </svg>
  );
}
