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

app = FastAPI(
    title="SIYANA API",
    version="0.1.0",
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
    return {"status": "ok", "db": db_reachable()}
