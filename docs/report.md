# CivicLens — Technical Report (skeleton, Phase 1.6.4)

> Status: section headers only. Each section gets filled as its phase lands.
> Figures: `docs/arch_diagram.png` (Appendix A Mermaid, checked in).

## 1. Problem & Impact
TODO (Phase 3): pothole repair latency, cost of patrols vs garbage-truck reuse.

## 2. Users & Buyer
TODO (Phase 3): city works dept buyer, crew + citizen users.

## 3. Architecture
TODO (Phase 2): S3 raw → SQS → Graviton worker (G-API decode→detect→blur→embed)
→ Dynamo detections → cluster/score/file → tickets+traces → React map → CSV/webhook.

## 4. OpenCV 5 Implementation
TODO (Phase 2): YOLOv8n + classical fusion params, G-API graph, blur recall ≥0.95.

## 5. AWS Deployment
TODO (Phase 3): S3/DynamoDB/SQS/EC2 Graviton, `infra/scripts/setup-aws.sh` evidence.

## 6. Agentic Loop
TODO (Phase 2): perceive→decide→act→store, trace JSONL evidence, override path.

## 7. COOL Benchmark
TODO (Phase 2/3): `eval/bench` results table (Graviton+COOL vs x86 stock).

## 8. Evaluation Results
TODO (Phase 2): detector P/R on RDD2020, dedup ratio on demo route (hole_id ground truth).

## 9. Failure Cases
TODO (Phase 2/3): curated `eval/failure_cases/` + mitigations.

## 10. Responsible Use
TODO (Phase 3): face/plate blur, 14-day raw retention, human override, advisory not auto-dispatch.

## 11. Reproducibility
TODO (Phase 3): `requirements.lock` (post Oct 17 freeze), `make` targets, pinned AMIs/instances.
