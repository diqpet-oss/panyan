import { Alert } from '../types';

interface Props {
  alerts: Alert[];
  onDismiss: () => void;
}

export default function AlertBanner({ alerts, onDismiss }: Props) {
  if (alerts.length === 0) return null;

  return (
    <div className="alert-banner">
      <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--red)' }}>
        ⚠ 异动告警
      </span>
      {alerts.slice(0, 6).map((a, i) => (
        <span className="alert-item" key={`${a.timestamp}-${i}`}>
          {a.message}
        </span>
      ))}
      {alerts.length > 6 && (
        <span style={{ color: 'var(--text2)', fontSize: '0.8rem' }}>
          +{alerts.length - 6} 条
        </span>
      )}
      <button className="dismiss-btn" onClick={onDismiss} title="关闭告警">
        ✕
      </button>
    </div>
  );
}
