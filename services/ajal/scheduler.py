"""Hangar slot and licensed-engineer assignment with OR-Tools CP-SAT.

Hard constraints: every task ends by its airworthiness due date, runs in a bay rated for its ATA
chapter, and is worked by one engineer holding the required licence; no bay or engineer is
double-booked; engineers only work inside their shift windows. Objective: minimise priority-weighted
completion time.

Infeasibility is a finding, not an error: the planner learns before the week starts that they are
short a licence category, and by how many hours.
"""
from __future__ import annotations

import time
from typing import Literal

from ortools.sat.python import cp_model
from pydantic import BaseModel, Field

HOURS_PER_DAY = 24


class Task(BaseModel):
    id: str
    tail: str
    est_hours: int = Field(ge=1)
    due_by: int = Field(ge=1, description="hour index in the horizon by which the task must be complete")
    ata: str
    licence_required: str
    priority: int = Field(ge=1, le=5)
    description: str = ""


class BaySpec(BaseModel):
    id: str
    name: str = ""
    capable_ata: set[str]
    available_from: int = 0


class Shift(BaseModel):
    start: int
    end: int


class Engineer(BaseModel):
    id: str
    name: str = ""
    licences: set[str]
    shifts: list[Shift]

    @property
    def shift_hours(self) -> int:
        return sum(s.end - s.start for s in self.shifts)


class Assignment(BaseModel):
    task_id: str
    bay_id: str
    engineer_id: str
    start: int
    end: int
    tail: str
    ata: str
    licence: str
    description: str
    due_by: int


class LicenceShortage(BaseModel):
    licence: str
    tasks: list[str]
    hours_required: int
    hours_available: int
    day: str | None = None
    start: int | None = None
    end: int | None = None
    bay_id: str | None = None
    message: str


class ScheduleResult(BaseModel):
    status: Literal["optimal", "feasible", "infeasible"]
    assignments: list[Assignment]
    objective: int | None
    solve_seconds: float
    licence_shortage: list[LicenceShortage]
    weighted_lateness: int


def _chapter(ata: str) -> str:
    return ata[:2]


def weighted_lateness(tasks: list[Task], assignments: list[Assignment]) -> int:
    ends = {a.task_id: a.end for a in assignments}
    return sum(t.priority * max(0, ends.get(t.id, t.due_by + t.est_hours) - t.due_by) for t in tasks)


