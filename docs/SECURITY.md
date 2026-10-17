# Security
- Secret rotation: replace WEBHOOK_SECRET / ADMIN_SECRET before deploy.
- Retention: production AWS lifecycle (14d raw, 90d detections) enforced; local stack lacks TTL (see README).
- Privacy: blur verified per host log; raw retention not proof locally.
