import { useMemo } from 'react';
import L from 'leaflet';
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, Tooltip } from 'react-leaflet';
import { colorFor } from '../../utils/severity.js';

// Demo ward center (matches API sample coords).
export const DEFAULT_CENTER = [12.9716, 77.5946];

const STATUS_LABEL = { filed: 'Filed', pending: 'Review', dismissed: 'Dismissed' };

function soft(color) {
  return color + '55';
}

function pinIcon(ticket, selected) {
  const color = colorFor(ticket);
  const size = 16 + Math.min(12, (ticket.severity || 0) / 8);
  const pulse = ticket.status === 'filed' ? '<span class="pin-pulse"></span>' : '';
  return L.divIcon({
    className: 'cl-pin-wrap',
    html:
      `<span class="cl-pin${selected ? ' sel' : ''}"` +
      ` style="--pin:${color};--pin-soft:${soft(color)};width:${size}px;height:${size}px">` +
      `${pulse}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
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
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
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
        {visible.map((t) => (
          <Marker
            key={t.ticket_id}
            position={[t.centroid[0], t.centroid[1]]}
            icon={pinIcon(t, t.ticket_id === selectedId)}
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
      <div className="cl-filters">
        {Object.keys(STATUS_LABEL).map((s) => (
          <button
            key={s}
            className="cl-chip"
            aria-pressed={!statusFilter || statusFilter.has(s)}
            onClick={() => onToggleStatus(s)}
            title={`Toggle ${STATUS_LABEL[s]} pins`}
          >
            <span className="dot" style={{ background: colorFor({ status: s }) }} />
            {STATUS_LABEL[s]} {counts[s] ?? 0}
          </button>
        ))}
      </div>
      <button className="cl-rawtoggle" aria-pressed={showRaw} onClick={onToggleRaw}>
        {showRaw ? 'Hide' : 'Show'} raw detections
      </button>
      <div className="cl-legend">
        <div className="row"><span className="dot" style={{ background: '#ff5252' }} /> Filed ≥ 70</div>
        <div className="row"><span className="dot" style={{ background: '#ffb020' }} /> Review 40–69</div>
        <div className="row"><span className="dot" style={{ background: '#6b7280' }} /> Dismissed &lt; 40</div>
      </div>
    </div>
  );
}
