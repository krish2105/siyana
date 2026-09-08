"""Map C-MAPSS test engines onto fleet tails so the control room has an RUL watchlist.

C-MAPSS engines are simulated and carry no registration, so the mapping is explicit and stored:
test unit i -> fleet tail (i mod n_tails), engine position (i // n_tails) % 2 + 1. Every stored
prediction carries an evidence row naming the model version and the unit's last-cycle feature hash.
"""
from __future__ import annotations

import json

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ingest.cmapss import load_fd
from services.ajal.benchmark import METRICS_PATH
from services.common.evidence import write_evidence
from services.common.models import RulPrediction, Tail


def fleet_tails(session: Session) -> list[str]:
    return [t for (t,) in session.execute(select(Tail.registration).where(Tail.in_fleet.is_(True)).order_by(Tail.registration))]


def persist_watchlist(session: Session, fd: str = "FD001", *, max_units: int = 48) -> int:
    metrics = json.loads(METRICS_PATH.read_text())
    version = metrics["models"]["lgbm"]["version"]
    tails = fleet_tails(session)
    if not tails:
        raise RuntimeError("no fleet tails: run ingest.fleet first")
    _, test_df, _ = load_fd(fd)
    session.execute(delete(RulPrediction).where(RulPrediction.dataset == fd))
    preds = sorted(metrics["predictions"], key=lambda p: p["lgbm"])[:max_units]
    n = 0
    for i, p in enumerate(preds):
        unit = p["unit"]
        g = test_df[test_df.unit == unit].sort_values("cycle")
        s11 = g["s11"].to_numpy(dtype=float)[-30:]
        series = [{"cycle": int(c), "s11": float(v)} for c, v in zip(g["cycle"].to_numpy()[-30:], s11, strict=True)]
        tail = tails[i % len(tails)]
        pos = (i // len(tails)) % 2 + 1
        eid = write_evidence(
            session,
            module="ajal",
            model_version=version,
            payload=g.tail(1).to_json(),
            confidence=float(max(0.0, min(1.0, 1.0 - metrics["models"]["lgbm"]["rmse"] / 125.0))),
            source_ids=[f"cmapss:{fd}:test_unit:{unit}"],
        )
        session.add(RulPrediction(tail=tail, engine_pos=pos, unit_id=unit, dataset=fd, predicted_rul=float(p["lgbm"]), series=series, evidence_id=eid))
        n += 1
    session.flush()
    return n


if __name__ == "__main__":
    from services.common.db import SessionLocal

    with SessionLocal() as db:
        n = persist_watchlist(db)
        db.commit()
    print(f"[ajal] watchlist rows: {n}")
