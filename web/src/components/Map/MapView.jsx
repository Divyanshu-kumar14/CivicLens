import { useMemo } from 'react';
import L from 'leaflet';
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, Tooltip } from 'react-leaflet';
import { colorFor } from '../../utils/severity.js';

// Demo ward center (matches API sample coords).
export const DEFAULT_CENTER = [12.9716, 77.5946];

const STATUS_LABEL = { filed: 'Filed', pending: 'Review', dismissed: 'Dismissed' };

// Icon cache: rebuilding L.divIcon objects on every parent render forces
// Leaflet to tear down and re-add every marker. Keyed by visual signature so
// icons rebuild only when something visible actually changed. Bounded at 2000
// entries (evict oldest) so long sessions can't leak.
const iconCache = new Map();
const ICON_CACHE_LIMIT = 2000;

function soft(color) {
  return color + '55';
}

function pinIcon(ticket, selected, delayMs = 0) {
  const key = `${ticket.ticket_id}|${ticket.severity}|${ticket.status}|${selected}`;
  const hit = iconCache.get(key);
  if (hit) return hit;
  const color = colorFor(ticket);
  const size = 16 + Math.min(12, (ticket.severity || 0) / 8);
  const pulse = ticket.status === 'filed' ? '<span class="pin-pulse"></span>' : '';
  const icon = L.divIcon({
    className: 'cl-pin-wrap',
    // --pin-delay staggers the one-shot drop-in so a full map blooms instead
    // of popping; capped so large fleets don't cascade forever.
    html:
      `<span class="cl-pin${selected ? ' sel' : ''}"` +
      ` style="--pin:${color};--pin-soft:${soft(color)};width:${size}px;height:${size}px;--pin-delay:${delayMs}ms">` +
      `${pulse}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
  if (iconCache.size >= ICON_CACHE_LIMIT) iconCache.delete(iconCache.keys().next().value);
  iconCache.set(key, icon);
  return icon;
}

export default function MapView({
  tickets,
  rawDetections = [],
  showRaw,
  onToggleRaw,
  onPinClick,
  selectedId,
  statusFilter,
  onToggleStatus,
}) {
  const visible = useMemo(
    () => tickets.filter((t) => !statusFilter || statusFilter.has(t.status)),
    [tickets, statusFilter],
  );
  const counts = useMemo(() => {
    const c = { filed: 0, pending: 0, dismissed: 0 };
    tickets.forEach((t) => { if (c[t.status] !== undefined) c[t.status] += 1; });
    return c;
  }, [tickets]);

  return (
    <div className="cl-mapwrap">
      <MapContainer center={DEFAULT_CENTER} zoom={14} scrollWheelZoom>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {showRaw &&
          rawDetections.map((d) => (
            <CircleMarker
              key={d.det_id}
              center={[d.lat, d.lon]}
              radius={2.5}
              pathOptions={{ color: '#8b94a3', weight: 1, fillOpacity: 0.55 }}
            />
          ))}
        {visible.map((t, i) => (
          <Marker
            key={t.ticket_id}
            position={[t.centroid[0], t.centroid[1]]}
            icon={pinIcon(t, t.ticket_id === selectedId, Math.min(i, 20) * 18)}
            keyboard
            title={`${t.ticket_id}, severity ${t.severity}, ${STATUS_LABEL[t.status] || t.status}`}
            eventHandlers={{ click: () => onPinClick(t.ticket_id) }}
          >
            <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
              {t.ticket_id} · {t.severity} ({STATUS_LABEL[t.status] || t.status})
            </Tooltip>
            <Popup>
              {t.ticket_id} — severity {t.severity} ({t.status})
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      <div className="absolute left-[52px] top-3 z-[500] flex gap-1.5">
        {Object.keys(STATUS_LABEL).map((s) => {
          const on = !statusFilter || statusFilter.has(s);
          return (
          <button
            key={s}
            aria-pressed={on}
            onClick={() => onToggleStatus(s)}
            title={`Toggle ${STATUS_LABEL[s]} pins`}
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold backdrop-blur-xl transition-all duration-150 hover:-translate-y-px ${
              on
                ? 'border-white/12 bg-[rgba(12,15,21,0.88)] text-slate-200'
                : 'border-white/8 bg-[rgba(12,15,21,0.6)] text-slate-500 opacity-50'
            }`}
          >
            <span className="h-2 w-2 rounded-full" style={{ background: colorFor({ status: s }), boxShadow: `0 0 6px ${colorFor({ status: s })}` }} />
            {STATUS_LABEL[s]} <span className="tabular-nums">{counts[s] ?? 0}</span>
          </button>
          );
        })}
      </div>
      <button
        aria-pressed={showRaw}
        onClick={onToggleRaw}
        className={`absolute right-3 top-3 z-[500] rounded-[10px] border px-3 py-2 text-[13px] font-semibold backdrop-blur-xl transition-colors ${
          showRaw
            ? 'border-cyan-300/60 bg-[rgba(12,15,21,0.9)] text-cyan-100'
            : 'border-white/10 bg-[rgba(12,15,21,0.88)] text-slate-100 hover:border-white/25'
        }`}
      >
        {showRaw ? 'Hide' : 'Show'} raw detections
      </button>
      <div className="absolute bottom-[26px] left-3 z-[500] rounded-[10px] border border-white/10 bg-[rgba(12,15,21,0.88)] px-3 py-2 text-xs text-slate-400 backdrop-blur-xl">
        <div className="my-1 flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: '#ff5252' }} /> Filed ≥ 70</div>
        <div className="my-1 flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: '#ffb020' }} /> Review 40–69</div>
        <div className="my-1 flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: '#6b7280' }} /> Dismissed &lt; 40</div>
      </div>
    </div>
  );
}
