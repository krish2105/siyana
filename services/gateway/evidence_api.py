"""Evidence and audit endpoints: the 'Why?' behind every AI output, and who approved what."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.common.db import get_session
from services.common.models import Approval, Card, Evidence, Snag

router = APIRouter(tags=["evidence"])


@router.get("/evidence/{evidence_id}")
def get_evidence(evidence_id: int, session: Session = Depends(get_session)) -> dict:
    row = session.get(Evidence, evidence_id)
    if row is None:
        raise HTTPException(404, "evidence not found")
    snag_ids = [i for i in row.source_ids if isinstance(i, int)]
    snags = session.execute(select(Snag.id, Snag.raw_text, Snag.tail, Snag.source, Snag.source_doc_id).where(Snag.id.in_(snag_ids))).all() if snag_ids else []
    return {
        "id": row.id,
        "module": row.module,
        "model_version": row.model_version,
        "input_sha256": row.input_sha256,
        "confidence": row.confidence,
        "source_ids": row.source_ids,
        "created_at": row.created_at.isoformat(),
        "sources": [{"id": i, "text": t, "tail": tail, "source": src, "source_doc_id": doc} for i, t, tail, src, doc in snags],
    }


@router.get("/audit/approvals")
def approvals(limit: int = 100, session: Session = Depends(get_session)) -> list[dict]:
    rows = session.execute(select(Approval, Card).join(Card, Card.id == Approval.card_id).order_by(Approval.created_at.desc()).limit(limit)).all()
    return [
        {"id": a.id, "card_id": a.card_id, "card_title": c.body.get("title"), "engineer_name": a.engineer_name, "licence_number": a.licence_number, "decision": a.decision, "note": a.note, "created_at": a.created_at.isoformat(), "evidence_id": c.evidence_id}
        for a, c in rows
    ]
