const ACTOR_ICON = { agent: '🤖', human: '🧑' };
const STATUS_COLOR = { filed: 'green', pending: 'orange', dismissed: 'red' };

export default function TraceTimeline({ trace = [] }) {
  if (!trace.length) return <div className="cl-trace">No transitions yet.</div>;
  const entries = [...trace].reverse(); // most recent first
  return (
    <div className="cl-trace">
      <b>Trace</b>
      {entries.map((e, i) => (
        <div className="entry" key={i}>
          <span className="actor">{ACTOR_ICON[e.actor] || '•'}</span>
          <span>
            <span style={{ color: STATUS_COLOR[e.to_status] || 'inherit' }}>
              {e.from_status} → {e.to_status}
            </span>
            <br />
            <small>
              {e.ts}
              {e.reasons && e.reasons.length ? ` — ${e.reasons.join('; ')}` : ''}
            </small>
          </span>
        </div>
      ))}
    </div>
  );
}
