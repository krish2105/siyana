"""Build the week's task list from open defect events on fleet tails, solve it, store the run.

Estimated hours come from a per-chapter table (typical line-maintenance access + rectification
time). Due dates come from the defect's severity rank: S4 within 24h, S3 within 48h, S2 by day 4,
S1 by end of week. Bays and engineers are the demo hangar; an operator replaces them with their
roster. The roster is deliberately one B1.1 short on Thursday so the infeasibility path is visible.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from services.ajal.scheduler import BaySpec, Engineer, Shift, Task, greedy_edd, schedule
from services.common.evidence import write_evidence
from services.common.models import Bay, DefectEvent, Engineer as EngineerRow, MaintTask, ScheduleRun, Snag, Tail

HORIZON_HOURS = 7 * 24
SCHEDULER_VERSION = "ajal-scheduler/cp-sat/ortools-9.15"

EST_HOURS = {"21": 4, "22": 3, "23": 2, "24": 3, "25": 3, "26": 3, "27": 6, "28": 6, "29": 5, "30": 3, "31": 2, "32": 6, "33": 2, "34": 3, "35": 3, "36": 4, "38": 2, "49": 5, "52": 4, "53": 8, "54": 6, "55": 6, "56": 3, "57": 8, "71": 6, "72": 10, "73": 5, "74": 3, "75": 4, "76": 3, "77": 2, "78": 5, "79": 3, "80": 3}
LICENCE_FOR = {"22": "B2", "23": "B2", "24": "B2", "31": "B2", "33": "B2", "34": "B2", "42": "B2", "44": "B2", "45": "B2", "46": "B2"}
DUE_BY_RANK = {4: 24, 3: 48, 2: 96, 1: HORIZON_HOURS}

BAYS = [
    BaySpec(id="B1", name="Bay 1", capable_ata={"21", "24", "25", "26", "27", "28", "29", "30", "32", "33", "36", "38", "52", "53", "54", "55", "56", "57"}),
    BaySpec(id="B2", name="Bay 2", capable_ata={"21", "22", "23", "24", "25", "26", "27", "29", "31", "33", "34", "35", "38", "49", "52", "53", "55", "56"}),
    BaySpec(id="B3", name="Bay 3", capable_ata={"27", "28", "29", "32", "53", "54", "57", "71", "72", "73", "74", "75", "76", "77", "78", "79", "80"}),
    BaySpec(id="B4", name="Bay 4 · engine", capable_ata={"49", "54", "71", "72", "73", "74", "75", "76", "77", "78", "79", "80"}),
]


def day_shifts(days: list[int], start: int = 6, end: int = 18) -> list[Shift]:
    return [Shift(start=d * 24 + start, end=d * 24 + end) for d in days]


# Day 0 = Monday. Thursday (day 3) has only two B1.1 holders on shift.
ENGINEERS = [
    Engineer(id="E1", name="A. Rao", licences={"B1.1"}, shifts=day_shifts([0, 1, 2, 4, 5])),
    Engineer(id="E2", name="K. Iyer", licences={"B1.1"}, shifts=day_shifts([0, 1, 2, 3, 4])),
    Engineer(id="E3", name="S. Menon", licences={"B1.1", "B2"}, shifts=day_shifts([0, 1, 2, 3, 5])),
    Engineer(id="E4", name="P. Das", licences={"B2"}, shifts=day_shifts([0, 1, 2, 3, 4])),
    Engineer(id="E5", name="R. Gill", licences={"B1.1"}, shifts=day_shifts([1, 2, 4, 5, 6])),
    Engineer(id="E6", name="M. Shah", licences={"B2"}, shifts=day_shifts([2, 3, 4, 5, 6], 14, 22)),
]


def build_tasks(session: Session, limit: int = 28) -> list[Task]:
    from services.gateway.fleet import open_events_query, severity_rank

    q, now = open_events_query(session)
    events = session.execute(q.order_by(DefectEvent.opened_at.desc())).scalars().all()
    if now is None:
        return []
    ranked = sorted(events, key=lambda e: (-severity_rank(e, now), e.opened_at or now))
    seen: set[tuple[str, str]] = set()
    tasks: list[Task] = []
    for e in ranked:
        ch = (e.ata_code or "5300")[:2]
        key = (e.tail or "", ch)
        if key in seen or ch not in EST_HOURS:
            continue
        seen.add(key)
        snag = session.get(Snag, e.snag_id)
        rank = severity_rank(e, now)
        tasks.append(
            Task(
                id=f"WO-{e.work_order_id or e.id}",
                tail=e.tail or "UNKNOWN",
                est_hours=EST_HOURS[ch],
                due_by=DUE_BY_RANK[rank],
                ata=e.ata_code or f"{ch}00",
                licence_required=LICENCE_FOR.get(ch, "B1.1"),
                priority=rank + 1,
                description=(snag.raw_text[:140] if snag else ""),
            )
        )
        if len(tasks) >= limit:
            break
    return tasks


def solve_and_store(session: Session) -> ScheduleRun:
    tasks = build_tasks(session)
    result = schedule(tasks, BAYS, ENGINEERS, HORIZON_HOURS)
    baseline = greedy_edd(tasks, BAYS, ENGINEERS, HORIZON_HOURS)

    session.execute(delete(MaintTask))
    for t in tasks:
        if session.get(Tail, t.tail) is None:
            continue
        session.add(MaintTask(id=t.id, tail=t.tail, ata_code=t.ata, est_hours=t.est_hours, due_by=t.due_by, priority=t.priority, licence_required=t.licence_required, description=t.description))
    for b in BAYS:
        if session.get(Bay, b.id) is None:
            session.add(Bay(id=b.id, name=b.name, capable_ata=sorted(b.capable_ata), available_from=b.available_from))
    for e in ENGINEERS:
        if session.get(EngineerRow, e.id) is None:
            session.add(EngineerRow(id=e.id, name=e.name, licences=sorted(e.licences), shift_hours=e.shift_hours))

    eid = write_evidence(
        session,
        module="ajal",
        model_version=SCHEDULER_VERSION,
        payload="|".join(sorted(t.id for t in tasks)),
        confidence=1.0 if result.status == "optimal" else 0.8 if result.status == "feasible" else 0.6,
        source_ids=[t.id for t in tasks],
    )
    run = ScheduleRun(
        status=result.status,
        objective=result.objective,
        solve_seconds=result.solve_seconds,
        horizon_hours=HORIZON_HOURS,
        assignments=[a.model_dump() for a in result.assignments],
        licence_shortage=[s.model_dump() for s in result.licence_shortage],
        baseline={
            "name": "greedy earliest-due-date",
            "status": baseline.status,
            "weighted_lateness": baseline.weighted_lateness,
            "cp_sat_weighted_lateness": result.weighted_lateness,
            "bays": [{"id": b.id, "name": b.name} for b in BAYS],
            "engineers": [{"id": e.id, "name": e.name, "licences": sorted(e.licences)} for e in ENGINEERS],
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        },
        evidence_id=eid,
    )
    session.add(run)
    session.flush()
    return run


if __name__ == "__main__":
    from services.common.db import SessionLocal

    with SessionLocal() as db:
        r = solve_and_store(db)
        db.commit()
        print(f"[ajal] schedule {r.status}: {len(r.assignments)} assignments in {r.solve_seconds}s; shortages: {len(r.licence_shortage)}")
        for s in r.licence_shortage:
            print("   ", s["message"])
        print("    weighted lateness cp-sat", r.baseline["cp_sat_weighted_lateness"], "vs greedy", r.baseline["weighted_lateness"])
