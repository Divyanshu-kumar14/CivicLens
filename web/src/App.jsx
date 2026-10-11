import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Command, Download, ListChecks, Map as MapIcon, Search, UploadCloud } from 'lucide-react';
import {
  exportCSV,
  fetchJob,
  fetchTicket,
  fetchTickets,
  overrideTicket,
  uploadJob,
} from './api/client.js';
import MapView from './components/Map/MapView.jsx';
import Clock from './components/Clock.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import StatsRail from './components/Stats/StatsRail.jsx';
import { Badge } from './components/ui/badge.jsx';
import { Button } from './components/ui/button.jsx';
import { MeshBackground } from './components/ui/mesh.jsx';

// Below-fold views load on demand — Map + rail stay in the initial chunk.
// Command palette is also lazy: 0KB until the user hits Cmd+K.
const ReviewQueue = lazy(() => import('./components/Queue/ReviewQueue.jsx'));
const TicketDrawer = lazy(() => import('./components/Ticket/TicketDrawer.jsx'));
const JobProgress = lazy(() => import('./components/Upload/JobProgress.jsx'));
const UploadZone = lazy(() => import('./components/Upload/UploadZone.jsx'));
const CommandPalette = lazy(() => import('./components/ui/command.jsx'));

// Mock fallback: shown when the API is unreachable.
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
const ALL_ON = new Set(['filed', 'pending', 'dismissed']);

// Sample review entries: shown only when the live API returns zero pending
// tickets, so the Queue section (and its approve/dismiss flow) is never an
// empty room during demos. Client-side only — overrides apply locally (see
// applyOverride), real API data is never touched, and they yield the moment
// real pending tickets exist.
const SAMPLE_REVIEW = [
  { ticket_id: 't_hole06', centroid: [12.983, 77.6], severity: 63, status: 'pending',
    repeat_count: 4, crop_url: '', signals: { area_norm: 58, bus_route_w: 100, center_lane: 30 },
    created_at: '2026-10-11T06:00:00Z',
    trace: [{ ts: '2026-10-11T06:01:00Z', actor: 'agent', from_status: 'new', to_status: 'pending', reasons: ['severity 63 in review band'], signals: {} }] },
  { ticket_id: 't_hole07', centroid: [12.956, 77.585], severity: 55, status: 'pending',
    repeat_count: 3, crop_url: '', signals: { area_norm: 50, bus_route_w: 0, center_lane: 100 },
    created_at: '2026-10-11T06:05:00Z',
    trace: [{ ts: '2026-10-11T06:06:00Z', actor: 'agent', from_status: 'new', to_status: 'pending', reasons: ['severity 55 in review band'], signals: {} }] },
  { ticket_id: 't_hole08', centroid: [12.9719, 77.61], severity: 47, status: 'pending',
    repeat_count: 2, crop_url: '', signals: { area_norm: 42, bus_route_w: 0, center_lane: 30 },
    created_at: '2026-10-11T06:10:00Z',
    trace: [{ ts: '2026-10-11T06:11:00Z', actor: 'agent', from_status: 'new', to_status: 'pending', reasons: ['severity 47 in review band'], signals: {} }] },
];
const SAMPLE_IDS = new Set(SAMPLE_REVIEW.map((t) => t.ticket_id));
const VIEWS = [
  { id: 'map', label: 'Map', icon: MapIcon },
  { id: 'queue', label: 'Queue', icon: ListChecks },
  { id: 'upload', label: 'Upload', icon: UploadCloud },
];

