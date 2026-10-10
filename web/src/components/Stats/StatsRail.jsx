import useCountUp from '../../utils/useCountUp.js';

function Stat({ label, value, decimals = 0 }) {
  const num = Number(value);
  const numeric = value !== undefined && value !== null && value !== '—' && !Number.isNaN(num);
  const animated = useCountUp(numeric ? num : 0);
  const text = !numeric
    ? String(value ?? '—')
    : decimals > 0 ? animated.toFixed(decimals) : String(Math.round(animated));
  return (
    <div className="cl-stat">
      <div className="label">{label}</div>
      <div className="value">{text}</div>
    </div>
  );
}

export default function StatsRail({ stats }) {
  const total = (stats.filed ?? 0) + (stats.review ?? 0) + (stats.dismissed ?? 0) || 1;
  const segs = [
    ['Filed', stats.filed ?? 0, '#ff5252'],
    ['Review', stats.review ?? 0, '#ffb020'],
    ['Dismissed', stats.dismissed ?? 0, '#6b7280'],
  ];
  return (
    <aside className="cl-rail" aria-label="Processing statistics">
      <Stat label="km processed" value={stats.km} decimals={1} />
      <Stat label="Raw detections" value={stats.raw} />
      <Stat label="Tickets after dedup" value={stats.tickets} />
      <div className="cl-statusbar" title="Filed / Review / Dismissed">
        {segs.map(([label, v, color]) => (
          <span key={label} title={`${label}: ${v}`} style={{ width: `${(v / total) * 100}%`, background: color }} />
        ))}
      </div>
      <Stat label="Filed" value={stats.filed} />
      <Stat label="Review" value={stats.review} />
      <Stat label="Dismissed" value={stats.dismissed} />
      <Stat label="Est. $/1000km" value={stats.costPer1000km} />
      {stats.dedup && (
        <span className="cl-dedup" title="Raw detections collapsed into tickets">
          {stats.dedup.from} → {stats.dedup.to} tickets
        </span>
      )}
    </aside>
  );
}
