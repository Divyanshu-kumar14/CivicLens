import { cn } from '../../lib/utils.js';

// Liquid-glass Card (Kokonut-style, fully owned): translucent tile + inner
// top highlight + hairline border. No black box — tweak gradient/blur here.
export function Card({ className, ...props }) {
  return (
    <div
      data-slot="card"
      className={cn(
        'relative rounded-2xl border border-white/10 bg-[rgba(15,18,24,0.72)] backdrop-blur-xl',
        'shadow-[0_8px_32px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)]',
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }) {
  return <div data-slot="card-header" className={cn('flex flex-col gap-1 p-4 pb-2', className)} {...props} />;
}

export function CardTitle({ className, ...props }) {
  return (
    <h3 data-slot="card-title" className={cn('font-display text-[15px] font-bold tracking-tight text-slate-100', className)} {...props} />
  );
}

export function CardDescription({ className, ...props }) {
  return <p data-slot="card-description" className={cn('text-xs text-slate-400', className)} {...props} />;
}

export function CardContent({ className, ...props }) {
  return <div data-slot="card-content" className={cn('p-4 pt-2', className)} {...props} />;
}
