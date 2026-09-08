"""Customer tech-log adapter. This is the one file an operator replaces.

Contract: a CSV with these columns (header row required, extra columns ignored):

    tail            registration, e.g. VT-ABC
    occurred_at     ISO 8601 date or datetime
    ata_code        4-digit ATA code, or 2-digit chapter, or blank (DALEEL classifies blanks)
    text            the free-text snag as written in the tech log
    work_order_id   the work order or tech-log page reference
    closed_at       ISO 8601 date or blank if still open
    aircraft_type   optional; defaults to the family inferred from the tail's existing record

Rows are de-identified at the DALEEL normalise step, not here: the raw text is kept so an
auditor can trace a card back to the exact entry.

Run: .venv/bin/python -m ingest.adapters.client_techlog path/to/export.csv
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ingest.common import record_run
from services.common.db import SessionLocal
from services.common.models import AtaChapter, DefectEvent, Snag, Tail

COLUMNS = ["tail", "occurred_at", "ata_code", "text", "work_order_id", "closed_at"]


def _dt(value: str | None) -> datetime | None:
    if not value or not value.strip():
        return None
    v = value.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(v)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _ata(value: str | None, known: set[str]) -> str | None:
    if not value or not value.strip():
        return None
    code = "".join(ch for ch in value if ch.isdigit())
    if len(code) == 2:
        code += "00"
    return code if code in known else None


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"tech-log CSV is missing required columns: {', '.join(missing)}")
        return [row for row in reader if (row.get("text") or "").strip()]


def load_rows(rows: list[dict[str, str]], session: Session, run_id: int | None, aircraft_type_default: str = "UNKNOWN") -> int:
    known = {c for (c,) in session.execute(select(AtaChapter.code))}
    tails = {}
    for r in rows:
        reg = r["tail"].strip().upper()
        tails.setdefault(reg, {"registration": reg, "aircraft_type": (r.get("aircraft_type") or aircraft_type_default).strip().upper(), "in_fleet": True})
    if tails:
        session.execute(pg_insert(Tail).values(list(tails.values())).on_conflict_do_update(index_elements=["registration"], set_={"in_fleet": True}))
    n = 0
    for r in rows:
        reg = r["tail"].strip().upper()
        ata = _ata(r.get("ata_code"), known)
        snag_id = session.execute(
            pg_insert(Snag)
            .values(
                tail=reg,
                source="client",
                source_doc_id=(r.get("work_order_id") or f"{reg}-{r['occurred_at']}").strip(),
                occurred_at=_dt(r["occurred_at"]),
                raw_text=r["text"].strip(),
                ata_code=ata,
                ata_source="techlog" if ata else None,
                aircraft_type=tails[reg]["aircraft_type"],
                ingest_run_id=run_id,
            )
            .on_conflict_do_nothing(index_elements=["source", "source_doc_id"])
            .returning(Snag.id)
        ).scalar()
        if snag_id is None:
            continue
        session.add(
            DefectEvent(
                snag_id=snag_id,
                tail=reg,
                ata_code=ata,
                severity="S1",
                opened_at=_dt(r["occurred_at"]),
                closed_at=_dt(r.get("closed_at")),
                work_order_id=(r.get("work_order_id") or None),
            )
        )
        n += 1
    session.flush()
    return n


def load_csv(path: Path, session: Session) -> int:
    rows = read_rows(path)
    run = record_run(session, source="client", source_url=path.resolve().as_uri(), payload=path.read_bytes(), rows=len(rows))
    return load_rows(rows, session, run.id)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    with SessionLocal() as db:
        n = load_csv(Path(sys.argv[1]), db)
        db.commit()
    print(f"[client] {n} snags loaded")