def schedule(tasks: list[Task], bays: list[BaySpec], engineers: list[Engineer], horizon_hours: int, time_limit_s: float = 20.0) -> ScheduleResult:
    t0 = time.time()
    m = cp_model.CpModel()
    starts, ends, bay_choice, eng_choice = {}, {}, {}, {}
    bay_intervals: dict[str, list] = {b.id: [] for b in bays}
    eng_intervals: dict[str, list] = {e.id: [] for e in engineers}
    hopeless: list[Task] = []

    for t in tasks:
        allowed_bays = [b for b in bays if _chapter(t.ata) in b.capable_ata]
        allowed_engs = [e for e in engineers if t.licence_required in e.licences]
        if not allowed_bays or not allowed_engs:
            hopeless.append(t)
            continue
        s = m.NewIntVar(0, horizon_hours, f"s_{t.id}")
        e = m.NewIntVar(0, horizon_hours, f"e_{t.id}")
        m.Add(e == s + t.est_hours)
        m.Add(e <= t.due_by)  # hard: airworthiness limit
        starts[t.id], ends[t.id] = s, e

        bvars = []
        for b in allowed_bays:
            lit = m.NewBoolVar(f"b_{t.id}_{b.id}")
            m.Add(s >= b.available_from).OnlyEnforceIf(lit)
            bay_intervals[b.id].append(m.NewOptionalIntervalVar(s, t.est_hours, e, lit, f"ib_{t.id}_{b.id}"))
            bvars.append((b.id, lit))
        m.AddExactlyOne(lit for _, lit in bvars)
        bay_choice[t.id] = bvars

        evars = []
        for eng in allowed_engs:
            for k, sh in enumerate(eng.shifts):
                if sh.end - sh.start < t.est_hours:
                    continue
                lit = m.NewBoolVar(f"e_{t.id}_{eng.id}_{k}")
                m.Add(s >= sh.start).OnlyEnforceIf(lit)
                m.Add(e <= sh.end).OnlyEnforceIf(lit)
                eng_intervals[eng.id].append(m.NewOptionalIntervalVar(s, t.est_hours, e, lit, f"ie_{t.id}_{eng.id}_{k}"))
                evars.append((eng.id, lit))
        if not evars:
            hopeless.append(t)
            del starts[t.id], ends[t.id]
            continue
        m.AddExactlyOne(lit for _, lit in evars)
        eng_choice[t.id] = evars

    for ivs in bay_intervals.values():
        if len(ivs) > 1:
            m.AddNoOverlap(ivs)
    for ivs in eng_intervals.values():
        if len(ivs) > 1:
            m.AddNoOverlap(ivs)

    modelled = [t for t in tasks if t.id in starts]
    m.Minimize(sum(t.priority * ends[t.id] for t in modelled))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_workers = 8
    status = solver.Solve(m) if modelled else cp_model.OPTIMAL
    elapsed = time.time() - t0

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) and not hopeless:
        assignments = _extract(solver, modelled, bay_choice, eng_choice, starts, ends)
        return ScheduleResult(
            status="optimal" if status == cp_model.OPTIMAL else "feasible",
            assignments=assignments,
            objective=int(solver.ObjectiveValue()),
            solve_seconds=round(elapsed, 2),
            licence_shortage=[],
            weighted_lateness=weighted_lateness(tasks, assignments),
        )

    # Infeasible: explain it. Relax due dates and solve again so we can still show a plan, then
    # compute the licence gap per category and per day.
    shortage = licence_shortage(tasks, engineers, bays, horizon_hours, hopeless)
    relaxed = _relaxed_plan(tasks, bays, engineers, horizon_hours, time_limit_s / 2)
    return ScheduleResult(
        status="infeasible",
        assignments=relaxed,
        objective=None,
        solve_seconds=round(time.time() - t0, 2),
        licence_shortage=shortage,
        weighted_lateness=weighted_lateness(tasks, relaxed),
    )


def _extract(solver, tasks, bay_choice, eng_choice, starts, ends) -> list[Assignment]:
    out = []
    for t in tasks:
        bay = next(bid for bid, lit in bay_choice[t.id] if solver.Value(lit))
        eng = next(eid for eid, lit in eng_choice[t.id] if solver.Value(lit))
        out.append(Assignment(task_id=t.id, bay_id=bay, engineer_id=eng, start=solver.Value(starts[t.id]), end=solver.Value(ends[t.id]), tail=t.tail, ata=t.ata, licence=t.licence_required, description=t.description, due_by=t.due_by))
    return sorted(out, key=lambda a: (a.bay_id, a.start))


def _relaxed_plan(tasks, bays, engineers, horizon_hours, time_limit_s) -> list[Assignment]:
    """Due dates and shift windows relaxed: list-schedule every placeable task so the Gantt still
    shows where the work lands and how far past its deadline it falls. Never recurses."""
    del time_limit_s
    bay_free = {b.id: b.available_from for b in bays}
    eng_free = {e.id: min((s.start for s in e.shifts), default=0) for e in engineers}
    out: list[Assignment] = []
    for t in sorted(tasks, key=lambda x: (x.due_by, -x.priority)):
        cands = [b for b in bays if _chapter(t.ata) in b.capable_ata]
        engs = [e for e in engineers if t.licence_required in e.licences]
        if not cands or not engs:
            continue
        b = min(cands, key=lambda x: bay_free[x.id])
        e = min(engs, key=lambda x: eng_free[x.id])
        s = max(bay_free[b.id], eng_free[e.id])
        bay_free[b.id] = eng_free[e.id] = s + t.est_hours
        out.append(Assignment(task_id=t.id, bay_id=b.id, engineer_id=e.id, start=s, end=s + t.est_hours, tail=t.tail, ata=t.ata, licence=t.licence_required, description=t.description, due_by=t.due_by))
    return sorted(out, key=lambda a: (a.bay_id, a.start))


