import { useState } from 'react';
import { motion } from 'framer-motion';
import { colorFor } from '../../utils/severity.js';
import FrameStrip from './FrameStrip.jsx';
import SeverityBar from './SeverityBar.jsx';
import TraceTimeline from './TraceTimeline.jsx';

const STATUS_LABEL = { filed: 'Filed', pending: 'In review', dismissed: 'Dismissed' };

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
    // Spring entry (Emil: entering elements ease-out with presence, never from
    // scale(0)); exit is handled by the AnimatePresence boundary in App.
    <motion.aside
      className="cl-drawer"
      aria-label={`Ticket ${ticket.ticket_id}`}
      initial={{ x: 56, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 56, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 380, damping: 34 }}
    >
      <button className="btn-ghost" onClick={onClose}>← Close</button>
      <h3>{ticket.ticket_id}</h3>
      <div className="cl-statusline">
        <span className="dot" style={{ background: colorFor(ticket) }} />
        {STATUS_LABEL[ticket.status] || ticket.status}
        {ticket.repeat_count ? ` · seen ${ticket.repeat_count}×` : ''}
      </div>
      {ticket.crop_url ? (
        <img className="hero" src={ticket.crop_url} alt={`Crop of ${ticket.ticket_id}`} />
      ) : (
        <div className="cl-hero-empty">No crop stored yet</div>
      )}
      <FrameStrip ticket={ticket} />
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
      <div className="cl-meta">
        {ticket.centroid?.[0]?.toFixed(5)}, {ticket.centroid?.[1]?.toFixed(5)}
        {ticket.created_at ? ` · ${ticket.created_at}` : ''}
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
    </motion.aside>
  );
}