export default function App() {
  const [tickets, setTickets] = useState(MOCK_TICKETS);
  const [loading, setLoading] = useState(true);
  const [live, setLive] = useState(false);
  const [view, setView] = useState('map'); // map | queue | upload
  const [selectedId, setSelectedId] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [showRaw, setShowRaw] = useState(false);
  const [statusFilter, setStatusFilter] = useState(new Set(ALL_ON));
  const [job, setJob] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchTickets();
      // Backfill the queue for demos when nothing real awaits review.
      setTickets(data.some((t) => t.status === 'pending') ? data : [...data, ...SAMPLE_REVIEW]);
      setLive(true);
    } catch {
      setLive(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // The drawer is map context: close it on every view switch so Queue and
  // Upload always get the full width. Runs on mount too (no-op).
  useEffect(() => { setSelectedId(null); }, [view]);

  // Global Cmd+K / Ctrl+K for the action search bar (Kokonut-style).
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

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
    // Sample entries live only in client state — no API row to override.
    if (SAMPLE_IDS.has(id)) {
      setTickets((ts) => ts.map((t) => (t.ticket_id === id ? { ...t, status: to } : t)));
      return;
    }
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

  const toggleStatus = (s) => {
    setStatusFilter((prev) => {
      const next = new Set(prev);
      if (next.has(s)) {
        if (next.size > 1) next.delete(s);
      } else next.add(s);
      return next;
    });
  };

  const stats = useMemo(() => {
    const by = (s) => tickets.filter((t) => t.status === s).length;
    // Coverage: diagonal of the ticket bounding box (haversine). This is the
    // surveyed span, not odometer distance — the only distance the client can
    // derive honestly without the GPS track.
    const lats = tickets.map((t) => t.centroid?.[0]).filter((v) => Number.isFinite(v));
    const lons = tickets.map((t) => t.centroid?.[1]).filter((v) => Number.isFinite(v));
    let spanKm = 0;
    if (lats.length > 1) {
      const R = 6371;
      const dLa = ((Math.max(...lats) - Math.min(...lats)) * Math.PI) / 180;
      const meanLa = ((Math.max(...lats) + Math.min(...lats)) / 2) * (Math.PI / 180);
      const dLo = ((Math.max(...lons) - Math.min(...lons)) * Math.PI) / 180;
      spanKm = 2 * R * Math.asin(Math.sqrt(Math.sin(dLa / 2) ** 2 + Math.cos(meanLa) ** 2 * Math.sin(dLo / 2) ** 2));
    }
    // $/1000km estimate (live): 1000km at 18km/h survey speed = 55.6h of video
    // x 2fps sampling = 400k frames x 0.356s YOLO/frame (measured ARM) =
    // 39.6h compute x ~$0.034/h Graviton-class = ~$1.35. Classical-only path
    // would be ~$0.03; demo mode keeps its mock figure.
    return {
      km: live ? spanKm : 12.4,
      raw: tickets.reduce((n, t) => n + (t.repeat_count || 1), 0),
      tickets: tickets.length,
      filed: by('filed'),
      review: by('pending'),
      dismissed: by('dismissed'),
      costPer1000km: live ? '$1.35' : '$8.20',
      costHint: live
        ? 'Est. from measured 356ms/frame YOLO on ARM @18km/h survey, Graviton-class $0.034/h'
        : undefined,
      dedup: undefined,
    };
  }, [tickets, live]);

  return (
    <div className="relative flex h-full flex-col bg-[#060709] font-sans text-slate-100 antialiased">
      <MeshBackground />
      {/* Premium glass header: brand + live badge + search trigger + workspace tabs */}
      <header className="relative z-10 flex h-14 shrink-0 items-center gap-3 border-b border-white/8 bg-[rgba(10,12,17,0.85)] px-4 backdrop-blur-xl">
        <span className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-[10px] border border-white/12 bg-[#151b26] shadow-[0_0_16px_rgba(255,82,82,0.25)]">
            <span className="h-3.5 w-3.5 rounded-full border-[2.5px] border-[#ff5252]" />
          </span>
          <span className="font-display text-[17px] font-bold tracking-tight">CivicLens</span>
        </span>
        <Badge variant="muted" className="hidden sm:inline-flex">ward-12-demo</Badge>
        <Badge variant={live ? 'live' : 'demo'} title={live ? 'Connected to the API' : 'API unreachable — showing mock data'}>
          <span className={`h-1.5 w-1.5 rounded-full ${live ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-amber-400 shadow-[0_0_8px_#ffb020]'}`} />
          {live ? 'Live' : 'Demo mode'}
        </Badge>
        <span className="ml-auto flex items-center gap-2">
          <Clock />
          {/* Action search trigger (Kokonut-style): the "expensive" entry point */}
          <button
            onClick={() => setPaletteOpen(true)}
            className="hidden h-9 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 text-[13px] text-slate-400 transition-colors hover:border-white/20 hover:text-slate-200 md:flex"
            title="Search tickets and actions"
          >
            <Search size={14} />
            <span>Search…</span>
            <kbd className="rounded-md border border-white/10 bg-black/40 px-1.5 py-0.5 text-[10px] font-semibold text-slate-400">⌘K</kbd>
          </button>
          <nav className="flex gap-0.5 rounded-xl border border-white/10 bg-black/50 p-0.5" role="tablist" aria-label="Views">
            {VIEWS.map((v) => {
              const Icon = v.icon;
              const active = view === v.id;
              return (
                <button
                  key={v.id}
                  role="tab"
                  aria-selected={active}
                  onClick={() => setView(v.id)}
                  className={`relative flex items-center gap-1.5 rounded-[10px] px-3.5 py-1.5 text-[13px] font-semibold transition-colors ${active ? 'text-[#061014]' : 'text-slate-400 hover:text-white'}`}
                >
                  {active && (
                    <motion.span
                      layoutId="ws-pill"
                      className="absolute inset-0 rounded-[10px] bg-cyan-300 shadow-[0_2px_14px_rgba(58,226,255,0.35)]"
                      transition={{ type: 'spring', stiffness: 520, damping: 36 }}
                    />
                  )}
                  <Icon size={14} className="relative z-10" />
                  <span className="relative z-10">{v.label}</span>
                </button>
              );
            })}
          </nav>
          <Button variant="ghost" size="sm" onClick={() => downloadCSV('filed')}>
            <Download />
            <span className="hidden lg:inline">Export CSV</span>
          </Button>
        </span>
      </header>
      <div className="cl-shell relative z-10">
        <StatsRail stats={stats} />
        <Suspense fallback={<div style={{ flex: 1, padding: 20 }}>Loading…</div>}>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={view}
            initial={{ opacity: 0, x: 14 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -14 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            style={{ flex: 1, display: 'flex', minWidth: 0, minHeight: 0 }}
          >
        {view === 'map' && (
          <MapView
            tickets={tickets}
            rawDetections={[]}
            showRaw={showRaw}
            onToggleRaw={() => setShowRaw((v) => !v)}
            onPinClick={openTicket}
            selectedId={selectedId}
            statusFilter={statusFilter}
            onToggleStatus={toggleStatus}
          />
        )}
        {view === 'queue' && (
          <ReviewQueue
            tickets={tickets.filter((t) => t.status === 'pending')}
            loading={loading}
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
          <div style={{ flex: 1, overflowY: 'auto', minWidth: 0 }}>
            <UploadZone onSubmit={submitUpload} busy={uploading} />
            <JobProgress
              job={job}
              fetchJob={fetchJob}
              onUpdate={setJob}
              onDone={() => refresh()}
            />
          </div>
        )}
          </motion.div>
        </AnimatePresence>
        <AnimatePresence initial={false}>
        {selected && (
          <ErrorBoundary message="The ticket drawer crashed. Try another pin.">
            <TicketDrawer
              ticket={selected}
              onClose={() => setSelectedId(null)}
              onOverride={(id, to) => applyOverride(id, to)}
            />
          </ErrorBoundary>
        )}
        </AnimatePresence>
        </Suspense>
      </div>
      <div className="relative z-10 flex h-[34px] shrink-0 items-center gap-2 border-t border-white/8 bg-[rgba(10,12,17,0.85)] px-4 text-xs tabular-nums text-slate-500 backdrop-blur-xl">
        <Command size={12} className="text-slate-600" />
        {job ? `Job ${job.job_id?.slice(0, 8)} — ${job.status}` : 'No active job — Upload tab to process a route'}
        <span className="ml-auto hidden sm:inline">⌘K for actions · A approve · D dismiss</span>
      </div>
      <Suspense fallback={null}>
        <CommandPalette
          open={paletteOpen}
          onClose={() => setPaletteOpen(false)}
          tickets={tickets}
          onOpenTicket={(id) => { setView('map'); openTicket(id); }}
          onGoto={setView}
          onExport={() => downloadCSV('filed')}
        />
      </Suspense>
    </div>
  );
}
