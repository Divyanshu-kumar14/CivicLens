import { cva } from 'class-variance-authority';
import { cn } from '../../lib/utils.js';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold tabular-nums transition-colors',
  {
    variants: {
      variant: {
        filed: 'border-[rgba(255,82,82,0.4)] bg-[rgba(255,82,82,0.12)] text-[#ff9a9a]',
        review: 'border-[rgba(255,176,32,0.4)] bg-[rgba(255,176,32,0.12)] text-[#ffcf7a]',
        dismissed: 'border-white/10 bg-white/5 text-slate-400',
        live: 'border-[rgba(52,211,153,0.4)] bg-[rgba(52,211,153,0.1)] text-emerald-300',
        demo: 'border-[rgba(255,176,32,0.4)] bg-[rgba(255,176,32,0.1)] text-amber-300',
        accent: 'border-[rgba(58,226,255,0.38)] bg-[rgba(58,226,255,0.1)] text-cyan-200',
        muted: 'border-white/10 bg-white/5 text-slate-300',
      },
    },
    defaultVariants: { variant: 'muted' },
  },
);

export function Badge({ className, variant, ...props }) {
  return <span data-slot="badge" className={cn(badgeVariants({ variant }), className)} {...props} />;
}
export { badgeVariants };
