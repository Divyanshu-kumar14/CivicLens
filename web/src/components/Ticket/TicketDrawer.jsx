import { useState } from 'react';
import SeverityBar from './SeverityBar.jsx';
import TraceTimeline from './TraceTimeline.jsx';

export default function TicketDrawer({ ticket, onClose, onOverride }) {
  const [editSev, setEditSev] = useState(null);
  if (!ticket) return null;
  const signals = ticket.signals || {};

  const copyWebhookJSON = () => {
    const payload = {
      event: 'ticket.filed',
      ticket_id: ticket.ticket_id,
      lat: ticket.centroid?.[0],
      lon: ticket.centroid?.[1],
      severity: editSev ?? ticket.severity,
      status: ticket.status,
      crop_url: ticket.crop_url,
    };
    navigator.clipboard?.writeText(JSON.stringify(payload, null, 2));
  };

  return (
    <aside className="cl-drawer">
      <button className="btn-ghost" onClick={onClose}>← Close</button>
      <h3>{ticket.ticket_id}</h3>
      {ticket.crop_url ? (
        <img className="hero" src={ticket.crop_url} alt="detection crop" />
      ) : (
        <img className="hero" alt="no crop yet" />
      )}
      <SeverityBar severity={editSev ?? ticket.severity} />
      <div className="cl-signals">
        {Object.entries({
          area_norm: signals.area_norm,
          repeat: ticket.repeat_count,
          bus_route: signals.bus_route_w,
          center_lane: signals.center_lane,
        }).map(([k, v]) => (
          <div className="sig" key={k}>
            {k}<b>{v ?? '—'}</b>
          </div>
        ))}
      </div>
      <div>
        <small>
          📍 {ticket.centroid?.[0]}, {ticket.centroid?.[1]}
          {ticket.created_at ? ` · ${ticket.created_at}` : ''}
        </small>
      </div>
      <div className="cl-actions">
        <button className="btn-file" onClick={() => onOverride(ticket.ticket_id, 'filed')}>
          Approve &amp; Export
        </button>
        <button className="btn-dismiss" onClick={() => onOverride(ticket.ticket_id, 'dismissed')}>
          Dismiss
        </button>
        <button className="btn-ghost" onClick={copyWebhookJSON}>Copy Webhook JSON</button>
      </div>
      <div>
        <label>
          Edit severity:{' '}
          <input
            type="number"
            min="0"
            max="100"
            value={editSev ?? ticket.severity ?? 0}
            onChange={(e) => setEditSev(Number(e.target.value))}
            style={{ width: 70 }}
          />
        </label>
      </div>
      <TraceTimeline trace={ticket.trace} />
    </aside>
  );
}
