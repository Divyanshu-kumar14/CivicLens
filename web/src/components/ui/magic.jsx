import { useEffect, useRef, useState } from 'react';
import { cn } from '../../lib/utils.js';

// NumberTicker (MagicUI-style, owned): exponential ease-out count to value.
// Respects reduced-motion. Tabular nums so layout never jitters.
export function NumberTicker({ value, decimals = 0, duration = 700, className, ...props }) {
  const num = Number(value);
  const numeric = value !== undefined && value !== null && value !== '—' && !Number.isNaN(num);
  const [display, setDisplay] = useState(numeric ? num : 0);
  const fromRef = useRef(numeric ? num : 0);
  const firstRef = useRef(true);

  useEffect(() => {
    if (!numeric) return;
    if (firstRef.current) {
      // First paint: count up from 0 for the hero feel.
      firstRef.current = false;
      fromRef.current = 0;
    }
    const from = fromRef.current;
    if (from === num) return;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      fromRef.current = num;
      setDisplay(num);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(2, -10 * p);
      setDisplay(from + (num - from) * (p === 1 ? 1 : eased));
      if (p < 1) raf = requestAnimationFrame(tick);
      else fromRef.current = num;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [num, numeric, duration]);

  if (!numeric) return <span className={cn('tabular-nums', className)} {...props}>{String(value ?? '—')}</span>;
  const text = decimals > 0 ? display.toFixed(decimals) : String(Math.round(display));
  return <span className={cn('tabular-nums', className)} {...props}>{text}</span>;
}

// ShimmerButton (MagicUI-style): premium CTA with sweeping highlight.
// Use for the single primary action per view — never for rows.
export function ShimmerButton({ className, children, ...props }) {
  return (
    <button
      className={cn(
        'group relative inline-flex h-9 items-center justify-center gap-2 overflow-hidden rounded-xl px-4',
        'bg-emerald-400 text-[13px] font-bold text-[#05241b]',
        'shadow-[0_2px_16px_rgba(52,211,153,0.35)] transition-all duration-150 hover:brightness-105 active:scale-[0.97]',
        'disabled:pointer-events-none disabled:opacity-40 [&_svg]:size-4',
        className,
      )}
      {...props}
    >
      <span className="relative z-10 inline-flex items-center gap-2">{children}</span>
      <span
        aria-hidden
        className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/40 to-transparent transition-transform duration-700 group-hover:translate-x-full"
      />
    </button>
  );
}
