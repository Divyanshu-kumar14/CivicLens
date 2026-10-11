import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva } from 'class-variance-authority';
import { cn } from '../../lib/utils.js';

// shadcn-style Button (new-york, owned in-repo): variants via cva so callers
// compose intent (file/dismiss/ghost/outline) without re-declaring CSS.
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-[13px] font-semibold transition-all duration-150 outline-none cursor-pointer disabled:pointer-events-none disabled:opacity-40 active:scale-[0.97] focus-visible:ring-2 focus-visible:ring-cyan-300/70 [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default: 'bg-cyan-300 text-[#061014] shadow-[0_2px_16px_rgba(58,226,255,0.35)] hover:brightness-110',
        success: 'bg-emerald-400 text-[#05241b] shadow-[0_2px_12px_rgba(52,211,153,0.28)] hover:brightness-105',
        dangerOutline: 'bg-transparent text-[#ff7a7a] border border-[rgba(255,82,82,0.55)] hover:bg-[rgba(255,82,82,0.12)]',
        ghost: 'bg-[rgba(24,30,40,0.72)] text-slate-100 border border-white/10 hover:border-white/20',
        outline: 'bg-transparent text-slate-200 border border-white/12 hover:border-white/25 hover:bg-white/5',
        link: 'text-cyan-200 underline-offset-4 hover:underline h-auto px-0',
      },
      size: {
        default: 'h-9 px-4',
        sm: 'h-8 px-3 text-xs rounded-lg',
        lg: 'h-11 px-6 text-sm rounded-xl',
        icon: 'h-9 w-9 p-0',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
);

function Button({ className, variant, size, asChild = false, ...props }) {
  const Comp = asChild ? Slot : 'button';
  return <Comp data-slot="button" className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}

export { Button, buttonVariants };
