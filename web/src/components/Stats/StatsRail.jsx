import { Activity, CircleDollarSign, Layers, Route, TicketCheck } from 'lucide-react';
import { Card } from '../ui/card.jsx';
import { NumberTicker } from '../ui/magic.jsx';

// Liquid-glass stat tile (Kokonut-style): icon in tinted well + ticker value.
// Behavior unchanged — same stats object, same titles, just premium skin.
function StatTile({ icon, label, value, decimals = 0, title, accent = '#3ae2ff' }) {
  return (
    <Card className="p-3.5" title={title}>
      <div className="mb-2 flex items-center gap-2">
        <span
          className="flex h-7 w-7 items-center justify-center rounded-lg border"
          style={{ borderColor: `${accent}44`, background: `${accent}14`, color: accent }}
        >
          {icon}
        </span>
        <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">{label}</span>
      </div>
      <div className="font-display text-[28px] font-bold leading-none tabular-nums text-slate-50">
        <NumberTicker value={value} decimals={decimals} />
      </div>
    </Card>
  );
}

// Severity mix chart (Bklit-style: styled, not plotted): animated segmented
// bar + per-status rows with counts. No chart lib — 30 lines we fully own.
function SeverityMix({ filed = 0, review = 0, dismissed = 0 }) {
  const total = filed + review + dismissed || 1;
  const rows = [
    ['Filed', filed, '#ff5252'],
    ['Review', review, '#ffb020'],
    ['Dismissed', dismissed, '#6b7280'],
  ];
  return (
    <Card className="p-3.5">
      <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">Ticket mix</div>
      <div className="mb-3 flex h-2 overflow-hidden rounded-full bg-[#161c26]" title="Filed / Review / Dismissed">
        {rows.map(([label, v, color]) => (
          <span
            key={label}
            title={`${label}: ${v}`}
            className="block h-full transition-all duration-500"
            style={{ width: `${(v / total) * 100}%`, background: color }}
          />
        ))}
      </div>
      <div className="space-y-1.5">
        {rows.map(([label, v, color]) => (
          <div key={label} className="flex items-center gap-2 text-xs">
            <span className="h-2 w-2 rounded-full" style={{ background: color, boxShadow: `0 0 6px ${color}` }} />
            <span className="text-slate-400">{label}</span>
            <span className="ml-auto font-bold tabular-nums text-slate-100">{v}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function StatsRail({ stats }) {
  return (
    <aside className="flex w-60 shrink-0 flex-col gap-2.5 overflow-y-auto border-r border-white/8 bg-[rgba(15,18,24,0.72)] p-3.5 backdrop-blur-xl max-md:w-full max-md:flex-row max-md:overflow-x-auto max-md:border-b max-md:border-r-0 [&>*]:max-md:min-w-[160px]" aria-label="Processing statistics">
      <StatTile icon={<Route size={15} />} label="Coverage km" value={stats.km} decimals={1} title="Diagonal span of ticket locations" accent="#3ae2ff" />
      <StatTile icon={<Layers size={15} />} label="Raw detections" value={stats.raw} accent="#a7b0bd" />
      <StatTile icon={<TicketCheck size={15} />} label="Tickets" value={stats.tickets} accent="#34d399" />
      <SeverityMix filed={stats.filed} review={stats.review} dismissed={stats.dismissed} />
      <Card className="p-3.5" title={stats.costHint}>
        <div className="mb-1 flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-emerald-400/30 bg-emerald-400/10 text-emerald-300">
            <CircleDollarSign size={15} />
          </span>
          <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">Est. $/1000km</span>
        </div>
        <div className="font-display text-[22px] font-bold tabular-nums text-slate-50">{stats.costPer1000km}</div>
      </Card>
      {stats.dedup && (
        <Card className="border-cyan-300/30 bg-cyan-300/8 p-3 text-[13px] font-semibold tabular-nums text-cyan-100" title="Raw detections collapsed into tickets">
          <span className="mr-1.5 inline-flex items-center gap-1 text-cyan-200"><Activity size={13} /></span>
          {stats.dedup.from} → {stats.dedup.to} tickets
        </Card>
      )}
    </aside>
  );
}
