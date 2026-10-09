import { useEffect, useState } from 'react';
import { labelFor } from '../../utils/severity.js';

function barColor(severity) {
  if (severity >= 70) return '#E53935';
  if (severity >= 40) return '#FF8F00';
  return '#2E7D32';
}

// Horizontal 0-100 bar: numeric value + label, animated fill, threshold
// markers at 40 (review) and 70 (auto-file). `compact` fits table rows.
export default function SeverityBar({ severity = 0, compact = false }) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const t = requestAnimationFrame(() =>
      setWidth(Math.min(100, Math.max(0, severity))),
    );
    return () => cancelAnimationFrame(t);
  }, [severity]);

  return (
    <div>
      {!compact && (
        <div>
          <b>{severity}</b> — {labelFor(severity)}
        </div>
      )}
      <div className="sevbar" title={`${severity} (${labelFor(severity)})`}>
        <div
          className="fill"
          style={{ width: `${width}%`, background: barColor(severity), transition: 'width 0.6s ease' }}
        />
        <div className="mark" style={{ left: '40%' }} title="review threshold" />
        <div className="mark" style={{ left: '70%' }} title="auto-file threshold" />
      </div>
    </div>
  );
}
