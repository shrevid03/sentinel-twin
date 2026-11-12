"""Optional sponsor-tool sinks: Elastic (event index) and Zapier (high-risk alerts).

Both are fire-and-forget, run on a background thread and are skipped when not
configured, so a slow or missing endpoint never blocks checkout.
"""
from __future__ import annotations

import os
import queue
import threading
import time

import httpx

ELASTIC_URL = os.getenv("ELASTIC_URL", "").rstrip("/")  # e.g. https://my-deploy.es.us-central1.gcp.cloud.es.io
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY", "")
ELASTIC_INDEX = os.getenv("ELASTIC_INDEX", "sentinel-twin-events")
ZAPIER_HOOK = os.getenv("ZAPIER_WEBHOOK_URL", "")

_q: queue.Queue = queue.Queue(maxsize=1000)
status = {"elastic": {"enabled": bool(ELASTIC_URL), "sent": 0, "errors": 0},
          "zapier": {"enabled": bool(ZAPIER_HOOK), "sent": 0, "errors": 0}}


def publish(event: dict):
    if not (ELASTIC_URL or ZAPIER_HOOK):
        return
    try:
        _q.put_nowait(event)
    except queue.Full:
        pass


def _worker():
    while True:
        ev = _q.get()
        doc = {"@timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **ev}
        if ELASTIC_URL:
            try:
                r = httpx.post(f"{ELASTIC_URL}/{ELASTIC_INDEX}/_doc", json=doc, timeout=10,
                               headers={"Authorization": f"ApiKey {ELASTIC_API_KEY}"} if ELASTIC_API_KEY else {})
                status["elastic"]["sent" if r.status_code < 300 else "errors"] += 1
            except httpx.HTTPError:
                status["elastic"]["errors"] += 1
        if ZAPIER_HOOK and ev.get("level") == "bad":
            try:
                r = httpx.post(ZAPIER_HOOK, json=doc, timeout=10)
                status["zapier"]["sent" if r.status_code < 300 else "errors"] += 1
            except httpx.HTTPError:
                status["zapier"]["errors"] += 1


threading.Thread(target=_worker, daemon=True).start()
