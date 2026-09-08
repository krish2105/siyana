from services.ajal.scheduler import BaySpec, Engineer, Shift, Task, greedy_edd, schedule

BAYS = [BaySpec(id="B1", name="Bay 1", capable_ata={"53", "57", "72", "32"}), BaySpec(id="B2", name="Bay 2", capable_ata={"53", "27", "29"})]
ENGS = [
    Engineer(id="E1", licences={"B1.1"}, shifts=[Shift(start=0, end=8), Shift(start=24, end=32)]),
    Engineer(id="E2", licences={"B2"}, shifts=[Shift(start=0, end=8), Shift(start=24, end=32)]),
]


def test_no_overlap_in_one_bay():
    tasks = [Task(id="T1", tail="A", est_hours=4, due_by=8, ata="7200", licence_required="B1.1", priority=3), Task(id="T2", tail="B", est_hours=4, due_by=8, ata="3200", licence_required="B1.1", priority=2)]
    r = schedule(tasks, BAYS[:1], ENGS, horizon_hours=48)
    assert r.status in ("optimal", "feasible")
    a, b = sorted(r.assignments, key=lambda x: x.start)
    assert a.end <= b.start
    assert all(x.end <= x.due_by for x in r.assignments)


def test_missing_licence_is_a_finding_not_an_error():
    tasks = [Task(id="T1", tail="A", est_hours=4, due_by=8, ata="7200", licence_required="B1.3", priority=3)]
    r = schedule(tasks, BAYS, ENGS, horizon_hours=48)
    assert r.status == "infeasible"
    assert r.licence_shortage and r.licence_shortage[0].licence == "B1.3"
    assert "B1.3" in r.licence_shortage[0].message


def test_capacity_shortage_names_the_day():
    tasks = [Task(id=f"T{i}", tail=f"N{i}", est_hours=6, due_by=8, ata="5300", licence_required="B1.1", priority=2) for i in range(3)]
    r = schedule(tasks, BAYS, ENGS, horizon_hours=48)
    assert r.status == "infeasible"
    s = r.licence_shortage[0]
    assert s.day == "Day 1" and s.hours_required == 18 and s.hours_available == 8
    assert len(r.assignments) == 3  # relaxed plan still shows where the work lands


def test_cp_sat_no_worse_than_greedy():
    tasks = [Task(id=f"T{i}", tail=f"N{i}", est_hours=2 + (i % 3), due_by=8 + 8 * (i % 4), ata=["5300", "7200", "2700", "2900"][i % 4], licence_required="B1.1" if i % 3 else "B2", priority=1 + i % 5) for i in range(12)]
    engs = ENGS + [Engineer(id="E3", licences={"B1.1", "B2"}, shifts=[Shift(start=0, end=8), Shift(start=24, end=32)])]
    cp = schedule(tasks, BAYS, engs, horizon_hours=48)
    gr = greedy_edd(tasks, BAYS, engs, horizon_hours=48)
    assert cp.weighted_lateness <= gr.weighted_lateness
