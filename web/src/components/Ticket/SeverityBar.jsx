import { useEffect, useState } from 'react';
import { labelFor } from '../../utils/severity.js';

function barColor(severity) {
  if (severity >= 70) return '#E53935';
  if (severity >= 40) return '#FF8F00';
  return '#2E7D32';
}

// Horizontal 0-100 bar: numeric value + label, animated fill, threshold
// markers at 40 (review) and 70 (auto-file). `compact` fits table rows.
// Premium skin keeps the same math — Tailwind layout, display-face numerals.
export default function SeverityBar({ severity = 0, compact = false }) {
  const [scale, setScale] = useState(0);
  useEffect(() => {
    // Normalize FIRST, then clamp: min(1, sev)/100 pinned every bar to ~1%.
    const t = requestAnimationFrame(() =>
      setScale(Math.min(1, Math.max(0, severity) / 100)),
    );
    return () => cancelAnimationFrame(t);
  }, [severity]);

  if (compact) {
    return (
      <span className="flex items-center">
        <span className="font-display mr-2 text-xs font-bold tabular-nums">{severity}</span>
        <span className="relative m-0 h-2.5 flex-1 rounded bg-[#161c26]" title={`${severity} (${labelFor(severity)})`}>
          <span
            className="block h-full w-full origin-left rounded"
            style={{ transform: `scaleX(${scale})`, background: barColor(severity), transition: 'transform 0.6s cubic-bezier(0.22, 1, 0.36, 1)' }}
          />
          <span className="absolute -top-[3px] h-4 w-0.5 bg-white/60" style={{ left: '40%' }} title="review threshold" />
          <span className="absolute -top-[3px] h-4 w-0.5 bg-white/60" style={{ left: '70%' }} title="auto-file threshold" />
        </span>
      </span>
    );
  }

  return (
    <div>
      <div className="text-sm text-slate-300">
        <span className="font-display text-lg font-bold tabular-nums text-slate-50">{severity}</span> — {labelFor(severity)}
      </div>
      <div className="relative m-0 my-[7px] h-2.5 rounded bg-[#161c26]" title={`${severity} (${labelFor(severity)})`}>
        <div
          className="h-full w-full origin-left rounded"
          style={{ transform: `scaleX(${scale})`, background: barColor(severity), transition: 'transform 0.6s cubic-bezier(0.22, 1, 0.36, 1)' }}
        />
        <div className="absolute -top-[3px] h-4 w-0.5 bg-white/60" style={{ left: '40%' }} title="review threshold" />
        <div className="absolute -top-[3px] h-4 w-0.5 bg-white/60" style={{ left: '70%' }} title="auto-file threshold" />
      </div>
    </div>
  );
}
