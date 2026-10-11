import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowRight, Download, Map as MapIcon, Search, UploadCloud, ListChecks } from 'lucide-react';

// Action search bar (Kokonut-style, fully owned): Cmd+K fuzzy finder over
// tickets + view actions + exports. No black box — ranking is a 20-line
// substring scorer below. Lazy-mounted by App so it costs 0KB until opened.
function score(q, text) {
  // Subsequence scorer: +2 per ordered char hit, +4 for prefix, -len penalty.
  q = q.toLowerCase();
  text = text.toLowerCase();
  if (!q) return 0;
  if (text.startsWith(q)) return 100 - text.length;
  let qi = 0;
  let hits = 0;
  for (let i = 0; i < text.length && qi < q.length; i++) {
    if (text[i] === q[qi]) { hits++; qi++; }
  }
  if (qi < q.length) return -1;
  return hits * 2 - text.length * 0.1;
}

export default function CommandPalette({ open, onClose, tickets, onOpenTicket, onGoto, onExport }) {
  const [q, setQ] = useState('');
  const [idx, setIdx] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) {
      setQ('');
      setIdx(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open ]);

  const actions = useMemo(() => {
    const ticketHits = (tickets || []).slice(0, 400).map((t) => ({
      kind: 'ticket',
      id: t.ticket_id,
      title: `${t.ticket_id} · sev ${t.severity} · ${t.status}`,
      sub: `${t.centroid?.[0]?.toFixed(4)}, ${t.centroid?.[1]?.toFixed(4)}`,
      s: score(q, `${t.ticket_id} ${t.status} ${t.severity}`),
      run: () => onOpenTicket(t.ticket_id),
    })).filter((a) => a.s >= 0);

    const views = [
      { kind: 'view', id: 'map', title: 'Go to Map', icon: <MapIcon size={15} />, s: score(q, 'go map pins'), run: () => onGoto('map') },
      { kind: 'view', id: 'queue', title: 'Go to Review queue', icon: <ListChecks size={15} />, s: score(q, 'go review queue approve'), run: () => onGoto('queue') },
      { kind: 'view', id: 'upload', title: 'Go to Upload', icon: <UploadCloud size={15} />, s: score(q, 'go upload video job'), run: () => onGoto('upload') },
      { kind: 'view', id: 'export', title: 'Export filed CSV', icon: <Download size={15} />, s: score(q, 'export csv download filed'), run: onExport },
    ].filter((a) => a.s >= 0 || !q);

    const merged = [...views.filter((v) => (v.s ?? 0) > 0 || !q), ...ticketHits]
      .sort((a, b) => (b.s ?? 0) - (a.s ?? 0))
      .slice(0, 9);
    return merged;
  }, [q, tickets, onOpenTicket, onGoto, onExport]);

  useEffect(() => setIdx(0), [q]);

  if (!open) return null;

  const onKey = (e) => {
    if (e.key === 'Escape') onClose();
    else if (e.key === 'ArrowDown') { e.preventDefault(); setIdx((i) => Math.min(actions.length - 1, i + 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setIdx((i) => Math.max(0, i - 1)); }
    else if (e.key === 'Enter') { actions[idx]?.run(); onClose(); }
  };

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[2000] flex items-start justify-center bg-black/60 p-4 pt-[14vh] backdrop-blur-sm"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          role="dialog"
          aria-label="Action search"
          className="w-full max-w-lg overflow-hidden rounded-2xl border border-white/12 bg-[rgba(13,17,24,0.96)] shadow-[0_24px_80px_rgba(0,0,0,0.6)]"
          initial={{ y: 12, scale: 0.98, opacity: 0 }}
          animate={{ y: 0, scale: 1, opacity: 1 }}
          exit={{ y: 8, scale: 0.98, opacity: 0 }}
          transition={{ type: 'spring', stiffness: 500, damping: 36 }}
          onClick={(e) => e.stopPropagation()}
          onKeyDown={onKey}
        >
          {/* Search header: the container owns the focus ring (single cyan
              hairline), the input itself is chrome-free so there is never a
              double nested box. */}
          <div className="flex items-center gap-2 border-b border-white/8 px-4 transition-colors focus-within:border-[rgba(58,226,255,0.35)] focus-within:bg-cyan-300/[0.03]">
            <Search size={16} className="shrink-0 text-slate-500" />
            <input
              ref={inputRef}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search tickets, jump to views, export…"
              className="h-12 w-full border-0 bg-transparent text-sm text-slate-100 shadow-none outline-none placeholder:text-slate-500 focus:outline-none focus:ring-0 focus-visible:outline-none"
            />
            <kbd className="shrink-0 rounded-md border border-white/10 bg-white/5 px-1.5 py-0.5 text-[10px] font-semibold text-slate-400">esc</kbd>
          </div>
          <div className="max-h-72 overflow-y-auto p-1.5">
            {actions.length === 0 && <div className="px-3 py-6 text-center text-[13px] text-slate-500">No matches — try a ticket id or “export”.</div>}
            {actions.map((a, i) => (
              <button
                key={`${a.kind}-${a.id}`}
                onMouseEnter={() => setIdx(i)}
                onClick={() => { a.run(); onClose(); }}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors ${i === idx ? 'bg-cyan-300/[0.09] text-white shadow-[inset_0_0_0_1px_rgba(58,226,255,0.22)]' : 'text-slate-300'}`}
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-slate-300">
                  {a.icon || <Search size={14} />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13px] font-semibold">{a.title}</span>
                  {a.sub && <span className="block truncate text-[11px] tabular-nums text-slate-500">{a.sub}</span>}
                </span>
                <ArrowRight size={14} className={i === idx ? 'text-cyan-200' : 'text-slate-600'} />
              </button>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
