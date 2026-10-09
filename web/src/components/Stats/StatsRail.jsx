export default function StatsRail({ stats }) {
  const rows = [
    ['km processed', stats.km],
    ['Raw detections', stats.raw],
    ['Tickets after dedup', stats.tickets],
    ['Filed', stats.filed],
    ['Review', stats.review],
    ['Dismissed', stats.dismissed],
    ['Est. $/1000km', stats.costPer1000km],
  ];
  return (
    <aside className="cl-rail">
      {rows.map(([label, value]) => (
        <div className="cl-stat" key={label}>
          <div className="label">{label}</div>
          <div className="value">{value ?? '—'}</div>
        </div>
      ))}
      {stats.dedup && (
        <span className="cl-dedup">
          {stats.dedup.from} → {stats.dedup.to}
        </span>
      )}
    </aside>
  );
}
