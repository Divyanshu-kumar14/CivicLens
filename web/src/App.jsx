import { useState } from 'react';
import MapView from './components/Map/MapView.jsx';
import TicketDrawer from './components/Ticket/TicketDrawer.jsx';
import StatsRail from './components/Stats/StatsRail.jsx';

// Phase-1 mock data: proves layout before real data flows (Task 1.5.6).
// Phase 2 (Task 2.3.4) replaces these with GET /tickets.
const MOCK_TICKETS = [
  { ticket_id: 't_hole01', centroid: [12.9716, 77.5946], severity: 82, status: 'filed',
    repeat_count: 6, crop_url: '', signals: { area_norm: 78, bus_route_w: 100, center_lane: 100 },
    created_at: '2026-10-09T08:00:00Z',
    trace: [{ ts: '2026-10-09T08:01:00Z', actor: 'agent', from_status: 'new', to_status: 'filed', reasons: ['severity 82 >= 70'], signals: {} }] },
  { ticket_id: 't_hole02', centroid: [12.9730, 77.5960], severity: 64, status: 'pending',
    repeat_count: 3, crop_url: '', signals: { area_norm: 55, bus_route_w: 0, center_lane: 100 },
    created_at: '2026-10-09T08:05:00Z',
    trace: [{ ts: '2026-10-09T08:06:00Z', actor: 'agent', from_status: 'new', to_status: 'pending', reasons: ['severity 64 in review band'], signals: {} }] },
  { ticket_id: 't_hole03', centroid: [12.9690, 77.5920], severity: 45, status: 'pending',
    repeat_count: 2, crop_url: '', signals: { area_norm: 40, bus_route_w: 0, center_lane: 30 },
    created_at: '2026-10-09T08:10:00Z', trace: [] },
  { ticket_id: 't_hole04', centroid: [12.9750, 77.5980], severity: 28, status: 'dismissed',
    repeat_count: 1, crop_url: '', signals: { area_norm: 20, bus_route_w: 0, center_lane: 30 },
    created_at: '2026-10-09T08:12:00Z',
    trace: [{ ts: '2026-10-09T08:13:00Z', actor: 'agent', from_status: 'new', to_status: 'dismissed', reasons: ['low_severity'], signals: {} }] },
  { ticket_id: 't_hole05', centroid: [12.9700, 77.5990], severity: 74, status: 'filed',
    repeat_count: 5, crop_url: '', signals: { area_norm: 70, bus_route_w: 100, center_lane: 30 },
    created_at: '2026-10-09T08:15:00Z', trace: [] },
];

const MOCK_STATS = {
  km: 12.4, raw: 100, tickets: 12, filed: 5, review: 4, dismissed: 3,
  costPer1000km: '$8.20', dedup: { from: 100, to: 12 },
};

export default function App() {
  const [tickets, setTickets] = useState(MOCK_TICKETS);
  const [selectedId, setSelectedId] = useState(null);
  const [showRaw, setShowRaw] = useState(false);

  const selected = tickets.find((t) => t.ticket_id === selectedId) || null;

  const handleOverride = (ticket_id, to) => {
    // Phase 1: local state only. Phase 2 posts to /tickets/{id}/override.
    setTickets((ts) => ts.map((t) => (t.ticket_id === ticket_id ? { ...t, status: to } : t)));
  };

  return (
    <>
      <header className="cl-header">
        <span className="logo">CivicLens</span>
        <span className="ward">ward-12-demo</span>
      </header>
      <div className="cl-shell">
        <StatsRail stats={MOCK_STATS} />
        <MapView
          tickets={tickets}
          rawDetections={[]}
          showRaw={showRaw}
          onToggleRaw={() => setShowRaw((v) => !v)}
          onPinClick={setSelectedId}
        />
        {selected && (
          <TicketDrawer
            ticket={selected}
            onClose={() => setSelectedId(null)}
            onOverride={handleOverride}
          />
        )}
      </div>
      <div className="cl-uploadbar">Upload zone (collapsed) — drag-drop mp4 + gps.csv lands in Phase 2</div>
    </>
  );
}
