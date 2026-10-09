// 3-frame context strip: before / detection / after. Falls back to the
// hero crop when the ticket carries no context frames (Phase-1 tickets).
export default function FrameStrip({ ticket }) {
  const frames = ticket.frames?.length
    ? ticket.frames
    : [ticket.crop_url, ticket.crop_url, ticket.crop_url].filter(Boolean);
  if (!frames.length) return null;
  return (
    <div style={{ display: 'flex', gap: 6, margin: '8px 0' }}>
      {frames.slice(0, 3).map((src, i) => (
        <img
          key={i}
          src={src}
          alt={`context ${i}`}
          style={{ width: '32%', borderRadius: 4, background: '#ddd' }}
        />
      ))}
    </div>
  );
}
