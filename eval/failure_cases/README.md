# Failure Cases (Task 2.4.5)

Honest log: what breaks, what the system does, proposed fix. Entries marked
**measured** came from real runs in Phase 2.4; **expected** need night/rain
footage (human filming step, Task 1.6.1).

## 1. Night / low-light detection drops — EXPECTED
- What: Canny thresholds (50/150) tuned for daylight; dark frames yield
  near-zero edges, YOLO conf collapses.
- System response: fewer/no detections (silent miss, worst kind).
- Fix: condition-specific thresholds (gain-normalized preprocessing), report
  night split separately in eval (PRD target split exists for this reason).

## 2. Rain glare false positives — EXPECTED
- What: wet reflections create strong edges; classical path fires.
- System response: low-conf classical-only boxes mostly die at the 0.45 gate
  or land in `pending` review — noisy queue, not false filings.
- Fix: polarization-agnostic check (glare regions are bright: reject boxes
  with mean intensity > 200), rain split in eval.

## 3. Speed breaker misidentified as pothole — EXPECTED
- What: breakers pass the aspect filter (0.3–3.0) and area gate.
- System response: likely `pending` (single pass, off-center) — human rejects.
- Fix: YOLO class training on breakers as explicit negatives; geometry cue
  (breakers span full lane width, potholes don't).

## 4. Tar patch false positive — EXPECTED
- What: dark repair patches match pothole color; classical shape filter passes.
- System response: ORB texture differs from true holes, so dedup won't merge
  it with real clusters — isolated ticket, reviewer dismisses once.
- Fix: texture-aware scorer signal (edge density inside box vs border).

## 5. GPS drift causing split clusters — MEASURED (eval_dedup, 2026-10-09)
- What: one of 8 synthetic holes split into 2 clusters (recall 0.88, precision
  1.00) — an embedding outlier fell below cos_thresh despite being within
  geo_eps_m.
- System response: two tickets for one hole (duplicate work, visible in queue).
- Fix: track-level smoothing before clustering (interpolate_gps already
  exists — apply to sightings), or second-pass merge of nearby same-shift
  tickets. Repro: `python eval/eval_dedup.py`.
