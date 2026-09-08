"""SIYANA API gateway. One FastAPI app mounting NAZAR, AJAL, DALEEL, fleet and evidence routers.

Run: .venv/bin/uvicorn services.gateway.main:app --reload --port 8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.ajal.router import router as ajal_router
from services.common.db import db_reachable
from services.daleel.router import router as daleel_router
from services.gateway.evidence_api import router as evidence_router
from services.gateway.fleet import router as fleet_router
from services.gateway.middleware import api_key_required, request_context

VERSION = "0.2.0"

app = FastAPI(
    title="SIYANA API",
    version=VERSION,
    description="Aircraft maintenance intelligence: recurrence detection, RUL, scheduling, vision. Every AI output carries an evidence id.",
)

origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=os.environ.get("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app"),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(request_context)

app.include_router(fleet_router)
app.include_router(daleel_router)
app.include_router(ajal_router)
app.include_router(evidence_router)

try:
    from services.nazar.router import router as nazar_router

    app.include_router(nazar_router)
except ImportError:
    pass


@app.get("/health")
def health() -> dict:
    """Liveness: the process is up and the database answers."""
    return {"status": "ok", "version": VERSION, "db": db_reachable()}


@app.get("/health/ready")
def ready() -> dict:
    """Readiness: the corpus and derived tables are populated enough to serve the control room."""
    from sqlalchemy import func, select

    from services.common.db import SessionLocal
    from services.common.models import Evidence, Signature, Snag, Tail

    with SessionLocal() as s:
        counts = {
            "snags": s.execute(select(func.count()).select_from(Snag)).scalar() or 0,
            "embedded": s.execute(select(func.count()).select_from(Snag).where(Snag.embedding.is_not(None))).scalar() or 0,
            "fleet_tails": s.execute(select(func.count()).select_from(Tail).where(Tail.in_fleet.is_(True))).scalar() or 0,
            "signatures": s.execute(select(func.count()).select_from(Signature)).scalar() or 0,
            "evidence_rows": s.execute(select(func.count()).select_from(Evidence)).scalar() or 0,
        }
    ready_ok = counts["snags"] > 0 and counts["fleet_tails"] > 0
    return {
        "ready": ready_ok,
        "version": VERSION,
        "auth": "api-key" if api_key_required() else "open",
        "embed_backend": os.environ.get("SIYANA_EMBED_BACKEND", "torch"),
        "vision": os.environ.get("SIYANA_ENABLE_NAZAR", "1") != "0",
        "judge": "claude" if os.environ.get("ANTHROPIC_API_KEY") else "embedding",
        **counts,
    }
