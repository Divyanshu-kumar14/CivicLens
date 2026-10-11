// 3-frame context strip: before / detection / after. Falls back to the
// hero crop when the ticket carries no context frames (Phase-1 tickets).
// Demo fallback mirrors the drawer: local /demo-crops asset when no stored
// crop exists, so seed tickets show context instead of nothing.
export default function FrameStrip({ ticket }) {
  const hero = ticket.crop_url || `/demo-crops/${ticket.ticket_id}.jpg`;
  const frames = ticket.frames?.length
    ? ticket.frames
    : [hero, hero, hero].filter(Boolean);
  if (!frames.length) return null;
  return (
    <div style={{ display: 'flex', gap: 6, margin: '8px 0' }}>
      {frames.slice(0, 3).map((src, i) => (
        <img
          key={i}
          src={src}
          alt={`context ${i}`}
          style={{ width: '32%', aspectRatio: '16 / 10', objectFit: 'cover', borderRadius: 8, background: '#141a24' }}
          onError={(e) => { e.currentTarget.style.display = 'none'; }}
        />
      ))}
    </div>
  );
}
