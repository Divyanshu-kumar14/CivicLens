import { useEffect, useState } from 'react';

// Reverse-geocode via Nominatim (free, no key) with a persistent cache and
// polite pacing. Policy: max ~1 req/s, results cached indefinitely in
// localStorage, fail-open to null (callers fall back to coordinates).
const LS_KEY = 'cl-geocode-v1';
const mem = new Map();
try {
  const saved = JSON.parse(localStorage.getItem(LS_KEY) || '{}');
  for (const [k, v] of Object.entries(saved)) mem.set(k, v);
} catch { /* private mode etc — memory cache still works */ }

const listeners = new Set();
function notify() {
  listeners.forEach((fn) => { try { fn(); } catch { /* ignore */ } });
}
export function subscribeGeocode(fn) {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}

function persist() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(Object.fromEntries(mem)));
  } catch { /* ignore */ }
}

export function keyFor(lat, lon) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  return `${lat.toFixed(4)},${lon.toFixed(4)}`;
}

export function cachedAddress(lat, lon) {
  const k = keyFor(lat, lon);
  return (k && mem.get(k)) || null;
}

function shortAddr(j) {
  const a = j.address || {};
  const road = a.road || a.pedestrian || a.cycleway || '';
  const area = a.suburb || a.neighbourhood || a.quarter || a.city_district || '';
  const bits = [road, area].filter(Boolean);
  if (bits.length) return bits.join(', ');
  return (j.display_name || '').split(',').slice(0, 2).join(',').trim() || null;
}

// Paced prefetch queue — one request per ~1.1s, duplicates collapsed.
const pending = new Map();
let tail = Promise.resolve();

export function prefetchAddress(lat, lon) {
  const k = keyFor(lat, lon);
  if (!k || mem.has(k) || pending.has(k)) return;
  pending.set(k, true);
  tail = tail.then(async () => {
    try {
      const r = await fetch(
        `https://nominatim.openstreetmap.org/reverse?lat=${lat.toFixed(5)}&lon=${lon.toFixed(5)}&format=jsonv2&zoom=17&accept-language=en`,
      );
      if (r.ok) {
        const s = shortAddr(await r.json());
        if (s) {
          mem.set(k, s);
          persist();
          notify();
        }
      }
    } catch { /* offline — callers show coordinates */ }
    finally {
      pending.delete(k);
      await new Promise((r) => setTimeout(r, 1100));
    }
  });
}

// Hook: returns {ticket_id: address|null} and re-renders as lookups land.
export function useAddresses(tickets) {
  const [, setV] = useState(0);
  useEffect(() => subscribeGeocode(() => setV((x) => x + 1)), []);
  useEffect(() => {
    (tickets || []).forEach((t) => prefetchAddress(t.centroid?.[0], t.centroid?.[1]));
  }, [tickets]);
  const out = {};
  (tickets || []).forEach((t) => {
    out[t.ticket_id] = cachedAddress(t.centroid?.[0], t.centroid?.[1]);
  });
  return out;
}
