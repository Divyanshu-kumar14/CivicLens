import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// shadcn-style cn(): merge Tailwind classes intelligently so component
// overrides never fight base variants.
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
