"""FastAPI router for NAZAR: upload an inspection image, get findings plus an evidence id."""
from __future__ import annotations

import io
import json
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.common.db import get_session
from services.common.evidence import write_evidence
from services.common.hashing import sha256_bytes
from services.common.models import NazarFinding
from services.common.config import settings

METRICS_PATH = settings.metrics_dir / "nazar.json"
NAZAR_ENABLED = os.environ.get("SIYANA_ENABLE_NAZAR", "1") != "0"

router = APIRouter(prefix="/nazar", tags=["nazar"])
_nazar = None


def get_nazar():
    global _nazar
    if not NAZAR_ENABLED:
        raise HTTPException(503, "Vision inference is disabled on this host (SIYANA_ENABLE_NAZAR=0). Run the API on a host with at least 2 GB RAM, or use Docker Compose, to enable NAZAR.")
    if _nazar is None:
        from services.nazar.inference import Nazar

        _nazar = Nazar()
    return _nazar


@router.post("/inspect")
async def inspect(image: UploadFile = File(...), session: Session = Depends(get_session)) -> dict:
    raw = await image.read()
    if len(raw) > 12 * 1024 * 1024:
        raise HTTPException(413, "image larger than 12 MB")
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as e:  # pillow raises several types
        raise HTTPException(400, f"not an image: {e}") from e
    nazar = get_nazar()
    findings = nazar.predict(img)
    payload = nazar.to_json(findings)
    digest = sha256_bytes(raw)
    conf = max((f.confidence for f in findings), default=0.0)
    eid = write_evidence(session, module="nazar", model_version=nazar.model_version, payload=raw, confidence=conf if findings else 1.0, source_ids=[f"image:{digest[:16]}"])
    row = NazarFinding(image_sha256=digest, filename=image.filename, findings=payload, evidence_id=eid)
    session.add(row)
    session.flush()
    return {"id": row.id, "image_sha256": digest, "width": img.width, "height": img.height, "findings": payload, "model_version": nazar.model_version, "evidence_id": eid}


@router.get("/findings")
def recent(limit: int = 20, session: Session = Depends(get_session)) -> list[dict]:
    rows = session.execute(select(NazarFinding).order_by(NazarFinding.id.desc()).limit(limit)).scalars().all()
    return [{"id": r.id, "filename": r.filename, "image_sha256": r.image_sha256, "findings": r.findings, "evidence_id": r.evidence_id, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/metrics")
def metrics() -> dict:
    if not METRICS_PATH.exists():
        raise HTTPException(404, "NAZAR not evaluated yet: python -m services.nazar.eval")
    return json.loads(METRICS_PATH.read_text())
