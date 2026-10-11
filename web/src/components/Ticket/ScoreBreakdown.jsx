import { prettySignalKey } from '../../utils/labels.js';

// Why-this-score: severity as stacked signal contributions. Weights mirror
// SeverityScorer defaults (w_area .50, w_repeat .25, w_route .15, w_lane .10).
// No total line: seed tickets predate scoring so their rows are illustrative,
// while live-scored tickets sum to their severity exactly.
const WEIGHTS = [
  ['area_norm', 0.5],
  ['repeat', 0.25],
  ['bus_route_w', 0.15],
  ['center_lane', 0.1],
];

export default function ScoreBreakdown({ signals = {}, severity }) {
  const maxPts = 50; // largest single contribution (100 × 0.5)
  return (
    <div>
      <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">
        Why this score
      </div>
      <div className="space-y-2">
        {WEIGHTS.map(([key, w]) => {
          const v = Number(signals[key]);
          const val = Number.isFinite(v) ? v : 0;
          const pts = val * w;
          return (
            <div key={key}>
              <div className="mb-1 flex items-baseline gap-2 text-xs">
                <span className="text-slate-400">
                  {prettySignalKey(key)} <span className="text-slate-600">×{Math.round(w * 100)}%</span>
                </span>
                <span className="ml-auto font-display font-bold tabular-nums text-slate-100">+{Math.round(pts)}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-white/8">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-emerald-400 transition-transform duration-500 origin-left"
                  style={{ transform: `scaleX(${Math.min(1, pts / maxPts)})` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-2 text-[11px] tabular-nums text-slate-500">
        Severity {severity} · weights 50/25/15/10 · file ≥70 · review 40–69
      </div>
    </div>
  );
}
