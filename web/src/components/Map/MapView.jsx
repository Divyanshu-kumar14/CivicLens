import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import { colorFor } from '../../utils/severity.js';

// Demo ward center (matches API sample coords).
export const DEFAULT_CENTER = [12.9716, 77.5946];

export default function MapView({ tickets, rawDetections = [], showRaw, onToggleRaw, onPinClick }) {
  return (
    <div className="cl-mapwrap">
      <MapContainer center={DEFAULT_CENTER} zoom={14} scrollWheelZoom>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {showRaw &&
          rawDetections.map((d) => (
            <CircleMarker
              key={d.det_id}
              center={[d.lat, d.lon]}
              radius={3}
              pathOptions={{ color: '#666', weight: 1, fillOpacity: 0.6 }}
            />
          ))}
        {tickets.map((t) => (
          <CircleMarker
            key={t.ticket_id}
            center={[t.centroid[0], t.centroid[1]]}
            radius={6 + Math.min(8, (t.severity || 0) / 10)}
            pathOptions={{ color: colorFor(t), weight: 2, fillOpacity: 0.7 }}
            eventHandlers={{ click: () => onPinClick(t.ticket_id) }}
          >
            <Popup>
              {t.ticket_id} — severity {t.severity} ({t.status})
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <button className="cl-rawtoggle" onClick={onToggleRaw}>
        {showRaw ? 'Hide' : 'Show'} raw detections
      </button>
    </div>
  );
}
