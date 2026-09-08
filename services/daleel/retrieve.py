"""k-NN retrieval over pgvector, restricted to the same ATA chapter and aircraft type."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class Neighbour:
    id: int
    text: str
    norm_text: str
    tail: str | None
    occurred_at: datetime | None
    work_order_id: str | None
    ata_code: str | None
    distance: float

    @property
    def similarity(self) -> float:
        return 1.0 - self.distance


def neighbours(
    session: Session,
    vec: np.ndarray | list[float],
    *,
    ata_code: str | None,
    aircraft_type: str | None,
    k: int = 20,
    exclude_id: int | None = None,
    chapter_only: bool = True,
) -> list[Neighbour]:
    """Nearest snags by cosine distance. chapter_only matches on the 2-digit chapter, which is
    how SDRS section codes are actually used in practice; set False for exact 4-digit matching."""
    v = "[" + ",".join(f"{float(x):.6f}" for x in np.asarray(vec).ravel()) + "]"
    where = ["s.embedding IS NOT NULL"]
    params: dict = {"v": v, "k": k}
    if ata_code:
        if chapter_only:
            where.append("left(s.ata_code, 2) = :chapter")
            params["chapter"] = ata_code[:2]
        else:
            where.append("s.ata_code = :ata")
            params["ata"] = ata_code
    if aircraft_type and aircraft_type != "UNKNOWN":
        where.append("s.aircraft_type = :atype")
        params["atype"] = aircraft_type
    if exclude_id is not None:
        where.append("s.id <> :xid")
        params["xid"] = exclude_id
    sql = text(
        f"""
        SELECT s.id, s.raw_text, s.norm_text, s.tail, s.occurred_at, d.work_order_id, s.ata_code,
               (s.embedding <=> CAST(:v AS vector)) AS distance
        FROM snags s
        LEFT JOIN LATERAL (
            SELECT work_order_id FROM defect_events WHERE snag_id = s.id LIMIT 1
        ) d ON TRUE
        WHERE {' AND '.join(where)}
        ORDER BY s.embedding <=> CAST(:v AS vector)
        LIMIT :k
        """
    )
    rows = session.execute(sql, params).all()
    return [Neighbour(id=r[0], text=r[1], norm_text=r[2] or "", tail=r[3], occurred_at=r[4], work_order_id=r[5], ata_code=r[6], distance=float(r[7])) for r in rows]
