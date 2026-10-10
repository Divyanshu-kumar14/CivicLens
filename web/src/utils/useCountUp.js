import { useEffect, useRef, useState } from 'react';

// Animated counter: eases from previous value to `value` on change.
// Respects prefers-reduced-motion (jumps immediately).
export default function useCountUp(value, duration = 600) {
  const [display, setDisplay] = useState(value);
  const fromRef = useRef(value);

  useEffect(() => {
    const from = fromRef.current;
    if (from === value) return;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      fromRef.current = value;
      setDisplay(value);
      return;
    }
    let raf = 0;
    const t0 = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(2, -10 * p); // exponential ease-out
      setDisplay(from + (value - from) * (p === 1 ? 1 : eased));
      if (p < 1) raf = requestAnimationFrame(tick);
      else fromRef.current = value;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);

  return display;
}
