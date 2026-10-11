import { cn } from '../../lib/utils.js';

export function Skeleton({ className, ...props }) {
  return (
    <div
      data-slot="skeleton"
      className={cn('relative overflow-hidden rounded-md bg-[#161c26]', className)}
      {...props}
    >
      <div className="absolute inset-0 -translate-x-full animate-[skel-sweep_1.3s_ease_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
    </div>
  );
}

export function Input({ className, ...props }) {
  return (
    <input
      data-slot="input"
      className={cn(
        'h-9 rounded-lg border border-white/10 bg-[rgba(10,13,18,0.9)] px-3 text-[13px] text-slate-100',
        'placeholder:text-slate-500 outline-none focus:border-cyan-300/60 focus:ring-2 focus:ring-cyan-300/20',
        className,
      )}
      {...props}
    />
  );
}

export function Separator({ className, ...props }) {
  return <div data-slot="separator" className={cn('h-px bg-white/8', className)} {...props} />;
}

export function Progress({ value = 0, className, barClassName, ...props }) {
  return (
    <div data-slot="progress" className={cn('h-2 overflow-hidden rounded-full bg-[#161c26]', className)} {...props}>
      <div
        className={cn('h-full rounded-full bg-emerald-400 transition-transform duration-500 origin-left', barClassName)}
        style={{ transform: `scaleX(${Math.min(1, Math.max(0, value))})` }}
      />
    </div>
  );
}
