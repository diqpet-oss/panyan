import { useState, useEffect } from 'react';
import { colorForChange, formatChangePct } from '../utils/format';

interface KnowledgeResult {
  overall_rating: string;
  confidence: string;
  total_score: number;
  framework_breakdown: Record<string, {
    score?: number;
    principle?: string;
    source?: string;
    tags?: string[];
    signals?: string[];
    checks?: string[];
    rating?: string;
    verdict?: string;
    peg?: number;
  }>;
  behavioral_biases?: {
    severity_level: string;
    active_biases: Array<{
      bias: string;
      description: string;
      severity: number;
      mitigation: string;
      book: string;
    }>;
  };
  historical_lessons?: Array<{
    lesson: string;
    story: string;
    action: string;
    book: string;
  }>;
  applicable_books?: Array<{ book: string; relevance: string }>;
}

interface Props {
  stockCode: string | null;
  stockName: string;
}

const FRAMEWORK_ORDER = ['安全边际', '护城河', 'CAN_SLIM', '神奇公式', '彼得林奇', '趋势强度', '量价分析', '支撑阻力', '资产负债表', '盈利能力'];

export default function KnowledgeAnalysis({ stockCode, stockName }: Props) {
  const [result, setResult] = useState<KnowledgeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'scores' | 'biases' | 'lessons' | 'books'>('scores');

  useEffect(() => {
    if (!stockCode) return;
    setLoading(true);
    setError('');
    fetch(`/api/v1/knowledge/analyze/${stockCode}`)
      .then(r => r.json())
      .then(d => {
        if (d.error) { setError(d.error); setResult(null); }
        else { setResult(d as KnowledgeResult); }
      })
      .catch(() => setError('分析请求失败'))
      .finally(() => setLoading(false));
  }, [stockCode]);

  if (!stockCode) {
    return (
      <div className="panel" style={{ padding: '24px', textAlign: 'center', color: 'var(--text2)', fontSize: '0.9rem' }}>
        选择一只自选股查看知识库分析
      </div>
    );
  }

  return (
    <div className="panel" style={{ marginTop: 0 }}>
      <div className="panel-header" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span>知识库分析 — {stockName}</span>
        <div style={{ display: 'flex', gap: 4, marginLeft: 'auto' }}>
          {(['scores', 'biases', 'lessons', 'books'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={tab === t ? 'tab-active' : ''}
              style={{
                padding: '2px 10px', fontSize: '0.75rem', borderRadius: 4,
                border: '1px solid var(--border)', cursor: 'pointer',
                background: tab === t ? 'var(--accent)' : 'var(--bg3)',
                color: tab === t ? '#fff' : 'var(--text)',
              }}
            >{{
              scores: '评分', biases: '偏差', lessons: '教训', books: '书单'
            }[t]}</button>
          ))}
        </div>
      </div>

      {loading && <div style={{ padding: 20, textAlign: 'center', color: 'var(--text2)' }}>分析中...</div>}
      {error && <div style={{ padding: 20, textAlign: 'center', color: 'var(--red)' }}>{error}</div>}
      {!result && !loading && !error && <div style={{ padding: 20, textAlign: 'center', color: 'var(--text2)' }}>等待分析结果</div>}
      {!result && loading && <div style={{ padding: 20, textAlign: 'center', color: 'var(--text2)' }}>请求中...</div>}

      {result && tab === 'scores' && (
        <div style={{ padding: 12 }}>
          {/* 总评 */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 16,
            padding: 12, marginBottom: 12,
            borderRadius: 8,
            background: result.total_score >= 6 ? 'rgba(39,174,96,0.1)' : result.total_score >= 4 ? 'rgba(243,156,18,0.1)' : 'rgba(231,76,60,0.1)',
          }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{result.overall_rating}</div>
            <div>
              <div style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                综合评分 {result.total_score}/10
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text2)' }}>
                置信度 {result.confidence}
              </div>
            </div>
          </div>

          {/* 框架评分网格 */}
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 8
          }}>
            {FRAMEWORK_ORDER.map(key => {
              const fw = result.framework_breakdown[key];
              if (!fw || fw.score === undefined) return null;
              const score = fw.score;
              return (
                <div key={key} style={{
                  padding: '8px 10px', borderRadius: 6,
                  background: score >= 7 ? 'rgba(39,174,96,0.08)' : score >= 4 ? 'rgba(243,156,18,0.08)' : 'rgba(231,76,60,0.08)',
                  border: '1px solid var(--border)',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>{key}</span>
                    <span style={{
                      fontSize: '0.8rem', fontWeight: 700,
                      color: score >= 7 ? 'var(--green)' : score >= 4 ? 'var(--yellow)' : 'var(--red)',
                    }}>{score}/10</span>
                  </div>
                  {fw.verdict && <div style={{ fontSize: '0.75rem', color: 'var(--text2)' }}>{fw.verdict}</div>}
                  {fw.tags && <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 4 }}>
                    {fw.tags.map((t: string) => (
                      <span key={t} style={{
                        fontSize: '0.7rem', padding: '1px 6px', borderRadius: 3,
                        background: 'var(--bg3)', color: 'var(--accent)',
                      }}>{t}</span>
                    ))}
                  </div>}
                  {fw.signals && fw.signals.slice(0, 2).map((s: string) => (
                    <div key={s} style={{ fontSize: '0.7rem', color: 'var(--text2)', marginTop: 2 }}>{s}</div>
                  ))}
                  {fw.principle && (
                    <div style={{ fontSize: '0.65rem', color: 'var(--text2)', marginTop: 4, fontStyle: 'italic', borderTop: '1px solid var(--border)', paddingTop: 4 }}>
                      {fw.principle}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {result && tab === 'biases' && result.behavioral_biases && (
        <div style={{ padding: 12 }}>
          <div style={{
            padding: '8px 12px', marginBottom: 10, borderRadius: 6,
            background: result.behavioral_biases.severity_level === '高' ? 'rgba(231,76,60,0.1)' : 'rgba(243,156,18,0.1)',
          }}>
            <strong>认知偏差风险: {result.behavioral_biases.severity_level}</strong>
            <span style={{ fontSize: '0.8rem', color: 'var(--text2)', marginLeft: 8 }}>
              ({result.behavioral_biases.active_biases.length} 个偏差)
            </span>
          </div>
          {result.behavioral_biases.active_biases.map((b, i) => (
            <div key={i} style={{
              padding: '8px 10px', marginBottom: 6, borderRadius: 6,
              background: 'var(--bg3)',
              borderLeft: `3px solid ${b.severity >= 3 ? 'var(--red)' : 'var(--yellow)'}`,
            }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{b.bias}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text2)', marginTop: 2 }}>{b.description}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--accent)' }}>🔧 {b.mitigation}</span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text2)' }}>{b.book}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {result && tab === 'lessons' && result.historical_lessons && (
        <div style={{ padding: 12 }}>
          {result.historical_lessons.map((l, i) => (
            <div key={i} style={{
              padding: '10px 12px', marginBottom: 8, borderRadius: 6,
              background: 'var(--bg3)',
            }}>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: 4 }}>📖 {l.lesson}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text2)', marginBottom: 4 }}>{l.story}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--accent)' }}>👉 {l.action}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text2)', marginTop: 4 }}>{l.book}</div>
            </div>
          ))}
        </div>
      )}

      {result && tab === 'books' && (
        <div style={{ padding: 12 }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: 8 }}>基于当前分析推荐的书籍</div>
          {result.applicable_books && result.applicable_books.length > 0 ? (
            result.applicable_books.map((b, i) => (
              <div key={i} style={{
                padding: '8px 10px', marginBottom: 6, borderRadius: 6,
                background: 'var(--bg3)',
              }}>
                <div style={{ fontWeight: 500, fontSize: '0.85rem' }}>{b.book}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--accent)' }}>{b.relevance}</div>
              </div>
            ))
          ) : (
            <div style={{ color: 'var(--text2)', fontSize: '0.8rem', textAlign: 'center', padding: 12 }}>
              暂无特定推荐。查看完整书单可访问 API /api/v1/knowledge/book-list
            </div>
          )}
          <div style={{ marginTop: 12, paddingTop: 8, borderTop: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: 6 }}>推荐阅读路径</div>
            <div style={{
              display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: '0.75rem'
            }}>
              {[
                { level: '入门(建立认知)', books: '《投资最重要的事》《漫步华尔街》《思考，快与慢》' },
                { level: '进阶(学会选股)', books: '《聪明的投资者》《彼得·林奇的成功投资》' },
                { level: '提高(学会交易)', books: '《海龟交易法则》《以交易为生》' },
                { level: '高阶(看周期)', books: '《周期》《黑天鹅》' },
              ].map(item => (
                <div key={item.level} style={{ padding: '6px 8px', borderRadius: 4, background: 'var(--bg)' }}>
                  <div style={{ color: 'var(--accent)', fontWeight: 600, marginBottom: 2 }}>{item.level}</div>
                  <div style={{ color: 'var(--text2)' }}>{item.books}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
