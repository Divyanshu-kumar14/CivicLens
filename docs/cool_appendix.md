# COOL Appendix

- COOL version: TBD (Marketplace ID pending access)
- Baseline AMI/instance: x86 dev box (16 vCPU) + ARM Ampere VPS (2 vCPU)
- Target: c7g.medium (Graviton) vs c6i.large (x86)
- Region: us-east-1 (planned)
- Method: 60s demo route (960×540 h264), 3 runs each, mean reported
- Results (stock-OpenCV path, `make bench`):
  - x86 dev: 146.9 fps sampled, p95 2.3ms, 77% CPU
  - ARM Ampere: 90.0 fps sampled, p95 2.5ms, 71% CPU
  - Graviton+COOL: TBD — same command on c7g.medium
- Arm-workload proof: TODO (htop screenshot on Graviton during processing)
- Reproduce: `make bench`
