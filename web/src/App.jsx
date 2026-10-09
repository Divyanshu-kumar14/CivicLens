import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import {
  exportCSV,
  fetchJob,
  fetchTicket,
  fetchTickets,
  overrideTicket,
  uploadJob,
} from './api/client.js';
import MapView from './components/Map/MapView.jsx';
import StatsRail from './components/Stats/StatsRail.jsx';

// Below-fold views load on demand — Map + rail stay in the initial chunk.
const ReviewQueue = lazy(() => import('./components/Queue/ReviewQueue.jsx'));
const TicketDrawer = lazy(() => import('./components/Ticket/TicketDrawer.jsx'));
const JobProgress = lazy(() => import('./components/Upload/JobProgress.jsx'));
const UploadZone = lazy(() => import('./components/Upload/UploadZone.jsx'));

// Phase-1 mock fallback: shown when the API is unreachable (Task 1.5.6).
// Phase 2 (Task 2.3.4): live data replaces these as soon as GET /tickets answers.
const MOCK_TICKETS = [
  { ticket_id: 't_hole01', centroid: [12.9716, 77.5946], severity: 82, status: 'filed',
    repeat_count: 6, crop_url: '', signals: { area_norm: 78, bus_route_w: 100, center_lane: 100 },
    created_at: '2026-10-09T08:00:00Z',
    trace: [{ ts: '2026-10-09T08:01:00Z', actor: 'agent', from_status: 'new', to_status: 'filed', reasons: ['severity 82 >= 70'], signals: {} }] },
  { ticket_id: 't_hole02', centroid: [12.973, 77.596], severity: 64, status: 'pending',
    repeat_count: 3, crop_url: '', signals: { area_norm: 55, bus_route_w: 0, center_lane: 100 },
    created_at: '2026-10-09T08:05:00Z',
    trace: [{ ts: '2026-10-09T08:06:00Z', actor: 'agent', from_status: 'new', to_status: 'pending', reasons: ['severity 64 in review band'], signals: {} }] },
  { ticket_id: 't_hole03', centroid: [12.969, 77.592], severity: 45, status: 'pending',
    repeat_count: 2, crop_url: '', signals: { area_norm: 40, bus_route_w: 0, center_lane: 30 },
    created_at: '2026-10-09T08:10:00Z', trace: [] },
  { ticket_id: 't_hole04', centroid: [12.975, 77.598], severity: 28, status: 'dismissed',
    repeat_count: 1, crop_url: '', signals: { area_norm: 20, bus_route_w: 0, center_lane: 30 },
    created_at: '2026-10-09T08:12:00Z',
    trace: [{ ts: '2026-10-09T08:13:00Z', actor: 'agent', from_status: 'new', to_status: 'dismissed', reasons: ['low_severity'], signals: {} }] },
  { ticket_id: 't_hole05', centroid: [12.97, 77.599], severity: 74, status: 'filed',
    repeat_count: 5, crop_url: '', signals: { area_norm: 70, bus_route_w: 100, center_lane: 30 },
    created_at: '2026-10-09T08:15:00Z', trace: [] },
];

const SEV_PRESET = { low: 25, med: 55, high: 85 };

