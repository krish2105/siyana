"""Fleet endpoints that feed the MIRAAT control room.

'Open' is defined explicitly because SDRS has no closure record: a defect event is open when it
has no closed_at and occurred within OPEN_WINDOW_DAYS of the newest event in the corpus. The
window is returned in every response so the UI can state it.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from services.common.db import get_session
from services.common.models import AtaChapter, Card, DefectEvent, MaintTask, ScheduleRun, Signature, Snag, Tail

router = APIRouter(prefix="/fleet", tags=["fleet"])
OPEN_WINDOW_DAYS = 90
AGED_DAYS = 30


def corpus_now(session: Session):
    return session.execute(select(func.max(DefectEvent.opened_at))).scalar()


def open_events_query(session: Session):
    now = corpus_now(session)
    if now is None:
        return select(DefectEvent).where(False), None  # noqa: E712
    since = now - timedelta(days=OPEN_WINDOW_DAYS)
    q = (
        select(DefectEvent)
        .join(Tail, Tail.registration == DefectEvent.tail)
        .where(Tail.in_fleet.is_(True), DefectEvent.closed_at.is_(None), DefectEvent.opened_at >= since)
    )
    return q, now


def severity_rank(ev: DefectEvent, now) -> int:
    """1 recent isolated, 2 aged or S2 prior, 3 recurring or S3 prior, 4 recurring and aged or S4."""
    aged = now is not None and ev.opened_at is not None and (now - ev.opened_at).days > AGED_DAYS
    recurring = ev.signature_id is not None
    prior = int(ev.severity[1]) if ev.severity else 1
    if prior >= 4 or (recurring and aged):
        return 4
    if prior == 3 or recurring:
        return 3
    if prior == 2 or aged:
        return 2
    return 1


class Summary(BaseModel):
    tails: int
    open_defects: int
    recurring_signatures: int
    drafts_pending: int
    unserviceable_tails: int
    open_window_days: int
    corpus_as_of: str | None


@router.get("/summary", response_model=Summary)
def summary(session: Session = Depends(get_session)) -> Summary:
    q, now = open_events_query(session)
    events = session.execute(q).scalars().all()
    unserviceable = {e.tail for e in events if severity_rank(e, now) >= 4}
    return Summary(
        tails=session.execute(select(func.count()).select_from(Tail).where(Tail.in_fleet.is_(True))).scalar() or 0,
        open_defects=len(events),
        recurring_signatures=session.execute(select(func.count()).select_from(Signature)).scalar() or 0,
        drafts_pending=session.execute(select(func.count()).select_from(Card).where(Card.status == "DRAFT")).scalar() or 0,
        unserviceable_tails=len(unserviceable),
        open_window_days=OPEN_WINDOW_DAYS,
        corpus_as_of=now.isoformat() if now else None,
    )


class Zone(BaseModel):
    chapter: str
    title: str
    open_count: int
    max_severity_rank: int
    recurring: int
    tails: list[str]


@router.get("/zones", response_model=list[Zone])
def zones(session: Session = Depends(get_session)) -> list[Zone]:
    q, now = open_events_query(session)
    events = session.execute(q).scalars().all()
    titles = {c.chapter: c.title for c in session.execute(select(AtaChapter).where(AtaChapter.code.like("%00"))).scalars()}
    by: dict[str, dict] = {}
    for e in events:
        ch = (e.ata_code or "0000")[:2]
        d = by.setdefault(ch, {"open": 0, "rank": 0, "rec": 0, "tails": set()})
        d["open"] += 1
        d["rank"] = max(d["rank"], severity_rank(e, now))
        d["rec"] += 1 if e.signature_id else 0
        if e.tail:
            d["tails"].add(e.tail)
    out = [Zone(chapter=ch, title=titles.get(ch, "Unassigned"), open_count=d["open"], max_severity_rank=d["rank"], recurring=d["rec"], tails=sorted(d["tails"])) for ch, d in by.items()]
    return sorted(out, key=lambda z: (-z.max_severity_rank, -z.open_count))


class TailOut(BaseModel):
    registration: str
    aircraft_type: str
    status: str
    open_defects: int
    max_severity_rank: int
    bay_id: str | None
    chapters: list[str]


@router.get("/tails", response_model=list[TailOut])
def tails(session: Session = Depends(get_session)) -> list[TailOut]:
    q, now = open_events_query(session)
    events = session.execute(q).scalars().all()
    latest = session.execute(select(ScheduleRun).order_by(ScheduleRun.id.desc())).scalars().first()
    bay_by_tail: dict[str, str] = {}
    if latest:
        task_tail = {t.id: t.tail for t in session.execute(select(MaintTask)).scalars()}
        for a in latest.assignments:
            t = task_tail.get(a["task_id"])
            if t and t not in bay_by_tail:
                bay_by_tail[t] = a["bay_id"]
    per: dict[str, dict] = {}
    for e in events:
        d = per.setdefault(e.tail, {"open": 0, "rank": 0, "ch": set()})
        d["open"] += 1
        d["rank"] = max(d["rank"], severity_rank(e, now))
        d["ch"].add((e.ata_code or "0000")[:2])
    out = []
    for t in session.execute(select(Tail).where(Tail.in_fleet.is_(True)).order_by(Tail.registration)).scalars():
        d = per.get(t.registration, {"open": 0, "rank": 0, "ch": set()})
        status = "unserviceable" if d["rank"] >= 4 else "serviceable"
        out.append(TailOut(registration=t.registration, aircraft_type=t.aircraft_type, status=status, open_defects=d["open"], max_severity_rank=d["rank"], bay_id=bay_by_tail.get(t.registration), chapters=sorted(d["ch"])))
    return out


class HeatCell(BaseModel):
    tail: str
    chapter: str
    count: int
    recurring: int


class Heatmap(BaseModel):
    tails: list[str]
    chapters: list[str]
    cells: list[HeatCell]
    window_days: int


@router.get("/heatmap", response_model=Heatmap)
def heatmap(days: int = 365, session: Session = Depends(get_session)) -> Heatmap:
    now = corpus_now(session)
    if now is None:
        return Heatmap(tails=[], chapters=[], cells=[], window_days=days)
    since = now - timedelta(days=days)
    rows = session.execute(
        select(DefectEvent.tail, func.left(DefectEvent.ata_code, 2), func.count(), func.count(DefectEvent.signature_id))
        .join(Tail, Tail.registration == DefectEvent.tail)
        .where(Tail.in_fleet.is_(True), DefectEvent.opened_at >= since, DefectEvent.ata_code.is_not(None))
        .group_by(DefectEvent.tail, func.left(DefectEvent.ata_code, 2))
    ).all()
    cells = [HeatCell(tail=t, chapter=ch, count=c, recurring=r) for t, ch, c, r in rows]
    chapters = sorted({c.chapter for c in cells}, key=lambda ch: -sum(x.count for x in cells if x.chapter == ch))[:16]
    tails_ = sorted({c.tail for c in cells}, key=lambda t: -sum(x.count for x in cells if x.tail == t))
    return Heatmap(tails=tails_, chapters=sorted(chapters), cells=[c for c in cells if c.chapter in chapters], window_days=days)


class SnagOut(BaseModel):
    id: int
    tail: str | None
    occurred_at: str | None
    text: str
    ata_code: str | None
    defect_type: str | None
    severity: str | None
    severity_rank: int
    work_order_id: str | None
    signature_id: int | None
    source: str
    source_doc_id: str


class ChapterDrill(BaseModel):
    chapter: str
    title: str
    open_count: int
    snags: list[SnagOut]
    signatures: list[dict]
    cards: list[dict]


@router.get("/ata/{chapter}", response_model=ChapterDrill)
def drill(chapter: str, limit: int = 40, session: Session = Depends(get_session)) -> ChapterDrill:
    ch = chapter[:2]
    title_row = session.get(AtaChapter, ch + "00")
    if title_row is None:
        raise HTTPException(404, f"unknown ATA chapter {ch}")
    q, now = open_events_query(session)
    events = [e for e in session.execute(q.where(DefectEvent.ata_code.like(f"{ch}%")).order_by(DefectEvent.opened_at.desc())).scalars().all()]
    snags = {s.id: s for s in session.execute(select(Snag).where(Snag.id.in_([e.snag_id for e in events[:limit]]))).scalars()}
    out_snags = [
        SnagOut(id=s.id, tail=s.tail, occurred_at=s.occurred_at.isoformat() if s.occurred_at else None, text=s.raw_text, ata_code=s.ata_code, defect_type=s.defect_type, severity=e.severity, severity_rank=severity_rank(e, now), work_order_id=e.work_order_id, signature_id=e.signature_id, source=s.source, source_doc_id=s.source_doc_id)
        for e in events[:limit]
        if (s := snags.get(e.snag_id))
    ]
    sigs = session.execute(select(Signature).where(Signature.ata_code.like(f"{ch}%")).order_by(Signature.count.desc()).limit(20)).scalars().all()
    cards = session.execute(select(Card).where(Card.signature_id.in_([s.id for s in sigs])).order_by(Card.created_at.desc())).scalars().all() if sigs else []
    return ChapterDrill(
        chapter=ch,
        title=title_row.title,
        open_count=len(events),
        snags=out_snags,
        signatures=[{"id": s.id, "canonical": s.canonical, "count": s.count, "aircraft_type": s.aircraft_type, "member_snag_ids": list(s.member_snag_ids), "evidence_id": s.evidence_id, "last_seen": s.last_seen.isoformat() if s.last_seen else None} for s in sigs],
        cards=[{"id": c.id, "signature_id": c.signature_id, "status": c.status, "title": c.body.get("title"), "evidence_id": c.evidence_id} for c in cards],
    )
