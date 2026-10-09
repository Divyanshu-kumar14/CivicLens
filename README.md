# CivicLens

Every garbage truck becomes a city inspector. Cities fix potholes weeks faster without extra patrols — the truck that already drives every street files its own tickets with photo proof.

## Quickstart (local, no AWS)

```bash
# 1. Build + boot the full stack (API :8000, web :3000, localstack :4566, DynamoDB :8100)
docker compose up --build

# 2. Seed demo data (idempotent)
make seed-demo

# 3. Open the map
open http://localhost:3000
```

## Make targets

| Target | What |
|---|---|
| `make install` | vision + agent pip deps, web npm deps |
| `make test` | vision + agent pytest suites |
| `make seed-demo` | pre-seed DynamoDB/S3 (targets localstack when `DYNAMO_ENDPOINT_URL`/`AWS_ENDPOINT_URL` are set) |
| `make bench` | stock-OpenCV benchmark on the demo route |
| `make lint` | flake8 + eslint |
| `make secrets` | gitleaks (or grep fallback) secret scan |
| `make clean` | drop `__pycache__` / `*.pyc` |

## Layout

- `vision/` — OpenCV pipeline (ingest, GPS, YOLOv8n + classical fusion, blur, ORB embed)
- `agent/` — FastAPI triage service (routes, DBSCAN dedup, severity, filer, webhooks, SQS worker)
- `web/` — React + Leaflet map, review queue, upload (`npm run dev` for HMR, API proxied to :8000)
- `infra/` — Dockerfiles, compose, localstack/AWS scripts, CloudWatch dashboard
- `eval/` — demo route + ground truth, bench harness, eval scripts (`eval_*.py`), failure gallery
- `scripts/` — GPS sim, synthetic demo generator, label helper, demo seeder, cascade fetcher
- `docs/` — technical report, arch diagram, perf ledger

## Config

Copy `.env.example` to `.env` for real deployments. Shared knobs live in
`config.yaml` (dedup eps/thresholds, severity weights + 70/40 gates, privacy
flags). `specs/` (planning) and run state (`.orchestrator/`, `.token-optimizer/`)
are local-only and never committed — see `.gitignore`.

## Evaluation

```bash
python eval/eval_detector.py   # classical path vs key-frame ground truth
python eval/eval_dedup.py      # 80 sightings -> clusters, precision/recall
python eval/eval_severity.py   # system vs engineer rank, Spearman rho
```

## Real-AWS deploy

```bash
./infra/scripts/setup-aws.sh   # S3 + DynamoDB + SQS (needs credentials)
CORS_ORIGINS=https://<web-host> WEBHOOK_SECRET=<secret> docker compose up --build
```
