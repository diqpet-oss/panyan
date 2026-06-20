import { StockAnalysis, Prediction } from '../types';
import KLineChart from './KLineChart';

interface Props {
  analysis: StockAnalysis | null;
  prediction: Prediction | null;
  kline: any[];
  loading: boolean;
}

export default function AnalysisPanel({ analysis, prediction, kline, loading }: Props) {
  if (loading) {
    return (
      <div className="panel" style={{ padding: 24, textAlign: 'center', color: 'var(--text2)' }}>
        加载分析数据...
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="panel" style={{ padding: 24, textAlign: 'center', color: 'var(--text2)' }}>
        选择一只股票查看技术分析
      </div>
    );
  }

  const a = analysis;
  const b = a.bollinger;
  const s = a.support_resistance;
  const t = a.trend;
  const v = a.volume_analysis;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* K线图 */}
      <div className="panel">
        <div className="panel-header">日K线图 · {a.name}</div>
        <div className="panel-body" style={{ overflowX: 'auto', padding: 8 }}>
          <KLineChart data={kline} width={Math.max(600, kline.length * 16)} height={380} />
        </div>
      </div>

      {/* 技术指标网格 */}
      <div className="panel">
        <div className="panel-header">技术指标</div>
        <div className="panel-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
            <IndicatorCard title="均线" rows={[
              { label: 'MA5', value: String(a.ma['MA5'] ?? '-'), dir: String(a.ma['价在MA5上方'] ?? '') },
              { label: 'MA10', value: String(a.ma['MA10'] ?? '-'), dir: String(a.ma['价在MA10上方'] ?? '') },
              { label: 'MA20', value: String(a.ma['MA20'] ?? '-'), dir: String(a.ma['价在MA20上方'] ?? '') },
              { label: 'MA60', value: String(a.ma['MA60'] ?? '-'), dir: String(a.ma['价在MA60上方'] ?? '') },
            ]} />
            <IndicatorCard title="震荡指标" rows={[
              { label: 'RSI(14)', value: String(a.rsi14.value ?? '-'), dir: a.rsi14.status },
              { label: 'MACD', value: a.macd['金叉死叉'], dir: '' },
              { label: 'DIF', value: a.macd.DIF.toFixed(4) },
              { label: 'DEA', value: a.macd.DEA.toFixed(4) },
            ]} />
            <IndicatorCard title="布林带" rows={[
              { label: '上轨', value: String(b.上轨 ?? '-') },
              { label: '中轨', value: String(b.中轨 ?? '-') },
              { label: '下轨', value: String(b.下轨 ?? '-') },
              { label: '带宽', value: b.带宽 != null ? `${b.带宽.toFixed(1)}%` : '-' },
              { label: '位置', value: b.位置 },
            ]} />
            <IndicatorCard title="量价" rows={[
              { label: '今日量', value: formatVol(v.today_vol) },
              { label: '5日均量', value: formatVol(v.avg_vol_5) },
              { label: '量比', value: v.vol_ratio_vs_5 != null ? v.vol_ratio_vs_5.toFixed(2) : '-' },
              { label: '趋势', value: v.vol_trend },
            ]} />
            <IndicatorCard title="趋势/波段" rows={[
              { label: '短期', value: t.短期 },
              { label: '中期', value: t.中期 },
              { label: '30日高', value: String(t.波段?.['30日最高'] ?? '-') },
              { label: '30日低', value: String(t.波段?.['30日最低'] ?? '-') },
              { label: '分位', value: t.波段?.['当前在区间分位'] != null ? `${t.波段['当前在区间分位'].toFixed(0)}%` : '-' },
            ]} />
            <IndicatorCard title="支撑/阻力" rows={[
              { label: '密集支撑', value: s.密集支撑区?.join(', ') || '-' },
              { label: '密集阻力', value: s.密集阻力区?.join(', ') || '-' },
              { label: '5日低点', value: String(s['5日低点'] ?? '-') },
              { label: '5日高点', value: String(s['5日高点'] ?? '-') },
            ]} />
          </div>
        </div>
      </div>

      {/* K线形态 */}
      <div className="panel">
        <div className="panel-header">K线形态</div>
        <div className="panel-body" style={{ padding: '8px 14px' }}>
          <span>今日形态：</span>
          <strong>{a.candle.today}</strong>
          {a.candle.patterns.length > 0 && (
            <span style={{ marginLeft: 16 }}>
              组合信号：
              {a.candle.patterns.map((p, i) => (
                <span key={i} className={p.includes('看涨') ? 'up' : p.includes('看跌') ? 'down' : ''} style={{ marginLeft: 8 }}>
                  {p}
                </span>
              ))}
            </span>
          )}
        </div>
      </div>

      {/* 明日预判 */}
      {prediction && (
        <div className="panel" style={{ borderColor: scoreColor(prediction['综合评分'])}}>
          <div className="panel-header">
            <span>明日预判 · 综合评分 {prediction['综合评分']}</span>
            <span style={{ fontWeight: 400, fontSize: '0.75rem', color: 'var(--text2)' }}>
              评分越高越偏多
            </span>
          </div>
          <div className="panel-body" style={{ padding: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8, marginBottom: 12 }}>
              <ScenarioBox label="大概率" {...prediction['大概率情景']} />
              <ScenarioBox label="次概率" {...prediction['次概率情景']} />
              <ScenarioBox label="小概率" {...prediction['小概率情景']} />
            </div>

            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text2)', marginBottom: 4 }}>关键支撑</div>
                <div style={{ color: 'var(--green)', fontWeight: 600 }}>
                  {prediction['关键支撑位'].join(' → ')}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text2)', marginBottom: 4 }}>关键阻力</div>
                <div style={{ color: 'var(--red)', fontWeight: 600 }}>
                  {prediction['关键阻力位'].join(' → ')}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap' }}>
              {prediction['看多信号'].length > 0 && (
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--green)', marginBottom: 4 }}>看多信号</div>
                  {prediction['看多信号'].map((s, i) => (
                    <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text)', marginBottom: 2 }}>▲ {s}</div>
                  ))}
                </div>
              )}
              {prediction['看空信号'].length > 0 && (
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--red)', marginBottom: 4 }}>看空信号</div>
                  {prediction['看空信号'].map((s, i) => (
                    <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text)', marginBottom: 2 }}>▼ {s}</div>
                  ))}
                </div>
              )}
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--yellow)', marginBottom: 4 }}>关键观察</div>
                {prediction['关键观察点'].map((s, i) => (
                  <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text)', marginBottom: 2 }}>● {s}</div>
                ))}
              </div>
            </div>

            <div style={{ marginTop: 12, fontSize: '0.7rem', color: 'var(--text2)', borderTop: '1px solid var(--border)', paddingTop: 8 }}>
              {prediction['免责声明']}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function IndicatorCard({ title, rows }: { title: string; rows: { label: string; value: string; dir?: string }[] }) {
  return (
    <div style={{ background: 'var(--bg3)', borderRadius: 6, padding: 8 }}>
      <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent)', marginBottom: 6 }}>{title}</div>
      {rows.map((r, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', padding: '1px 0' }}>
          <span style={{ color: 'var(--text2)' }}>{r.label}</span>
          <span style={{
            color: r.dir === '超买' || r.dir === 'true' || r.dir?.includes('空头') ? 'var(--red)' :
                   r.dir === '超卖' || r.dir === 'false' || r.dir?.includes('多头') ? 'var(--green)' :
                   r.dir?.includes('金叉') ? 'var(--red)' :
                   r.dir?.includes('死叉') ? 'var(--green)' : undefined,
            fontWeight: r.dir ? 600 : 400,
          }}>
            {r.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function ScenarioBox({ label, 方向, 概率, 估计区间 }: { label: string; 方向: string; 概率: string; 估计区间?: string }) {
  const isBull = 方向?.includes('反弹') || 方向?.includes('突破');
  const isBear = 方向?.includes('回调') || 方向?.includes('下探') || 方向?.includes('下行');
  return (
    <div style={{
      background: 'var(--bg3)', borderRadius: 6, padding: 10, textAlign: 'center',
      borderLeft: `3px solid ${isBull ? 'var(--red)' : isBear ? 'var(--green)' : 'var(--yellow)'}`,
    }}>
      <div style={{ fontSize: '0.7rem', color: 'var(--text2)', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: '0.9rem', fontWeight: 600, color: isBull ? 'var(--red)' : isBear ? 'var(--green)' : 'var(--text)' }}>
        {方向}
      </div>
      <div style={{ fontSize: '0.8rem', color: 'var(--accent)', margin: '2px 0' }}>{概率}</div>
      {估计区间 && <div style={{ fontSize: '0.75rem', color: 'var(--text2)' }}>{估计区间}</div>}
    </div>
  );
}

function formatVol(v: number): string {
  if (v >= 100000) return `${(v / 10000).toFixed(1)}万`;
  return String(v);
}

function scoreColor(score: string): string {
  const n = parseInt(score);
  if (n >= 65) return 'var(--red)';
  if (n >= 40) return 'var(--yellow)';
  return 'var(--green)';
}
