"""Recurrence pipeline: normalise -> classify -> embed -> retrieve k=20 -> judge -> evidence.

Every verdict writes an evidence row (module='daleel') whose source_ids are the neighbour snag
ids shown to the judge. run_recurrence works on a stored snag; judge_free_text serves the
command palette with pasted text and never stores a snag.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.common.evidence import write_evidence
from services.common.models import DefectEvent, Signature, Snag
from services.daleel.ata_classifier import MODEL_PATH, AtaClassifier
from services.daleel.embed import Embedder
from services.daleel.judge import Judge, Verdict
from services.daleel.normalise import normalise
from services.daleel.retrieve import Neighbour, neighbours

K = 20


@dataclass
class RecurrenceResult:
    snag_id: int
    text: str
    norm_text: str
    ata_code: str | None
    ata_confidence: float | None
    aircraft_type: str | None
    verdict: Verdict
    neighbours: list[Neighbour]
    evidence_id: int
    signature_id: int | None = None


_classifier: AtaClassifier | None = None


def classifier() -> AtaClassifier | None:
    global _classifier
    if _classifier is None and os.environ.get("SIYANA_ATA_CLASSIFIER", "1") != "0":
        from services.common.artefacts import ensure_artefact

        if ensure_artefact(MODEL_PATH.name) is not None:
            _classifier = AtaClassifier()
    return _classifier


def _judge_and_record(
    session: Session,
    *,
    snag_id: int,
    text: str,
    norm_text: str,
    ata_code: str | None,
    ata_conf: float | None,
    aircraft_type: str | None,
    vec,
    judge: Judge,
    exclude_id: int | None,
) -> RecurrenceResult:
    nbrs = neighbours(session, vec, ata_code=ata_code, aircraft_type=aircraft_type, k=K, exclude_id=exclude_id)
    verdict = judge.judge(norm_text, nbrs)
    evidence_id = write_evidence(
        session,
        module="daleel",
        model_version=f"{judge.model_version}; retrieval={Embedder().model_version} k={K}",
        payload=norm_text,
        confidence=verdict.confidence,
        source_ids=[n.id for n in nbrs],
    )
    return RecurrenceResult(snag_id, text, norm_text, ata_code, ata_conf, aircraft_type, verdict, nbrs, evidence_id)


def judge_free_text(session: Session, text: str, aircraft_type: str | None, judge: Judge) -> RecurrenceResult:
    norm = normalise(text).text
    clf = classifier()
    ata_code, conf = clf.predict(text) if clf else (None, None)
    vec = Embedder().encode([norm])[0]
    return _judge_and_record(
        session, snag_id=-1, text=text, norm_text=norm, ata_code=ata_code, ata_conf=conf,
        aircraft_type=aircraft_type, vec=vec, judge=judge, exclude_id=None,
    )


def run_recurrence(session: Session, snag_id: int, judge: Judge) -> RecurrenceResult:
    snag = session.get(Snag, snag_id)
    if snag is None:
        raise ValueError(f"snag {snag_id} not found")
    norm = snag.norm_text or normalise(snag.raw_text).text
    ata_code, conf = snag.ata_code, None
    if ata_code is None and (clf := classifier()):
        ata_code, conf = clf.predict(snag.raw_text)
        snag.ata_code, snag.ata_source = ata_code, "daleel"
    vec = snag.embedding if snag.embedding is not None else Embedder().encode([norm])[0]
    if snag.embedding is None:
        snag.norm_text, snag.embedding = norm, list(map(float, vec))
    result = _judge_and_record(
        session, snag_id=snag.id, text=snag.raw_text, norm_text=norm, ata_code=ata_code, ata_conf=conf,
        aircraft_type=snag.aircraft_type, vec=vec, judge=judge, exclude_id=snag.id,
    )
    if result.verdict.is_recurrence:
        result.signature_id = upsert_signature(session, result)
    return result


def upsert_signature(session: Session, result: RecurrenceResult) -> int:
    """Attach the snag and its matches to an existing signature sharing a member, else create one."""
    members = sorted({result.snag_id, *result.verdict.matched_ids})
    existing = session.execute(
        select(Signature).where(Signature.ata_code == (result.ata_code or "0000"), Signature.member_snag_ids.overlap(members))
    ).scalars().first()
    times = [t for (t,) in session.execute(select(Snag.occurred_at).where(Snag.id.in_(members))) if t]
    if existing:
        merged = sorted(set(existing.member_snag_ids) | set(members))
        existing.member_snag_ids = merged
        existing.count = len(merged)
        existing.first_seen = min([*(times or []), *( [existing.first_seen] if existing.first_seen else [])], default=None)
        existing.last_seen = max([*(times or []), *( [existing.last_seen] if existing.last_seen else [])], default=None)
        sig_id = existing.id
    else:
        sig = Signature(
            ata_code=result.ata_code or "0000",
            aircraft_type=result.aircraft_type,
            canonical=result.verdict.signature,
            member_snag_ids=members,
            count=len(members),
            first_seen=min(times) if times else None,
            last_seen=max(times) if times else None,
            evidence_id=result.evidence_id,
        )
        session.add(sig)
        session.flush()
        sig_id = sig.id
    session.execute(
        DefectEvent.__table__.update().where(DefectEvent.snag_id.in_(members)).values(signature_id=sig_id)
    )
    return sig_id


def scan(session: Session, judge: Judge, *, limit: int = 500, since: datetime | None = None, in_fleet_only: bool = True) -> int:
    """Judge recent fleet snags that are not yet in a signature. Returns recurrences found."""
    q = select(Snag.id).where(Snag.source == "sdrs", Snag.embedding.is_not(None), Snag.ata_code.is_not(None))
    if in_fleet_only:
        from services.common.models import Tail

        q = q.join(Tail, Tail.registration == Snag.tail).where(Tail.in_fleet.is_(True))
    if since:
        q = q.where(Snag.occurred_at >= since)
    q = q.order_by(Snag.occurred_at.desc()).limit(limit)
    found = 0
    for (sid,) in session.execute(q).all():
        already = session.execute(select(DefectEvent.signature_id).where(DefectEvent.snag_id == sid)).scalar()
        if already:
            continue
        res = run_recurrence(session, sid, judge)
        if res.verdict.is_recurrence:
            found += 1
        session.commit()
    return found


if __name__ == "__main__":
    import argparse

    from services.common.db import SessionLocal
    from services.daleel.judge import get_judge

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--all-tails", action="store_true")
    a = ap.parse_args()
    with SessionLocal() as db:
        j = get_judge()
        print(f"[daleel] judge: {j.model_version}")
        n = scan(db, j, limit=a.limit, in_fleet_only=not a.all_tails)
    print(f"[daleel] recurrences found: {n}")
