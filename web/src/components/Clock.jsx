import { useEffect, useState } from 'react';

// Own-component clock: App previously owned this interval, re-rendering the
// whole tree (map pins included) every second. Isolating state here means the
// map only re-renders when its own props change.
export default function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <span className="cl-clock" aria-label="Current UTC time">
      {now.toISOString().slice(11, 19)} UTC
    </span>
  );
}
