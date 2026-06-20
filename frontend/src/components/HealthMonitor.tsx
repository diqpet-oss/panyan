import { HealthStatus as HealthType } from '../types';
import { statusIcon, statusColor } from '../utils/format';

interface Props {
  sources: HealthType[];
}

export default function HealthMonitor({ sources }: Props) {
  return (
    <div className="panel health-monitor">
      <div className="panel-header">数据源监控</div>
      <div className="panel-body">
        {sources.length === 0 ? (
          <div style={{ padding: '8px 12px', fontSize: '0.8rem', color: 'var(--text2)' }}>
            检查中...
          </div>
        ) : (
          sources.map((s) => (
            <div className="health-item" key={s.source}>
              <div className="h-source">
                <span style={{ color: statusColor(s.status) }}>{statusIcon(s.status)}</span>
                <span>{s.source}</span>
              </div>
              <div className="h-status" style={{ color: statusColor(s.status) }}>
                {s.status === 'ok' ? `正常 ${s.latency_ms.toFixed(0)}ms` :
                 s.status === 'slow' ? `延迟 ${s.latency_ms.toFixed(0)}ms` :
                 s.status === 'error' ? '异常' : '未知'}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
