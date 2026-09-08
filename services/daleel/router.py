"""FastAPI router for DALEEL."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.common.db import get_session
from services.common.models import Card, Signature, Snag
from services.daleel.cards import approve_card, draft_card
from services.daleel.judge import get_judge
from services.daleel.recurrence import judge_free_text

router = APIRouter(prefix="/daleel", tags=["daleel"])


class JudgeRequest(BaseModel):
    text: str = Field(min_length=10, max_length=4000)
    aircraft_type: str | None = None


class NeighbourOut(BaseModel):
    id: int
    text: str
    tail: str | None
    occurred_at: str | None
    work_order_id: str | None
    ata_code: str | None
    similarity: float


class JudgeResponse(BaseModel):
    norm_text: str
    ata_code: str | None
    ata_confidence: float | None
    aircraft_type: str | None
    is_recurrence: bool
    matched_ids: list[int]
    signature: str
    reasoning: str
    confidence: float
    judge_model: str
    neighbours: list[NeighbourOut]
    evidence_id: int


@router.post("/judge", response_model=JudgeResponse)
def judge_endpoint(req: JudgeRequest, session: Session = Depends(get_session)) -> JudgeResponse:
    judge = get_judge()
    r = judge_free_text(session, req.text, req.aircraft_type, judge)
    return JudgeResponse(
        norm_text=r.norm_text,
        ata_code=r.ata_code,
        ata_confidence=r.ata_confidence,
        aircraft_type=r.aircraft_type,
        is_recurrence=r.verdict.is_recurrence,
        matched_ids=r.verdict.matched_ids,
        signature=r.verdict.signature,
        reasoning=r.verdict.reasoning,
        confidence=r.verdict.confidence,
        judge_model=judge.model_version,
        neighbours=[
            NeighbourOut(id=n.id, text=n.text, tail=n.tail, occurred_at=n.occurred_at.isoformat() if n.occurred_at else None, work_order_id=n.work_order_id, ata_code=n.ata_code, similarity=round(n.similarity, 4))
            for n in r.neighbours
        ],
        evidence_id=r.evidence_id,
    )


class SignatureOut(BaseModel):
    id: int
    ata_code: str
    aircraft_type: str | None
    canonical: str
    count: int
    member_snag_ids: list[int]
    tails: list[str]
    first_seen: str | None
    last_seen: str | None
    evidence_id: int
    card_id: int | None
    card_status: str | None


@router.get("/signatures", response_model=list[SignatureOut])
def list_signatures(limit: int = 50, ata: str | None = None, session: Session = Depends(get_session)) -> list[SignatureOut]:
    q = select(Signature).order_by(Signature.count.desc(), Signature.last_seen.desc().nullslast()).limit(limit)
    if ata:
        q = q.where(Signature.ata_code.like(f"{ata[:2]}%"))
    sigs = session.execute(q).scalars().all()
    out = []
    for s in sigs:
        tails = [t for (t,) in session.execute(select(func.distinct(Snag.tail)).where(Snag.id.in_(s.member_snag_ids), Snag.tail.is_not(None)))]
        card = session.execute(select(Card).where(Card.signature_id == s.id).order_by(Card.id.desc())).scalars().first()
        out.append(
            SignatureOut(
                id=s.id, ata_code=s.ata_code, aircraft_type=s.aircraft_type, canonical=s.canonical, count=s.count,
                member_snag_ids=list(s.member_snag_ids), tails=sorted(tails),
                first_seen=s.first_seen.isoformat() if s.first_seen else None, last_seen=s.last_seen.isoformat() if s.last_seen else None,
                evidence_id=s.evidence_id, card_id=card.id if card else None, card_status=card.status if card else None,
            )
        )
    return out


class CardOut(BaseModel):
    id: int
    signature_id: int
    status: str
    body: dict
    evidence_id: int
    created_at: str


def _card_out(c: Card) -> CardOut:
    return CardOut(id=c.id, signature_id=c.signature_id, status=c.status, body=c.body, evidence_id=c.evidence_id, created_at=c.created_at.isoformat())


@router.get("/cards", response_model=list[CardOut])
def list_cards(status: str | None = "DRAFT", limit: int = 50, session: Session = Depends(get_session)) -> list[CardOut]:
    q = select(Card).order_by(Card.created_at.desc()).limit(limit)
    if status:
        q = q.where(Card.status == status)
    return [_card_out(c) for c in session.execute(q).scalars().all()]


@router.get("/cards/{card_id}", response_model=CardOut)
def get_card(card_id: int, session: Session = Depends(get_session)) -> CardOut:
    c = session.get(Card, card_id)
    if c is None:
        raise HTTPException(404, "card not found")
    return _card_out(c)


@router.post("/signatures/{signature_id}/draft", response_model=CardOut)
def draft_endpoint(signature_id: int, session: Session = Depends(get_session)) -> CardOut:
    try:
        return _card_out(draft_card(session, signature_id, get_judge().model_version))
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


class ApprovalRequest(BaseModel):
    engineer_name: str = Field(min_length=2)
    licence_number: str = Field(min_length=3, description="AME / Part-66 licence number; logged with the decision")
    decision: Literal["APPROVED", "REJECTED"]
    note: str | None = None


@router.post("/cards/{card_id}/approve", response_model=CardOut)
def approve_endpoint(card_id: int, req: ApprovalRequest, session: Session = Depends(get_session)) -> CardOut:
    try:
        return _card_out(approve_card(session, card_id, engineer_name=req.engineer_name, licence_number=req.licence_number, decision=req.decision, note=req.note))
    except ValueError as e:
        raise HTTPException(409 if "already" in str(e) else 400, str(e)) from e


@router.get("/metrics")
def daleel_metrics() -> dict:
    """Measured evaluation results (recurrence judge and ATA classifier) from data/metrics."""
    import json

    from services.common.config import settings

    out: dict = {}
    for name in ("daleel_recurrence", "daleel_ata"):
        p = settings.metrics_dir / f"{name}.json"
        if p.exists():
            m = json.loads(p.read_text())
            m.pop("embedding_judge_sweep", None)
            m.pop("top20_classes", None)
            out[name] = m
    if not out:
        raise HTTPException(404, "no DALEEL metrics yet: python -m services.daleel.eval evaluate")
    return out
