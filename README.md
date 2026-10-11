# CivicLens 🔍🕳️

> **Every garbage truck becomes a city inspector.**
> Cities fix potholes weeks faster without extra patrols — the truck that already drives every street files its own tickets, with photo proof.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%C2%B7%20OpenCV%20%C2%B7%20React-blue)](#tech-stack)
[![AWS](https://img.shields.io/badge/AWS-S3%20%C2%B7%20DynamoDB%20%C2%B7%20SQS-orange)](#real-aws-deploy)
[![Evaluated](https://img.shields.io/badge/eval-dedup%208.9%C3%97%20%C2%B7%20severity%20%CF%81%3D1.00-purple)](#-evaluation)

---

## 👀 What is this?

CivicLens turns dashcam / garbage-truck route video into **actionable road-repair tickets**:

1. 🎥 **See** — a vision pipeline watches route video, detects potholes/cracks (YOLOv8n + classical Canny fallback), blurs faces/plates, and embeds each crop.
2. 🧠 **Think** — an agentic service dedups repeat sightings of the same hole (DBSCAN over GPS + visual similarity), scores severity 0–100, and decides: **auto-file** 🟥, **human review** 🟨, or **dismiss** ⬜.
3. 🗺️ **Act** — road crews get a live map, a review queue, CSV exports, and HMAC-signed webhooks. Every decision carries a full **agent trace** — no black boxes.

```
S3 raw video → SQS jobs → vision worker (decode→detect→blur→embed)
    → DynamoDB detections + S3 crops → agent (cluster→score→file/queue)
    → DynamoDB tickets + traces → React map / queue → CSV + webhook work orders
```

📐 Full architecture: [`docs/arch_diagram.png`](docs/arch_diagram.png) · source [`docs/arch_diagram.mmd`](docs/arch_diagram.mmd) · deep-dive [`docs/report.md`](docs/report.md)

---

## ⚡ Quick start (5 minutes, no AWS needed)

> You need: **Docker + Docker Compose**, **Python 3.11+**, **Node 20+**, `make`.

```bash
# 1. Boot the full stack — API :8000 · web :3000 · localstack :4566 · DynamoDB :8100
docker compose up --build

# 2. Seed demo data (idempotent — safe to re-run)
make seed-demo

# 3. Open the map
open http://localhost:3000        # macOS
# xdg-open http://localhost:3000  # Linux
```

**What you should see:** 5 demo tickets on a dark Leaflet map (`t_hole01`…`t_hole05`), a review queue with sample items, and an upload tab. If the API is unreachable the UI falls back to **Demo mode** (amber badge, mock data) instead of a blank screen.

```bash
# Sanity checks
curl localhost:8000/health                 # {"status":"ok","service":"civiclens-agent"}
curl localhost:8000/tickets | head -c 400  # seeded tickets as JSON
```

---

## 🖥️ A tour of the app (what each screen does)

| View | What it's for | Try this |
|------|---------------|----------|
| 🗺️ **Map** | Every ticket as a pin, colored by severity. Click a pin → photo crop, severity breakdown, agent trace. | Click the reddest pin, expand *Why this score?* |
| 📋 **Queue** | Human review inbox (`pending` tickets). Bulk approve / dismiss, severity presets. | Select 2 rows → *Approve* → watch them turn `filed` |
| ⬆️ **Upload** | Drop a route video + optional GPS file → new processing job with live progress. | Upload any `.mp4` + `.csv` → follow the progress bar |
| 🔬 **Method** | Explains the pipeline + live cost/perf stats. Great for demos to non-engineers. | Press `⌘K` / `Ctrl+K` anywhere for the action palette |

> 📸 **Screenshots:** capture each view and drop them in `docs/screenshots/` as `map.png`, `queue.png`, `upload.png`, `method.png` — then link them in the table above. (No screenshots are committed yet; the map works headless in CI so we don't gate merges on images.)

---

## 🧩 How it works

### 1. Vision — `vision/` (OpenCV pipeline)

`video + GPS → geo-tagged detections with blurred crops + embeddings`

- **Ingest** (`ingest.py`) — validates + decodes video at 2 fps sampling.
- **GPS** (`gps.py`) — parses `.csv` / `.srt` tracks, interpolates position per frame (haversine math).
- **Detect** (`detector.py`) — YOLOv8n (`conf 0.25`, `NMS 0.5`, min-box 24px) **fused** with a classical Canny+contour fallback. Overlap boosts confidence `+0.1`; large classical-only regions enter at `0.45`; borderline YOLO hits get a focused ROI re-check.
- **Blur** (`blur.py`) — Haar face + plate cascades **before storage**, plus a plate edge-density fallback.
- **Embed** (`embedder.py`) — ORB-500 mean → 128-d unit vector (inputs capped at 128px: `11.5 → 1.8 ms/crop`, identical quality).

### 2. Agent — `agent/` (FastAPI triage service)

`detections → clusters → severity → filed / pending / dismissed`

- **Dedup** (`services/cluster.py`) — DBSCAN over a combined metric: same hole iff within `geo_eps_m` **and** embedding cosine ≥ `cos_thresh`. Measured **80 sightings → 9 tickets (8.9×, −88.8%)**.
- **Score** (`services/scorer.py`) — weighted 0–100:
  `0.50 × area + 0.25 × repeats + 0.15 × bus-route + 0.10 × center-lane`
- **File** (`services/filer.py`) — the perceive → decide → act → store loop:

  | Severity | Action | Ticket status |
  |----------|--------|---------------|
  | `≥ 70` | auto-file (+ webhook) | `filed` 🟥 |
  | `40–69` | queue for human | `pending` 🟨 |
  | `< 40` | dismiss | `dismissed` ⬜ |
  | `≥ 85` **on an arterial** | forced human review (expensive repairs need eyes) | `pending` 🟨 |

  Every transition is trace-logged (`agent` or `human` actor) — see `docs/report.md §6` for real JSONL examples.

### 3. Web — `web/` (React + Leaflet)

Dark glass UI: `MapView`, `ReviewQueue`, `UploadZone` + `JobProgress`, `TicketDrawer`, `MethodView`, `CommandPalette` (`⌘K`). Initial bundle is code-split (map + stats rail first, drawer/queue/upload lazy).

---

## 🛠️ Commands you'll actually use

| Command | What it does |
|---------|--------------|
| `make install` | `pip install` vision + agent deps, `npm install` web |
| `make test` | `pytest` suites for `vision/` + `agent/` (55 passed at last check) |
| `make seed-demo` | Pre-seed DynamoDB/S3 with 1 job + 5 tickets (localstack when `DYNAMO_ENDPOINT_URL` / `AWS_ENDPOINT_URL` are set, else real AWS) |
| `make bench` | Stock-OpenCV throughput benchmark on the demo route |
| `make lint` | `flake8` (Python) + `eslint` (web) |
| `make secrets` | `gitleaks` scan, or grep fallback for `AKIA…` / `ghp_…` / `sk-live` |
| `make clean` | Drop `__pycache__` / `*.pyc` |

```bash
make install && make test     # fresh clone → verified
make bench                    # perf after touching vision/
make secrets                  # before every push
```

---

## 📁 Project layout

```
vision/    OpenCV pipeline — ingest, gps, detector (YOLOv8n + classical fusion),
                            blur, embedder (ORB), pipeline orchestrator
agent/     FastAPI triage — routes/ (jobs, tickets, export, health),
                            services/ (cluster, scorer, filer, webhook, trace, cache),
                            db/ (dynamo, s3), models/, worker.py, demo_worker.py
web/       React + Leaflet — Map, Queue, Upload, TicketDrawer, Method, ⌘K palette
                            (npm run dev for HMR, API proxied to :8000)
infra/     Dockerfiles, compose files, localstack/AWS scripts, CloudWatch dashboard
eval/      Demo route + ground truth, bench harness, eval_detector/dedup/severity.py,
                            failure_cases/ gallery
scripts/   GPS sim, synthetic demo generator, label helper, demo seeder, cascade fetcher
docs/      Technical report, arch diagram, perf ledger (PERF.md)
config.yaml  Shared knobs (dedup, severity, privacy, detection) — see below
```

> `specs/` (planning) and run state (`.orchestrator/`, `.token-optimizer/`) are **local-only, never committed** — see `.gitignore`.

---

## ⚙️ Configuration

### `config.yaml` — the knobs that change behavior

Copy-paste reference (defaults shown):

```yaml
ward: "ward-12-demo"

dedup:                       # DBSCAN over GPS + visual similarity
  geo_eps_m: 15              # sightings within 15 m *may* be the same hole
  cos_thresh: 0.82           # …but only if crop embeddings match ≥ 0.82
  min_samples: 2             # 2+ sightings to form a cluster

severity:                    # weights must ~sum to 1.0
  w_area: 0.50               # perspective-normalized hole size
  w_repeat: 0.25             # seen on N passes (saturates at 5)
  w_route: 0.15              # within 50 m of a bus route
  w_lane: 0.10               # center-lane vs shoulder
  auto_file_threshold: 70    # ≥70 → filed automatically
  review_threshold: 40       # 40–69 → human queue; <40 → dismissed

privacy:
  blur_faces: true
  blur_plates: true
  raw_retain_days: 14        # raw video auto-expires; crops keep blurred copies

detection:                   # YOLOv8n + classical fusion
  model: "yolov8n"
  conf_threshold: 0.25
  nms_iou: 0.5
  min_box_px: 24             # smaller boxes are noise — dropped
  classes: [pothole, crack]

embedding:
  dim: 128
  method: "orb"              # or "clip-tiny"
```

**Tuning tips:**
- **Too many duplicate tickets?** Lower `geo_eps_m` (e.g. `10`) or raise `cos_thresh` (e.g. `0.88`).
- **Missing real holes?** Lower `conf_threshold` to `0.20` — but expect more review-queue load.
- **Too aggressive auto-filing?** Raise `auto_file_threshold` to `80`. Threshold changes are trace-logged.

### `.env` — secrets & backends

```bash
cp .env.example .env   # required for real deployments; local compose works without it
```

| Variable | Example | What it's for |
|----------|---------|---------------|
| `AWS_REGION` | `us-east-1` | All AWS calls |
| `S3_RAW_BUCKET` / `S3_CROPS_BUCKET` | `civic-lens-raw` | Uploaded video / blurred crops |
| `DYNAMO_TABLE_DETECTIONS` / `_TICKETS` / `_JOBS` | `cl-tickets` | Detections, tickets, jobs |
| `SQS_QUEUE_URL` | `https://sqs.…/civic-lens-jobs` | Vision work queue (missing → `500 SQS_QUEUE_URL not configured`) |
| `WEBHOOK_SECRET` | `changeme` | HMAC-SHA256 signs `X-CivicLens-Signature` on webhooks |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowlist (prod: `https://<web-host>`) |
| `AWS_ENDPOINT_URL` / `DYNAMO_ENDPOINT_URL` | `http://localhost:4566` / `:8100` | **Local dev only** — point at localstack / DynamoDB-local |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | `test` / `test` | **Local dev only** — never use real keys here |

---

## 🔌 API reference (+ copy-paste examples)

Base URL local: `http://localhost:8000` · interactive docs: `http://localhost:8000/docs`

### `GET /health` — is it alive?

```bash
curl localhost:8000/health
# {"status":"ok","service":"civiclens-agent"}
```

### `POST /jobs` — queue a video by URL

```bash
curl -X POST localhost:8000/jobs -H 'Content-Type: application/json' -d '{
  "video_url": "s3://civic-lens-raw/routeA.mp4",
  "gps_url":   "s3://civic-lens-raw/routeA.csv",
  "ward":      "ward-12-demo"
}'
# {"job_id":"a3f9…","status":"queued"}
```

### `POST /jobs/upload` — queue a video by file (what the web Upload tab uses)

```bash
curl -X POST localhost:8000/jobs/upload \
  -F video=@routeA.mp4 -F gps=@routeA.csv -F ward=ward-12-demo
# {"job_id":"b71c…","status":"queued"}
```

Video: `.mp4` `.mov` `.avi` `.mkv` · GPS: `.csv` `.srt` · **2 GB max** (else `413`).

### `GET /jobs/{job_id}` — poll progress

```bash
curl localhost:8000/jobs/b71c… 
# {"job_id":"b71c…","status":"processing","progress_pct":42.5,"counts":{…}}
```
Statuses: `queued → processing → completed | failed`.

### `GET /tickets` — list tickets

```bash
curl 'localhost:8000/tickets?status=filed&sort=severity'
# [{ "ticket_id":"t_hole01","severity":82,"status":"filed",
#     "centroid":[12.9716,77.5946],"crop_url":"https://…(presigned, 15 min)",
#     "signals":{"area_norm":78,"repeat":100,"bus_route_w":100,"center_lane":100},
#     "trace":[{…}] }, …]
```
`status` ∈ `filed|pending|dismissed` (omit = all) · `sort` ∈ `severity|timestamp` (default `severity`).

### `GET /tickets/{id}` — one ticket

```bash
curl localhost:8000/tickets/t_hole01
```

### `POST /tickets/{id}/override` — human approves / dismisses

```bash
curl -X POST localhost:8000/tickets/t_hole02/override \
  -H 'Content-Type: application/json' -d '{"to":"filed","reason":"confirmed on site"}'
# {"ticket_id":"t_hole02","status":"filed", …}
```
`to` ∈ `filed|pending|dismissed` · already-exported tickets return **`409`** (see gotchas).

### `GET /export.csv?status=filed` — work orders for road crews

```bash
curl -o filed.csv 'localhost:8000/export.csv?status=filed'
head -2 filed.csv
# ticket_id,lat,lon,severity,status,crop_url,video_url,t,RoadName
```
Columns: `ticket_id, lat, lon, severity, status, crop_url, video_url, t, RoadName`. The web *Export CSV* button hits this endpoint.

### `POST /webhooks/test` — verify a receiver

```bash
curl -X POST localhost:8000/webhooks/test \
  -H 'Content-Type: application/json' -d '{"url":"https://example.com/hook"}'
# {"ok":true,"latency_ms":212,"status_code":200}
```
Real `ticket.filed` webhooks carry `{event, ticket_id, lat, lon, severity, status, crop_url, advisory:"verify on site", timestamp}` + `X-CivicLens-Signature: <hmac-sha256>` (verify with `WEBHOOK_SECRET`).

### JavaScript (same API the React app uses)

```js
import { fetchTickets, uploadJob, overrideTicket } from './api/client.js';

const tickets = await fetchTickets({ status: 'pending' });
const { job_id } = await uploadJob({ video, gps });   // File objects
await overrideTicket('t_hole02', { to: 'filed', reason: 'confirmed on site' });
```

---

## 📊 Evaluation — does it actually work?

```bash
python eval/eval_detector.py   # classical path vs key-frame ground truth
python eval/eval_dedup.py      # 80 sightings → clusters, precision / recall
python eval/eval_severity.py   # system vs engineer rank, Spearman rho
```

| Check | Result | Honest caveat |
|-------|--------|---------------|
| Dedup | **80 → 9 (8.9×), precision 1.00, recall 0.88** | One GPS-drift split — documented in `eval/failure_cases/` |
| Severity ranking | **Spearman ρ = 1.00** (PASS ≥ 0.70) | Rank perfect; absolute scores skew low on synthetic data |
| Classical-only detector | P = 0.29, R = 0.50 | That's the *fallback*, not the fused system — YOLO numbers need pothole-trained weights + RDD2020 |
| Full test suite | `make test` → green | Includes hardening tests (auth, injection, override guards) |
| Perf | `docs/PERF.md` — dedup 78→26 ms @ n=400, ORB 11.5→1.8 ms/crop | `make bench` reproduces vision throughput |

Failure gallery (night drop, rain glare, speed breakers, tar patches): `eval/failure_cases/README.md`.

---

## ☁️ Real-AWS deploy

```bash
./infra/scripts/setup-aws.sh   # provisions S3 + DynamoDB + SQS (needs credentials)
CORS_ORIGINS=https://<web-host> WEBHOOK_SECRET=<secret> docker compose up --build
```

Live reference (Oct 2026, `ap-southeast-2`): EC2 `t4g.small` running `agent-api` + `web` from `infra/docker-compose.prod.yml` against real S3/DynamoDB/SQS via the instance role `civiclens-ec2-role` — **no access keys on the box**. See `docs/report.md §5` for the full inventory.

---

## ⚠️ Edge cases & gotchas (read before you debug)

1. **Demo mode ≠ broken.** If the web shows an amber *Demo mode* badge, the API is unreachable and you're seeing mock tickets. Check `agent-api` is up (`curl localhost:8000/health`) — don't file bugs against mock data.
2. **Sample review rows are client-side only.** `SAMPLE_REVIEW` backfills the queue when no real `pending` tickets exist; approving them only flips local state. Real rows persist via `POST /tickets/{id}/override`.
3. **Exported tickets are frozen.** Overriding a ticket with `exported: true` returns **409** — deliberate, so CSVs crews already hold never silently change. Clone the ticket instead.
4. **Arterial ≥ 85 never auto-files.** High-cost road repairs always need a human, even at max severity. Don't "fix" this as a bug.
5. **Video limits bite.** `> 2 GB` → `413 Video exceeds 2GB limit` (both URL `Content-Length` check and multipart path). Weird filenames (paths, spaces, odd extensions) → `422`. Allowed: video `.mp4/.mov/.avi/.mkv`, GPS `.csv/.srt`.
6. **GPS drift splits clusters.** If one hole becomes two tickets ~15–30 m apart, that's the known drift failure (see `eval/failure_cases/`). Mitigate by lowering `geo_eps_m` or improving the track — not by tweaking the visual threshold first.
7. **Lone weak detections vanish.** A single sighting with `conf ≤ 0.5` is dismissed as noise. Real but faint holes need a second pass or a lower `conf_threshold`.
8. **Presigned URLs expire (15 min).** `crop_url`s are re-signed on read; a stale URL from an old export will 403 — re-fetch the ticket or re-export. Presign failures are **fail-open** (you get the `s3://` URI instead of an error).
9. **Ticket list is cached 5 s.** Rapid override → list may look stale for a few seconds. `GET /tickets/{id}` is always fresh.
10. **DynamoDB returns numbers as strings sometimes.** The web normalizes at the API boundary (`normalizeTicket`) — if you write your own client, coerce `severity`/`repeat_count`/`centroid` the same way or `.toFixed()` will crash.
11. **Uploads need patience.** The web gives multipart uploads a **10-minute** timeout (not the default 15 s) — don't shrink it for phone videos on slow links.
12. **CORS defaults to localhost.** Prod needs `CORS_ORIGINS=https://<web-host>` or the map loads with zero tickets and confusing network errors.
13. **Classical detector is a fallback, not the product.** Its P/R (≈0.29/0.50) proves the harness; accuracy claims need YOLO weights trained on potholes. Don't quote classical numbers as system accuracy.
14. **ORB has a 128px floor.** Capping embed inputs at 128px is a 6× win; going to 64px produces zero-vectors and kills recall (tried, reverted — `docs/PERF.md`).
15. **Localstack 3.0 is pinned deliberately.** `localstack/localstack:3.0` is the last OSS track; 4.x needs a token. Don't "upgrade" it casually.

---

## 🔧 Troubleshooting

| Symptom | Likely cause → fix |
|---------|--------------------|
| `docker compose up` fails on ports | `:3000` / `:8000` / `:4566` / `:8100` already bound → `docker ps`, stop the clash |
| Map empty, no Demo badge | `CORS_ORIGINS` wrong in prod, or ad-blocker killing Leaflet tiles → check browser console |
| `SQS_QUEUE_URL not configured` (500) | `.env` missing → `cp .env.example .env` and set it |
| `seed-demo` seeds but API shows 0 tickets | Seeded the wrong backend (local vs real) → check `DYNAMO_ENDPOINT_URL` / `AWS_ENDPOINT_URL` match the stack you're querying |
| Webhook never arrives | Receiver must return 2xx within 10 s; verify HMAC with `WEBHOOK_SECRET` → test with `POST /webhooks/test` |
| `make test` fails on `ultralytics` import | Vision tests need `pip install -r vision/requirements.txt` (or run `make install` first) |

---

## 🧰 Tech stack

`FastAPI · OpenCV 5 / YOLOv8n · scikit-learn DBSCAN · DynamoDB · S3 · SQS · React 19 · Leaflet · Tailwind 4 · Vite · Docker / LocalStack`

Pinned versions: [`requirements.lock`](requirements.lock) (Python) · [`web/package-lock.json`](web/package-lock.json) (JS).

---

## 🤝 Contributing

```bash
make lint && make test && make secrets   # green before you push
```

Keep docs next to the code they describe, update `docs/report.md` numbers with the reproduce command inline, and log perf wins *and* dead ends in `docs/PERF.md` so nobody re-runs a failed idea.

---

## 📄 License

MIT © 2026 Divyanshu — see [LICENSE](LICENSE).
