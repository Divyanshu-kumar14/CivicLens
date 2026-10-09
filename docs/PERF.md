# Performance Ledger (Phase 1–2 polish, 2026-10-09)

Skill: `performance-optimization` — measure → identify → fix → verify → guard.
Baselines on this box (x86_64, 16 cores, cv2 5.0.0). Best-of-3, same command
before/after. Kept AND reverted attempts are both logged so dead ideas stay dead.

## Baselines (no change)

| Area | Measurement |
|---|---|
| cluster n=400 (steady) | 78ms/job |
| interpolate_gps 120 calls, 601-pt track | 4ms total |
| classical full-frame | 1.6ms/frame |
| blur (face+plate Haar) per crop | 1.7ms |
| ORB embed per crop (160×120) | 11.5ms |
| web initial bundle | 447.05KB (141.54KB gzip) |

## Kept

| Idea | Baseline → Result | Why kept |
|---|---|---|
| Vectorize dedup distance matrix (`agent/services/cluster.py`) | n=400: 78ms → 26ms; n=1000: ~500ms est → 95ms | 3× measured + linear-ish scaling to large jobs; equivalence proofed on 2000 pairs |
| Cap ORB input at 128px (`vision/embedder.py`) | 320×240: 11.5ms → 1.8ms/crop, unit norm intact | 6×, identical similarity behavior; 64px rejected (zero vectors) |
| Lazy-split drawer/queue/upload (`web/src/App.jsx`) | initial 447.05KB → 439.82KB (gzip 141.54 → 139.29KB) | Small but deterministic; structure pays off as views grow |

## Dropped / reverted (do not re-run without new evidence)

| Idea | Baseline → Result | Verdict | Why |
|---|---|---|---|
| Optimize `interpolate_gps` (pre-sorted index) | 4ms / 120 calls | dropped | Not a bottleneck; change would add API surface for nothing |
| Optimize classical full-frame pass | 1.6ms/frame | dropped | ~1% of frame budget; YOLO will dominate anyway |
| Optimize blur Haar path | 1.7ms/crop | dropped | Same order as noise next to ORB |
| Hoist sklearn import to module top | ~1.1s cold once per worker | dropped | One-time per long-lived process; moving it doesn't reduce total |
| ORB cap at 64px | 0.25ms/crop BUT zero vectors | reverted | Destroys recall; 128px is the floor until re-measured |
| Python O(n²) pair loop at demo scale | 78ms/job | superseded | Replaced by the vectorized matrix above, not tuned in place |

## Guards

- `make bench` covers vision throughput; re-run after any detector/embed change.
- Bundle size: compare `vite build` asset lines before/after UI changes.
- Correctness gates the metric: full suite green required (`55 passed, 2 skipped`
  at time of writing); any perf change that breaks a test is reverted.
