import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Check, Download, X } from 'lucide-react';
import { Badge } from '../ui/badge.jsx';
import { Button } from '../ui/button.jsx';
import { Card } from '../ui/card.jsx';
import { Skeleton } from '../ui/primitives.jsx';

// Amber (pending) ticket table: sorted by severity desc, bulk select,
// A/D/1-3 keyboard shortcuts, row click opens the drawer.
// Premium skin: glass card, sticky micro-label header, severity pill + bar.
function sevColor(s) {
  if (s >= 70) return '#ff5252';
  if (s >= 40) return '#ffb020';
  return '#34d399';
}

export default function ReviewQueue({
  tickets,
  loading = false,
  selectedIds,
  onToggleSelect,
  onSelectAll,
  onApprove,
  onDismiss,
  onSetSeverity,
  onExportSelected,
  onRowClick,
}) {
  // O(n log n) sort memoized: without this, every parent render (poll ticks,
  // selection, clock) re-sorted the table for an identical ticket array.
  const rows = useMemo(
    () => [...tickets].sort((a, b) => (b.severity || 0) - (a.severity || 0)),
    [tickets],
  );

  const onKey = (e) => {
    if (e.key === 'a' || e.key === 'A') onApprove();
    else if (e.key === 'd' || e.key === 'D') onDismiss();
    else if (e.key === '1') onSetSeverity('low');
    else if (e.key === '2') onSetSeverity('med');
    else if (e.key === '3') onSetSeverity('high');
  };

  return (
    <div className="min-w-0 flex-1 overflow-y-auto p-3" tabIndex={0} onKeyDown={onKey} aria-label="Review queue">
      {/* Bulk action bar: count + approve/dismiss/export. Same handlers. */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge variant="review" className="px-3 py-1.5 text-xs">
          {selectedIds.size > 0 ? `${selectedIds.size} selected` : `${rows.length} awaiting review`}
        </Badge>
        <div className="ml-auto flex gap-2">
          <Button variant="success" size="sm" onClick={onApprove} disabled={selectedIds.size === 0}>
            <Check /> Approve
          </Button>
          <Button variant="dangerOutline" size="sm" onClick={onDismiss} disabled={selectedIds.size === 0}>
            <X /> Dismiss
          </Button>
          <Button variant="ghost" size="sm" onClick={onExportSelected}>
            <Download /> Export
          </Button>
        </div>
      </div>
      {loading && rows.length === 0 ? (
        <Card className="space-y-2.5 p-4" role="status" aria-label="Loading tickets">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="flex gap-2.5">
              <Skeleton className="h-9 w-[18%]" />
              <Skeleton className="h-9 w-[34%]" />
              <Skeleton className="h-9 w-[22%]" />
            </div>
          ))}
        </Card>
      ) : (
      <Card className="overflow-hidden">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-white/8">
              <th className="w-10 px-3 py-2.5 text-left">
                <input
                  type="checkbox"
                  aria-label="Select all"
                  className="h-[15px] w-[15px] accent-cyan-300"
                  checked={selectedIds.size === rows.length && rows.length > 0}
                  onChange={onSelectAll}
                />
              </th>
              {['Severity', 'Type', 'Location', 'Repeat'].map((h) => (
                <th key={h} className="px-2.5 py-2.5 text-left text-[10px] font-semibold uppercase tracking-[0.09em] text-slate-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((t, i) => (
              <motion.tr
                key={t.ticket_id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.18, delay: Math.min(i, 12) * 0.02 }}
                onClick={() => onRowClick(t.ticket_id)}
                className="cursor-pointer border-b border-white/5 transition-colors last:border-0 hover:bg-white/[0.035]"
              >
                <td className="px-3 py-2.5" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    aria-label={`Select ${t.ticket_id}`}
                    className="h-[15px] w-[15px] accent-cyan-300"
                    checked={selectedIds.has(t.ticket_id)}
                    onChange={() => onToggleSelect(t.ticket_id)}
                  />
                </td>
                <td className="px-2.5 py-2.5">
                  <span className="flex min-w-36 items-center gap-2">
                    <span
                      className="font-display text-xs font-bold tabular-nums"
                      style={{ color: sevColor(t.severity) }}
                    >
                      {t.severity}
                    </span>
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/8">
                      <span
                        className="block h-full rounded-full transition-transform duration-500 origin-left"
                        style={{ transform: `scaleX(${Math.min(1, Math.max(0, t.severity ?? 0) / 100)})`, background: sevColor(t.severity) }}
                      />
                    </span>
                  </span>
                </td>
                <td className="px-2.5 py-2.5 text-slate-300">{t.hole_label || t.cls || 'pothole'}</td>
                <td className="px-2.5 py-2.5 tabular-nums text-slate-400">{t.centroid?.[0]?.toFixed(4)}, {t.centroid?.[1]?.toFixed(4)}</td>
                <td className="px-2.5 py-2.5 tabular-nums text-slate-300">×{t.repeat_count ?? 1}</td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </Card>
      )}
      {rows.length === 0 && !loading && (
        <Card className="mt-3 p-7 text-center text-[13px] text-slate-500">Queue empty — nothing awaiting review.</Card>
      )}
      <div className="mt-3 flex items-center gap-1.5 text-xs text-slate-500">
        Shortcuts:
        <kbd className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] font-semibold text-slate-200">A</kbd> approve
        <kbd className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] font-semibold text-slate-200">D</kbd> dismiss
        <kbd className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] font-semibold text-slate-200">1</kbd>
        <kbd className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] font-semibold text-slate-200">2</kbd>
        <kbd className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] font-semibold text-slate-200">3</kbd> severity
      </div>
    </div>
  );
}
