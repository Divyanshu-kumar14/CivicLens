"""HMAC-signed webhook delivery with retries + dead-letter logging.

Plan ref: IMPLEMENTATION_PLAN.md Task 2.2.4.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass

log = logging.getLogger("civiclens.webhook")
RETRY_BACKOFF_S = (1, 2, 4)  # 3 attempts max


@dataclass
class WebhookResult:
    ok: bool
    status_code: int = 0
    latency_ms: int = 0
    attempts: int = 0


class WebhookService:
    def __init__(self, config: dict | None = None):
        """Secret from WEBHOOK_SECRET env (never logged)."""
        self.secret = os.getenv("WEBHOOK_SECRET", "changeme")

    def build_payload(self, ticket: dict) -> dict:
        centroid = ticket.get("centroid", [0.0, 0.0])
        return {
            "event": "ticket.filed",
            "ticket_id": ticket.get("ticket_id", ""),
            "lat": centroid[0] if len(centroid) > 0 else 0.0,
            "lon": centroid[1] if len(centroid) > 1 else 0.0,
            "severity": ticket.get("severity", 0),
            "status": ticket.get("status", ""),
            "crop_url": ticket.get("crop_url", ""),
            "advisory": "verify on site",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def sign_payload(self, payload: dict) -> str:
        """HMAC-SHA256 hex digest of the canonical JSON payload."""
        import json

        body = json.dumps(payload, sort_keys=True).encode()
        return hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()

    async def send(self, url: str, payload: dict) -> WebhookResult:
        """POST with signature header; retry 3x with backoff; dead-letter on fail."""
        import json

        import httpx

        body = json.dumps(payload, sort_keys=True).encode()
        headers = {"Content-Type": "application/json",
                   "X-CivicLens-Signature": self.sign_payload(payload)}
        attempts, started = 0, time.monotonic()
        async with httpx.AsyncClient(timeout=10) as client:
            for wait in (*RETRY_BACKOFF_S, None):
                attempts += 1
                try:
                    resp = await client.post(url, content=body, headers=headers)
                    latency = int((time.monotonic() - started) * 1000)
                    if 200 <= resp.status_code < 300:
                        return WebhookResult(True, resp.status_code, latency, attempts)
                    log.warning("webhook %s -> %s (attempt %d)", url, resp.status_code, attempts)
                except Exception as exc:
                    log.warning("webhook %s failed (attempt %d): %s", url, attempts, exc)
                if wait is not None:
                    await asyncio.sleep(wait)
        latency = int((time.monotonic() - started) * 1000)
        log.error("DEAD-LETTER webhook %s after %d attempts: %s", url, attempts, payload.get("ticket_id"))
        return WebhookResult(False, 0, latency, attempts)
