const STATUS_COLOR = { filed: '#ff5252', pending: '#ffb020', dismissed: '#8b94a3' };

function relative(ts) {
  const then = Date.parse(ts);
  if (Number.isNaN(then)) return ts || '';
  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)} min ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

// Vertical trace timeline, most recent first, with signal badges.
export default function TraceTimeline({ trace = [] }) {
  if (!trace.length) return <div className="cl-trace">No transitions yet.</div>;
  const entries = [...trace].reverse();
  return (
    <div className="cl-trace">
      <b>Trace</b>
      {entries.map((e, i) => (
        <div className="entry" key={i}>
          <span className={`cl-actorbadge ${e.actor === 'human' ? 'human' : 'agent'}`}>
            {e.actor === 'human' ? 'HUMAN' : 'AGENT'}
          </span>
          <span>
            <span style={{ color: STATUS_COLOR[e.to_status] || 'inherit', fontWeight: 600 }}>
              {e.from_status} → {e.to_status}
            </span>
            <br />
            <small style={{ color: 'var(--ink-2)' }}>
              {relative(e.ts)}
              {e.reasons && e.reasons.length ? ` — ${e.reasons.join('; ')}` : ''}
            </small>
            {e.signals && Object.keys(e.signals).length > 0 && (
              <div>
                {Object.entries(e.signals).map(([k, v]) => (
                  <span className="cl-sigbadge" key={k}>
                    {k}: {typeof v === 'number' ? Math.round(v) : String(v)}
                  </span>
                ))}
              </div>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