def licence_shortage(tasks: list[Task], engineers: list[Engineer], bays: list[BaySpec], horizon_hours: int, hopeless: list[Task]) -> list[LicenceShortage]:
    """Per licence category and per day: hours demanded before the due date vs hours rostered."""
    out: list[LicenceShortage] = []
    days = range((horizon_hours + HOURS_PER_DAY - 1) // HOURS_PER_DAY)
    licences = sorted({t.licence_required for t in tasks})
    for lic in licences:
        holders = [e for e in engineers if lic in e.licences]
        for d in days:
            d0, d1 = d * HOURS_PER_DAY, (d + 1) * HOURS_PER_DAY
            due_today = [t for t in tasks if t.licence_required == lic and d0 < t.due_by <= d1]
            if not due_today:
                continue
            required = sum(t.est_hours for t in due_today)
            # Capacity available up to the end of this day, less demand that had to be met earlier.
            avail = sum(max(0, min(s.end, d1) - s.start) for e in holders for s in e.shifts)
            earlier = sum(t.est_hours for t in tasks if t.licence_required == lic and t.due_by <= d0)
            avail_net = avail - earlier
            if required > avail_net or any(t in hopeless for t in due_today):
                gap = required - max(0, avail_net)
                out.append(
                    LicenceShortage(
                        licence=lic,
                        tasks=[t.id for t in due_today],
                        hours_required=required,
                        hours_available=max(0, avail_net),
                        day=f"Day {d + 1}",
                        start=d0,
                        end=d1,
                        message=(
                            f"Short {max(gap, 1)}h of {lic} on day {d + 1}: {required}h due, {max(0, avail_net)}h rostered"
                            + (" (no engineer holds this licence)" if not holders else "")
                        ),
                    )
                )
    for t in hopeless:
        if not any(t.id in s.tasks for s in out):
            no_bay = not any(_chapter(t.ata) in b.capable_ata for b in bays)
            out.append(LicenceShortage(licence=t.licence_required, tasks=[t.id], hours_required=t.est_hours, hours_available=0, message=(f"No bay rated for ATA {t.ata}" if no_bay else f"No engineer holds {t.licence_required}") + f" for task {t.id}"))
    return out


def greedy_edd(tasks: list[Task], bays: list[BaySpec], engineers: list[Engineer], horizon_hours: int) -> ScheduleResult:
    """Earliest-due-date list scheduling: the baseline a planner does by hand."""
    t0 = time.time()
    bay_free = {b.id: b.available_from for b in bays}
    eng_busy: dict[str, list[tuple[int, int]]] = {e.id: [] for e in engineers}
    out: list[Assignment] = []
    for t in sorted(tasks, key=lambda x: (x.due_by, -x.priority)):
        cands = [b for b in bays if _chapter(t.ata) in b.capable_ata]
        engs = [e for e in engineers if t.licence_required in e.licences]
        if not cands or not engs:
            continue
        best = None
        for b in cands:
            for e in engs:
                for sh in e.shifts:
                    s = max(bay_free[b.id], sh.start)
                    for bs, be in sorted(eng_busy[e.id]):
                        if s < be and s + t.est_hours > bs:
                            s = be
                    if s + t.est_hours <= sh.end and (best is None or s < best[0]):
                        best = (s, b.id, e.id)
        if best is None:
            continue
        s, bid, eid = best
        bay_free[bid] = s + t.est_hours
        eng_busy[eid].append((s, s + t.est_hours))
        out.append(Assignment(task_id=t.id, bay_id=bid, engineer_id=eid, start=s, end=s + t.est_hours, tail=t.tail, ata=t.ata, licence=t.licence_required, description=t.description, due_by=t.due_by))
    late = weighted_lateness(tasks, out)
    return ScheduleResult(status="feasible" if late == 0 and len(out) == len(tasks) else "infeasible", assignments=out, objective=None, solve_seconds=round(time.time() - t0, 3), licence_shortage=[], weighted_lateness=late)
