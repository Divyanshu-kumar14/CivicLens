# PLAN — bootstrap-foundation (Phase 1, Task 1.1: Project Bootstrap)

## Objective
Repository structure + project bootstrap per IMPLEMENTATION_PLAN.md §1.1 (Tasks 1.1.1–1.1.5).
Goal: `make install / test / lint` entry points exist, configs load, dirty-tree scaffolding committed on an isolated branch.

## Subtasks
| # | Task | Owner | Files | Verify | TDD |
|---|------|-------|-------|--------|-----|
| 1.1.1 | Init repo structure + .gitignore + .env.example | orchestrator (root config owns) | `**/*` dirs, `.gitignore`, `.env.example` | `ls` + `git status` | false |
| 1.1.2 | config.yaml defaults | orchestrator | `config.yaml` | `python3 -c yaml.safe_load` | false |
| 1.1.3 | Makefile | orchestrator | `Makefile` | `make -n test` dry-run | false |
| 1.1.4 | vision/requirements.txt | orchestrator | `vision/requirements.txt` | `pip install --dry-run` (or parse) | false |
| 1.1.5 | agent/requirements.txt | orchestrator | `agent/requirements.txt` | parse / pip check | false |

## Out of scope (next in queue)
- 1.2 vision/ingest.py + gps.py + detector.py (Lane A → python-developer)
- 1.3 infra Dockerfiles + compose (→ devops path, orchestrator-mediated)
- 1.4 agent/main.py + routes (→ backend path)
- 1.5 web shell (→ frontend path)
- Research dispatch skipped: trivial scaffolding (<2 existing files), no shared symbols to blast-radius.

## Verification criteria (Phase 3 gate for this slice)
- `python3 -c "yaml.safe_load(open('config.yaml'))"` exits 0
- `make -n test` prints expected pytest commands
- `grep -rE 'sk-|AKIA|changeme[^"]' --exclude-dir=.git` shows no real secrets (only .env.example placeholder)
- `git status --short` shows only intended new files
