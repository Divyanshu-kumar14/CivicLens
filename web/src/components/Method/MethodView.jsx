import { Camera, ScanEye, Satellite, TicketCheck } from 'lucide-react';
import { PipelineBeam } from '../ui/beam.jsx';
import { Card } from '../ui/card.jsx';

// Method view: how the system works, in measured numbers — the credibility
// panel for judges. Bench figures are VPS-measured (Oct 2026, docs/PERF.md);
// the dedup row is live from this session's stats.
function Row({ k, v, sub }) {
  return (
    <div className="border-b border-white/5 py-2.5 last:border-0">
      <div className="flex items-baseline gap-3">
        <span className="text-[13px] text-slate-400">{k}</span>
        <span className="ml-auto text-right font-display text-[15px] font-bold tabular-nums text-slate-50">{v}</span>
      </div>
      {sub && <div className="mt-0.5 text-[11px] text-slate-500">{sub}</div>}
    </div>
  );
}

export default function MethodView({ stats }) {
  const raw = stats?.raw ?? 0;
  const tickets = stats?.tickets ?? 0;
  const cut = raw > 0 ? Math.round(100 * (1 - tickets / raw)) : 0;
  return (
    <div className="min-w-0 flex-1 space-y-3 overflow-y-auto p-3.5">
      <Card className="p-4">
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">
          Perceive → decide → act
        </div>
        <PipelineBeam
          steps={[
            { icon: <Camera size={17} />, label: 'Scout', sub: '.mp4 + GPS', accent: '#3ae2ff' },
            { icon: <ScanEye size={17} />, label: 'Vision', sub: 'OpenCV+YOLO', accent: '#ffb020' },
            { icon: <Satellite size={17} />, label: 'Triage', sub: 'dedup+score', accent: '#a78bfa' },
            { icon: <TicketCheck size={17} />, label: 'Filed', sub: 'export CSV', accent: '#34d399' },
          ]}
        />
        <p className="mt-1 text-xs leading-relaxed text-slate-400">
          Every transition is trace-logged with actor, reasons, and signals —
          open any ticket drawer and read its Trace. Nothing is a black box.
        </p>
      </Card>
      <Card className="p-4">
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">
          Measured, not claimed
        </div>
        <Row k="Classical detect" v="90 fps" sub="stock OpenCV, ARM VPS bench" />
        <Row k="YOLOv8n" v="356 ms/frame" sub="measured on ARM; demo box runs classical-only" />
        <Row k="Dedup this session" v={`${raw} → ${tickets} (${cut}% cut)`} sub="live raw detections collapsed into tickets" />
        <p className="mt-2 text-[11px] text-slate-500">Full ledger: docs/PERF.md in the repo.</p>
      </Card>
      <Card className="p-4">
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">
          Scoring — open weights
        </div>
        <Row k="Damage area" v="×50%" />
        <Row k="Sightings" v="×25%" />
        <Row k="Bus route" v="×15%" />
        <Row k="Center lane" v="×10%" />
        <Row k="Thresholds" v="file ≥70 · review 40–69" />
        <p className="mt-2 text-[11px] text-slate-500">
          Demo-box worker: classical-only (fits 2GB), GPS-proximity dedup, no
          privacy blur. Full stack runs where GPUs live.
        </p>
      </Card>
    </div>
  );
}
