"""The evidence spine. Every AI output calls write_evidence in the same transaction."""
from __future__ import annotations

from sqlalchemy.orm import Session

from services.common.hashing import sha256_bytes, sha256_text
from services.common.models import Evidence


def write_evidence(
    session: Session,
    *,
    module: str,
    model_version: str,
    payload: str | bytes,
    confidence: float,
    source_ids: list[str | int],
) -> int:
    """Insert one evidence row and return its id. Flushes, does not commit."""
    digest = sha256_bytes(payload) if isinstance(payload, bytes) else sha256_text(payload)
    row = Evidence(
        module=module,
        model_version=model_version,
        input_sha256=digest,
        confidence=float(max(0.0, min(1.0, confidence))),
        source_ids=list(source_ids),
    )
    session.add(row)
    session.flush()
    return row.id