export default function App() {
  const [tickets, setTickets] = useState(MOCK_TICKETS);
  const [live, setLive] = useState(false);
  const [view, setView] = useState('map'); // map | queue | upload
  const [selectedId, setSelectedId] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [showRaw, setShowRaw] = useState(false);
  const [job, setJob] = useState(null);
  const [uploading, setUploading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await fetchTickets();
      setTickets(data);
      setLive(true);
    } catch {
      setLive(false); // API down -> keep mocks, banner shows Demo mode
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const selected = tickets.find((t) => t.ticket_id === selectedId) || null;

  const openTicket = async (id) => {
    setSelectedId(id);
    if (!live) return;
    try {
      const full = await fetchTicket(id);
      setTickets((ts) => ts.map((t) => (t.ticket_id === id ? full : t)));
    } catch { /* drawer still shows list data */ }
  };

  const applyOverride = async (id, to, reason = '') => {
    if (live) {
      const updated = await overrideTicket(id, { to, reason });
      setTickets((ts) => ts.map((t) => (t.ticket_id === id ? updated : t)));
    } else {
      setTickets((ts) => ts.map((t) => (t.ticket_id === id ? { ...t, status: to } : t)));
    }
  };

  const approveSelected = () => {
    selectedIds.forEach((id) => applyOverride(id, 'filed', 'bulk approve').catch(() => {}));
    setSelectedIds(new Set());
  };
  const dismissSelected = () => {
    selectedIds.forEach((id) => applyOverride(id, 'dismissed', 'bulk dismiss').catch(() => {}));
    setSelectedIds(new Set());
  };
  const setSeveritySelected = (preset) => {
    const value = SEV_PRESET[preset];
    setTickets((ts) => ts.map((t) => (selectedIds.has(t.ticket_id) ? { ...t, severity: value } : t)));
  };

  const downloadCSV = async (status = 'filed') => {
    const blob = await exportCSV(status);
    const url = URL.createObjectURL(new Blob([blob], { type: 'text/csv' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `tickets-${status}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const submitUpload = async ({ video, gps }) => {
    setUploading(true);
    try {
      const created = await uploadJob({ video, gps });
      const fresh = await fetchJob(created.job_id);
      setJob(fresh);
      setView('map');
    } finally {
      setUploading(false);
    }
  };

  const stats = useMemo(() => {
    const by = (s) => tickets.filter((t) => t.status === s).length;
    return {
      km: live ? '—' : 12.4,
      raw: tickets.reduce((n, t) => n + (t.repeat_count || 1), 0),
      tickets: tickets.length,
      filed: by('filed'),
      review: by('pending'),
      dismissed: by('dismissed'),
      costPer1000km: live ? '—' : '$8.20',
      dedup: undefined,
    };
  }, [tickets, live]);

  return (
    <>
      <header className="cl-header">
        <span className="logo">CivicLens</span>
        <span className="ward">ward-12-demo {live ? '' : '· Demo mode (API offline)'}</span>
        <span style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          {['map', 'queue', 'upload'].map((v) => (
            <button key={v} className="btn-ghost" style={{ color: '#fff', borderColor: '#555' }}
              onClick={() => setView(v)}>
              {v[0].toUpperCase() + v.slice(1)}
            </button>
          ))}
          <button className="btn-ghost" style={{ color: '#fff', borderColor: '#555' }}
            onClick={() => downloadCSV('filed')}>
            Export CSV
          </button>
        </span>
      </header>
      <div className="cl-shell">
        <StatsRail stats={stats} />
        <Suspense fallback={<div style={{ flex: 1, padding: 20 }}>Loading…</div>}>
        {view === 'map' && (
          <MapView
            tickets={tickets}
            rawDetections={[]}
            showRaw={showRaw}
            onToggleRaw={() => setShowRaw((v) => !v)}
            onPinClick={openTicket}
          />
        )}
        {view === 'queue' && (
          <ReviewQueue
            tickets={tickets.filter((t) => t.status === 'pending')}
            selectedIds={selectedIds}
            onToggleSelect={(id) => setSelectedIds((s) => {
              const n = new Set(s);
              if (n.has(id)) n.delete(id); else n.add(id);
              return n;
            })}
            onSelectAll={() => setSelectedIds((s) => (
              s.size ? new Set() : new Set(tickets.filter((t) => t.status === 'pending').map((t) => t.ticket_id))
            ))}
            onApprove={approveSelected}
            onDismiss={dismissSelected}
            onSetSeverity={setSeveritySelected}
            onExportSelected={() => downloadCSV('filed')}
            onRowClick={openTicket}
          />
        )}
        {view === 'upload' && (
          <div style={{ flex: 1, overflowY: 'auto' }}>
            <UploadZone onSubmit={submitUpload} busy={uploading} />
            <JobProgress
              job={job}
              fetchJob={fetchJob}
              onUpdate={setJob}
              onDone={() => refresh()}
            />
          </div>
        )}
        {selected && (
          <TicketDrawer
            ticket={selected}
            onClose={() => setSelectedId(null)}
            onOverride={(id, to) => applyOverride(id, to)}
          />
        )}
        </Suspense>
      </div>
      <div className="cl-uploadbar">
        {job ? `Job ${job.job_id?.slice(0, 8)} — ${job.status}` : 'No active job — Upload tab to process a route'}
      </div>
    </>
  );
}
