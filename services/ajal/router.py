"""FastAPI router for AJAL: RUL watchlist, benchmark metrics, and the hangar schedule."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.ajal.benchmark import METRICS_PATH
from services.common.db import get_session
from services.common.models import RulPrediction, ScheduleRun

router = APIRouter(prefix="/ajal", tags=["ajal"])


class WatchRow(BaseModel):
    tail: str
    engine_pos: int
    unit_id: int
    dataset: str
    predicted_rul: float
    band: str
    series: list[dict]
    evidence_id: int


def band(rul: float) -> str:
    if rul <= 20:
        return "critical"
    if rul <= 40:
        return "watch"
    return "healthy"


@router.get("/rul/watchlist", response_model=list[WatchRow])
def watchlist(limit: int = 24, session: Session = Depends(get_session)) -> list[WatchRow]:
    rows = session.execute(select(RulPrediction).order_by(RulPrediction.predicted_rul.asc()).limit(limit)).scalars().all()
    return [WatchRow(tail=r.tail, engine_pos=r.engine_pos, unit_id=r.unit_id, dataset=r.dataset, predicted_rul=round(r.predicted_rul, 1), band=band(r.predicted_rul), series=r.series, evidence_id=r.evidence_id) for r in rows]


@router.get("/rul/benchmark")
def benchmark() -> dict:
    if not METRICS_PATH.exists():
        raise HTTPException(404, "benchmark not run: python -m services.ajal.benchmark")
    m = json.loads(METRICS_PATH.read_text())
    return {k: v for k, v in m.items() if k != "predictions"}


@router.get("/schedule/latest")
def latest_schedule(session: Session = Depends(get_session)) -> dict:
    run = session.execute(select(ScheduleRun).order_by(ScheduleRun.id.desc())).scalars().first()
    if run is None:
        raise HTTPException(404, "no schedule yet: POST /ajal/schedule/solve")
    return _run_out(run)


def _run_out(run: ScheduleRun) -> dict:
    return {
        "id": run.id,
        "status": run.status,
        "objective": run.objective,
        "solve_seconds": run.solve_seconds,
        "horizon_hours": run.horizon_hours,
        "assignments": run.assignments,
        "licence_shortage": run.licence_shortage,
        "baseline": run.baseline,
        "evidence_id": run.evidence_id,
        "created_at": run.created_at.isoformat(),
    }


@router.post("/schedule/solve")
def solve_schedule(session: Session = Depends(get_session)) -> dict:
    from services.ajal.seed_schedule import solve_and_store

    return _run_out(solve_and_store(session))
