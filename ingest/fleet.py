"""Select the demo fleet: the tails of one aircraft family with the most SDRS activity.

SDRS covers every US operator. The control room shows one operator-sized fleet, so we mark the
top N registrations of the chosen families as in_fleet. The choice is data-driven and recorded.

Run: .venv/bin/python -m ingest.fleet --families A320 A321 B737 --n 24
"""
from __future__ import annotations

import argparse

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from services.common.db import SessionLocal
from services.common.models import Snag, Tail


def select_fleet(session: Session, families: tuple[str, ...], n: int) -> list[str]:
    session.execute(update(Tail).values(in_fleet=False).where(Tail.in_fleet.is_(True)))
    q = (
        select(Snag.tail, func.count(Snag.id).label("c"))
        .join(Tail, Tail.registration == Snag.tail)
        .where(Snag.source == "sdrs", Tail.aircraft_type.in_(families), Snag.tail.is_not(None))
        .group_by(Snag.tail)
        .order_by(func.count(Snag.id).desc())
        .limit(n)
    )
    tails = [t for (t, _) in session.execute(q).all()]
    if tails:
        session.execute(update(Tail).values(in_fleet=True).where(Tail.registration.in_(tails)))
    session.flush()
    return tails


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", nargs="+", default=["A320", "A321", "B737"])
    ap.add_argument("--n", type=int, default=24)
    a = ap.parse_args()
    with SessionLocal() as db:
        tails = select_fleet(db, tuple(a.families), a.n)
        db.commit()
    print(f"[fleet] {len(tails)} tails marked in_fleet: {', '.join(tails)}")
