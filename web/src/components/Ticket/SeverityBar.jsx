import { labelFor } from '../../utils/severity.js';

function barColor(severity) {
  if (severity >= 70) return '#E53935';
  if (severity >= 40) return '#FF8F00';
  return '#2E7D32';
}

export default function SeverityBar({ severity }) {
  return (
    <div>
      <div>
        <b>{severity}</b> — {labelFor(severity)}
      </div>
      <div className="sevbar">
        <div
          className="fill"
          style={{ width: `${Math.min(100, Math.max(0, severity))}%`, background: barColor(severity) }}
        />
        <div className="mark" style={{ left: '40%' }} title="review threshold" />
        <div className="mark" style={{ left: '70%' }} title="auto-file threshold" />
      </div>
    </div>
  );
}
