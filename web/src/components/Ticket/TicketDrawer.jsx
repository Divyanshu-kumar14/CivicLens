import { useState } from 'react';
import { motion } from 'framer-motion';
import { Check, ClipboardCopy, X } from 'lucide-react';
import { colorFor } from '../../utils/severity.js';
import FrameStrip from './FrameStrip.jsx';
import SeverityBar from './SeverityBar.jsx';
import TraceTimeline from './TraceTimeline.jsx';
import { Badge } from '../ui/badge.jsx';
import { Button } from '../ui/button.jsx';
import { Card } from '../ui/card.jsx';
import { Input } from '../ui/primitives.jsx';

const STATUS_LABEL = { filed: 'Filed', pending: 'In review', dismissed: 'Dismissed' };
const STATUS_BADGE = { filed: 'filed', pending: 'review', dismissed: 'dismissed' };

// Premium ticket drawer: same data + same handlers, glass skin.
// Spring entry via AnimatePresence boundary in App (Emil: never scale-from-0).
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
    <motion.aside
      className="z-20 flex w-[368px] shrink-0 flex-col gap-3 overflow-y-auto border-l border-white/8 bg-[rgba(15,18,24,0.88)] p-3.5 backdrop-blur-2xl max-md:fixed max-md:inset-x-0 max-md:bottom-0 max-md:top-auto max-md:max-h-[62vh] max-md:w-full max-md:rounded-t-2xl max-md:border-l-0 max-md:border-t"
      aria-label={`Ticket ${ticket.ticket_id}`}
      initial={{ x: 56, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 56, opacity: 0 }}
      transition={{ type: 'spring', stiffness: 380, damping: 34 }}
    >
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={onClose}>
          <X /> Close
        </Button>
        <Badge variant={STATUS_BADGE[ticket.status] || 'muted'}>
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: colorFor(ticket), boxShadow: `0 0 7px ${colorFor(ticket)}` }} />
          {STATUS_LABEL[ticket.status] || ticket.status}
        </Badge>
        {ticket.repeat_count ? (
          <span className="ml-auto text-xs tabular-nums text-slate-500">seen {ticket.repeat_count}×</span>
        ) : null}
      </div>

      <h3 className="font-display text-lg font-bold tracking-tight">{ticket.ticket_id}</h3>

      {ticket.crop_url ? (
        <img className="w-full rounded-2xl border border-white/10" src={ticket.crop_url} alt={`Crop of ${ticket.ticket_id}`} />
      ) : (
        <div className="flex aspect-video w-full items-center justify-center rounded-2xl border border-dashed border-white/12 bg-white/[0.02] text-xs text-slate-500">
          No crop stored yet
        </div>
      )}
      <FrameStrip ticket={ticket} />

      <Card className="p-3.5">
        <SeverityBar severity={editSev ?? ticket.severity} />
      </Card>

      <div className="grid grid-cols-2 gap-2">
        {Object.entries({
          area_norm: signals.area_norm,
          repeat: ticket.repeat_count,
          bus_route: signals.bus_route_w,
          center_lane: signals.center_lane,
        }).map(([k, v]) => (
          <Card key={k} className="p-2.5">
            <div className="text-[10px] font-semibold uppercase tracking-[0.07em] text-slate-500">{k}</div>
            <div className="font-display mt-0.5 text-[17px] font-bold tabular-nums">{v ?? '—'}</div>
          </Card>
        ))}
      </div>

      <div className="text-xs tabular-nums text-slate-400">
        {ticket.centroid?.[0]?.toFixed(5)}, {ticket.centroid?.[1]?.toFixed(5)}
        {ticket.created_at ? ` · ${ticket.created_at}` : ''}
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="success" size="sm" onClick={() => onOverride(ticket.ticket_id, 'filed')}>
          <Check /> Approve & Export
        </Button>
        <Button variant="dangerOutline" size="sm" onClick={() => onOverride(ticket.ticket_id, 'dismissed')}>
          Dismiss
        </Button>
        <Button variant="ghost" size="sm" onClick={copyWebhookJSON}>
          <ClipboardCopy /> Webhook JSON
        </Button>
      </div>

      <Card className="flex items-center gap-2 p-3">
        <label htmlFor="edit-sev" className="text-xs text-slate-400">Edit severity</label>
        <Input
          id="edit-sev"
          type="number"
          min="0"
          max="100"
          value={editSev ?? ticket.severity ?? 0}
          onChange={(e) => setEditSev(Number(e.target.value))}
          className="ml-auto w-[70px] tabular-nums"
        />
      </Card>

      <TraceTimeline trace={ticket.trace} />
    </motion.aside>
  );
}
