// Human labels: internal machine ids/keys must never reach the eye raw.
// `t_hole02` → "Hole 02", `area_norm` → "Damage area". Raw ids stay in
// aria-labels, webhook payloads, and exports — only the visible text changes.
export function prettyTicketId(id) {
  const m = /^t_hole0*(\d+)$/.exec(String(id || ''));
  if (m) return `Hole ${m[1].padStart(2, '0')}`;
  // Client-side demo queue entries (see DEMO_REVIEW in App.jsx).
  const d = /^t_demo0*(\d+)$/.exec(String(id || ''));
  if (d) return `Demo ${d[1].padStart(2, '0')}`;
  return String(id || '').replace(/_/g, ' ');
}

const SIGNAL_LABELS = {
  area_norm: 'Damage area',
  repeat: 'Sightings',
  bus_route: 'Bus route',
  bus_route_w: 'Bus route',
  center_lane: 'Center lane',
};

export function prettySignalKey(key) {
  if (SIGNAL_LABELS[key]) return SIGNAL_LABELS[key];
  return String(key)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const STATUS_LABELS = { filed: 'Filed', pending: 'In review', dismissed: 'Dismissed' };

export function prettyStatus(status) {
  return STATUS_LABELS[status] || String(status || '');
}
