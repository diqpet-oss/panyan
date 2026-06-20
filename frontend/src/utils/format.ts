export function formatPrice(v: number): string {
  return v.toFixed(2);
}

export function formatChangePct(v: number): string {
  const s = v >= 0 ? `+${v.toFixed(2)}%` : `${v.toFixed(2)}%`;
  return s;
}

export function formatVolume(v: number): string {
  if (v >= 10000) return `${(v / 10000).toFixed(1)}万`;
  if (v >= 1000) return `${(v / 1000).toFixed(1)}千`;
  return v.toFixed(0);
}

export function formatAmount(v: number): string {
  if (v >= 10000) return `${(v / 10000).toFixed(2)}亿`;
  return `${v.toFixed(0)}万`;
}

export function colorForChange(v: number): string {
  if (v > 0) return '#e74c3c';
  if (v < 0) return '#27ae60';
  return '#95a5a6';
}

export function bgColorForChange(v: number): string {
  if (v > 0) return 'rgba(231, 76, 60, 0.08)';
  if (v < 0) return 'rgba(39, 174, 96, 0.08)';
  return 'transparent';
}

export function statusIcon(status: string): string {
  switch (status) {
    case 'ok': return '●';
    case 'slow': return '◐';
    case 'error': return '✕';
    default: return '○';
  }
}

export function statusColor(status: string): string {
  switch (status) {
    case 'ok': return '#27ae60';
    case 'slow': return '#f39c12';
    case 'error': return '#e74c3c';
    default: return '#95a5a6';
  }
}

export function nowStr(): string {
  const d = new Date();
  return d.toLocaleTimeString('zh-CN', { hour12: false });
}


export function formatShortDate(dateStr: string): string {
  // Format: "20240101" -> "01/01" or "YYYYMMDD" -> "MM/DD"
  if (dateStr.length >= 8) {
    return `${dateStr.slice(4, 6)}/${dateStr.slice(6, 8)}`;
  }
  if (dateStr.includes('-')) {
    const parts = dateStr.split('-');
    return `${parts[1]}/${parts[2]}`;
  }
  return dateStr;
}
