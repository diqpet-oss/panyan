import { nowStr } from '../utils/format';

interface Props {
  isOnline: boolean;
  timestamp: string;
  alertCount: number;
}

export default function Header({ isOnline, timestamp, alertCount }: Props) {
  return (
    <header className="header">
      <h1>
        <span>盘眼</span> PanYan
        <span style={{ fontSize: '0.7rem', color: 'var(--text2)', fontWeight: 400 }}>
          五工具统一实时分析系统
        </span>
      </h1>
      <div className="header-right">
        <span>
          <span className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
          {isOnline ? '已连接' : '重连中...'}
        </span>
        {alertCount > 0 && (
          <span className="alert-badge">
            ⚠ {alertCount} 条告警
          </span>
        )}
        <span style={{ color: 'var(--text2)' }}>{timestamp || nowStr()}</span>
      </div>
    </header>
  );
}
