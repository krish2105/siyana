"""NASA ASRS narratives via the Hugging Face mirror elihoole/asrs-aviation-reports (Apache-2.0).

Only maintenance-relevant reports are kept: a named aircraft component, a component problem,
or a reporter whose function is maintenance. Narratives become snags(source='asrs') with no
ATA code; DALEEL classifies them.

Run: .venv/bin/python -m ingest.asrs
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import hf_hub_download
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ingest.common import aircraft_family, record_run
from services.common.db import SessionLocal
from services.common.models import Snag

REPO = "elihoole/asrs-aviation-reports"
SPLITS = ("train", "validation", "test")
MAINT_FUNCTIONS = ("Technician", "Maintenance", "Inspector", "Lead Technician")


def is_maintenance_report(rec: dict) -> bool:
    if rec.get("Component_Aircraft Component") or rec.get("Component.3_Problem"):
        return True
    fn = (rec.get("Person 1.3_Function") or "") + " " + (rec.get("Person 2.3_Function") or "")
    if any(k.lower() in fn.lower() for k in MAINT_FUNCTIONS):
        return True
    return bool(rec.get("Aircraft 1.16_Maintenance Status.Maintenance Type"))


def to_snag_values(rec: dict) -> dict | None:
    narrative = (rec.get("Report 1_Narrative") or "").strip()
    if len(narrative) < 40:
        return None
    ym = str(rec.get("Time_Date") or "")
    occurred = None
    if len(ym) == 6 and ym.isdigit():
        occurred = datetime(int(ym[:4]), int(ym[4:]), 1, tzinfo=timezone.utc)
    component = rec.get("Component_Aircraft Component") or None
    return {
        "tail": None,
        "source": "asrs",
        "source_doc_id": str(rec.get("acn_num_ACN")),
        "occurred_at": occurred,
        "raw_text": narrative[:8000],
        "ata_code": None,
        "ata_source": None,
        "defect_type": None,
        "part_name": component,
        "aircraft_type": aircraft_family(rec.get("Aircraft 1.2_Make Model Name")),
    }


def load_split(split: str) -> tuple[list[dict], Path]:
    path = Path(hf_hub_download(REPO, f"asrs-aviation-reports-{split}.jsonl", repo_type="dataset"))
    rows: list[dict] = []
    with path.open() as f:
        for line in f:
            rec = json.loads(line)
            if not is_maintenance_report(rec):
                continue
            v = to_snag_values(rec)
            if v:
                rows.append(v)
    return rows, path


def pull() -> int:
    total = 0
    for split in SPLITS:
        rows, path = load_split(split)
        with SessionLocal() as db:
            run = record_run(
                db,
                source="asrs",
                source_url=f"https://huggingface.co/datasets/{REPO}/resolve/main/{path.name}",
                payload=path.read_bytes(),
                rows=len(rows),
            )
            for v in rows:
                v["ingest_run_id"] = run.id
            n = 0
            for i in range(0, len(rows), 500):
                res = db.execute(
                    pg_insert(Snag).values(rows[i : i + 500]).on_conflict_do_nothing(index_elements=["source", "source_doc_id"])
                )
                n += res.rowcount
            db.commit()
        print(f"[asrs] {split}: {len(rows)} maintenance reports, {n} new", flush=True)
        total += n
    return total


if __name__ == "__main__":
    print(f"[asrs] done: {pull()} new snags")
