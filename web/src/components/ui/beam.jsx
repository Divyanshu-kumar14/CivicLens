// AnimatedBeam (MagicUI Animated Beam, owned one-liner version): an SVG
// connection with a travelling pulse. Used for the Scout→Vision→Triage→Filed
// pipeline strip — the integration-diagram "wow" without hand-coding WebGL.
export function PipelineBeam({ steps }) {
  // steps: [{ icon, label, sub, accent }]
  return (
    <div className="relative flex items-stretch justify-between gap-1 px-1 py-2" aria-label="Pipeline">
      <svg aria-hidden className="absolute left-6 right-6 top-1/2 h-px w-[calc(100%-3rem)] -translate-y-6 text-white/15" preserveAspectRatio="none">
        <line x1="0" y1="0.5" x2="100%" y2="0.5" stroke="currentColor" strokeWidth="1" />
      </svg>
      <svg aria-hidden className="absolute left-6 right-6 top-1/2 h-px w-[calc(100%-3rem)] -translate-y-6">
        <line x1="0" y1="0.5" x2="100%" y2="0.5" stroke="url(#beam-grad)" strokeWidth="1.5" strokeDasharray="42 260" className="beam-dash" />
        <defs>
          <linearGradient id="beam-grad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#3ae2ff" stopOpacity="0" />
            <stop offset="50%" stopColor="#3ae2ff" />
            <stop offset="100%" stopColor="#34d399" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
      {steps.map((s) => (
        <div key={s.label} className="relative z-10 flex w-20 flex-col items-center gap-1.5 text-center">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-2xl border backdrop-blur-xl"
            style={{ borderColor: `${s.accent}55`, background: 'rgba(12,15,21,0.9)', boxShadow: `0 0 18px ${s.accent}33, inset 0 1px 0 rgba(255,255,255,0.1)` }}
          >
            <span style={{ color: s.accent }}>{s.icon}</span>
          </div>
          <div className="text-[11px] font-bold text-slate-100">{s.label}</div>
          <div className="text-[10px] tabular-nums text-slate-500">{s.sub}</div>
        </div>
      ))}
      <style>{`.beam-dash { animation: beam-travel 2.6s linear infinite; } @keyframes beam-travel { to { stroke-dashoffset: -302; } } @media (prefers-reduced-motion: reduce) { .beam-dash { animation: none; } }`}</style>
    </div>
  );
}
