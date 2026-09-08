"""Cross-cutting HTTP concerns: request ids, structured access logs, optional API-key auth for
mutating routes, and a small in-memory rate limit for the expensive AI endpoints."""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("siyana.access")
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)

MUTATING_PREFIXES = ("/daleel/cards", "/daleel/signatures", "/ajal/schedule/solve", "/nazar/inspect")
RATE_LIMITED = {"/daleel/judge": (20, 60.0), "/nazar/inspect": (10, 60.0)}  # (requests, window seconds)
_buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def api_key_required() -> str | None:
    return os.environ.get("SIYANA_API_KEY") or None


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    request.state.request_id = rid
    started = time.perf_counter()

    # Optional API key on every mutating route. Unset means an open demo deployment.
    key = api_key_required()
    if key and request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith(MUTATING_PREFIXES):
        if request.headers.get("x-siyana-key") != key:
            return JSONResponse({"detail": "missing or invalid X-SIYANA-KEY", "request_id": rid}, status_code=401, headers={"x-request-id": rid})

    # Token bucket per client for the endpoints that call models.
    limit = RATE_LIMITED.get(request.url.path)
    if limit and request.method == "POST":
        n, window = limit
        now = time.monotonic()
        q = _buckets[(_client_ip(request), request.url.path)]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= n:
            return JSONResponse({"detail": f"rate limit: {n} requests per {int(window)}s on {request.url.path}", "request_id": rid}, status_code=429, headers={"x-request-id": rid, "retry-after": str(int(window))})
        q.append(now)

    response = await call_next(request)
    response.headers["x-request-id"] = rid
    log.info(json.dumps({"ts": time.time(), "rid": rid, "method": request.method, "path": request.url.path, "status": response.status_code, "ms": round((time.perf_counter() - started) * 1000, 1), "ip": _client_ip(request)}))
    return response
