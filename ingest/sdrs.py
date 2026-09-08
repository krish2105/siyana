"""FAA Service Difficulty Reporting System adapter.

The FAA bulk download host (av-info.faa.gov/sdrx) is offline as of 2026-09-09, so this
adapter drives the public query form at https://sdrs.faa.gov/Query.aspx:

  1. GET the form, capture the ASP.NET __VIEWSTATE fields.
  2. POST a Difficulty Date window and 'Run Query'.
  3. POST 'Download' with every result row selected. The server returns an
     application/vnd.ms-excel payload that is an HTML table with 76 columns including
     the free-text Discrepancy.
  4. Parse rows, upsert tails, snags(source='sdrs') and defect_events.

Run: .venv/bin/python -m ingest.sdrs --from 2024-01-01 --to 2025-12-31 [--days 7]
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ingest.common import USER_AGENT, aircraft_family, record_run
from services.common.db import SessionLocal
from services.common.models import AtaChapter, DefectEvent, Snag, Tail

QUERY_URL = "https://sdrs.faa.gov/Query.aspx"
PREFIX = "ctl00$pageContentPlaceHolder$"


class SdrsRecord(BaseModel):
    control_number: str
    difficulty_date: date | None
    submission_date: date | None
    operator_designator: str | None
    jasc_code: str | None
    registry_n_number: str | None
    aircraft_make: str | None
    aircraft_model: str | None
    engine_make: str | None
    engine_model: str | None
    part_name: str | None
    part_number: str | None
    part_condition: str | None
    part_location: str | None
    nature_of_condition: str | None
    stage_of_operation: str | None
    how_discovered: str | None
    crack_length: str | None
    number_of_cracks: str | None
    corrosion_level: str | None
    discrepancy: str
    raw: dict[str, str] = Field(default_factory=dict)


def _date(s: str | None) -> date | None:
    if not s:
        return None
    head = s.strip().split(" ")[0]  # export dates look like '1/6/2025 0:00:00'
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(head, fmt).date()
        except ValueError:
            continue
    return None


def _clean(s: str | None) -> str | None:
    if s is None:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def parse_export(html: str | bytes) -> list[SdrsRecord]:
    """Parse the Download export (an HTML table) into records. Rows without a Discrepancy are dropped."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return []
    header = [th.get_text(strip=True) for th in table.find_all("th")]
    if "Discrepancy" not in header:
        raise ValueError(f"unexpected export header: {header[:8]}")
    out: list[SdrsRecord] = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        cells = [td.get_text(" ", strip=True) for td in tds]
        row = dict(zip(header, cells, strict=False))
        disc = _clean(row.get("Discrepancy"))
        if not disc or not row.get("OperatorControlNumber"):
            continue
        out.append(
            SdrsRecord(
                control_number=row["OperatorControlNumber"].strip(),
                difficulty_date=_date(row.get("DifficultyDate")),
                submission_date=_date(row.get("SubmissionDate")),
                operator_designator=_clean(row.get("OperatorDesignator")),
                jasc_code=_clean(row.get("JASCCode")),
                registry_n_number=_clean(row.get("RegistryNNumber")),
                aircraft_make=_clean(row.get("AircraftMake")),
                aircraft_model=_clean(row.get("AircraftModel")),
                engine_make=_clean(row.get("EngineMake")),
                engine_model=_clean(row.get("EngineModel")),
                part_name=_clean(row.get("PartName")),
                part_number=_clean(row.get("PartNumber")),
                part_condition=_clean(row.get("PartCondition")),
                part_location=_clean(row.get("PartLocation")),
                nature_of_condition=_clean(row.get("NatureOfConditionA")),
                stage_of_operation=_clean(row.get("StageOfOperationCode")),
                how_discovered=_clean(row.get("HowDiscoveredCode")),
                crack_length=_clean(row.get("CrackLength")),
                number_of_cracks=_clean(row.get("NumberOfCracks")),
                corrosion_level=_clean(row.get("CorrosionLevel")),
                discrepancy=disc,
                raw=row,
            )
        )
    return out


def _form_fields(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    return {i.get("name"): i.get("value", "") or "" for i in soup.find_all("input") if i.get("name")}


def _state(fields: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in fields.items() if k.startswith("__") or k == "ctl00$welcomeText$hdnAnonymous"}


def fetch_window(start: date, end: date, *, session: requests.Session | None = None, timeout: int = 300) -> tuple[list[SdrsRecord], bytes]:
    """Query [start, end] inclusive and return (records, raw export bytes)."""
    s = session or requests.Session()
    s.headers.setdefault("User-Agent", USER_AGENT)
    form = s.get(QUERY_URL, timeout=60)
    form.raise_for_status()
    fields = _form_fields(form.text)
    data = _state(fields)
    for k in fields:
        if k.startswith(PREFIX + "tb"):
            data[k] = ""
    data[PREFIX + "tbDifficultyDateFrom"] = start.strftime("%m/%d/%Y")
    data[PREFIX + "tbDifficultyDateTo"] = end.strftime("%m/%d/%Y")
    data[PREFIX + "btnQuery"] = "Run Query"
    results = s.post(QUERY_URL, data=data, timeout=timeout)
    results.raise_for_status()
    if "Your query returned no results" in results.text:
        return [], results.content
    rf = _form_fields(results.text)
    dl = _state(rf)
    selected = [k for k in rf if k.endswith("$cbSelected")]
    for k in selected:
        dl[k] = "on"
    dl[PREFIX + "dgQueryResults$ctl01$cbSelectAll"] = "on"
    dl[PREFIX + "btnDownload"] = "Download"
    export = s.post(QUERY_URL, data=dl, timeout=timeout)
    export.raise_for_status()
    if "vnd.ms-excel" not in export.headers.get("Content-Type", ""):
        raise RuntimeError(f"SDRS download did not return an export (content-type {export.headers.get('Content-Type')})")
    return parse_export(export.content), export.content


def jasc_to_ata(jasc: str | None, known: set[str]) -> str | None:
    """JASC codes are ATA Spec 100 chapter+section. Fall back to the chapter's 00 code."""
    if not jasc:
        return None
    code = re.sub(r"\D", "", jasc)[:4]
    if len(code) < 2:
        return None
    if code in known:
        return code
    chapter = code[:2] + "00"
    return chapter if chapter in known else None


_DEFECT_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bCRACK"), "crack"),
    (re.compile(r"\bCORRO"), "corrosion"),
    (re.compile(r"\bDENT|\bDAMAGE[D]?\b.*\bSKIN"), "dent"),
    (re.compile(r"\bDELAM|\bDISBOND"), "delamination"),
    (re.compile(r"\bMISSING\b.*\b(FASTENER|RIVET|SCREW|BOLT)|\b(FASTENER|RIVET|SCREW|BOLT)S?\b.*\bMISSING"), "missing-fastener"),
    (re.compile(r"\bLEAK"), "leak"),
    (re.compile(r"\bCHAF|\bWORN|\bWEAR\b"), "wear"),
    (re.compile(r"\bVIB"), "vibration"),
    (re.compile(r"\bINOP|\bFAIL|\bFAULT"), "failure"),
]


def defect_type(text: str) -> str:
    t = text.upper()
    for pattern, label in _DEFECT_RULES:
        if pattern.search(t):
            return label
    return "other"


def severity_prior(rec: SdrsRecord) -> str:
    """Triage prior from structured SDR fields. Not an airworthiness determination."""
    if rec.number_of_cracks or rec.crack_length:
        return "S3"
    if rec.corrosion_level:
        return "S2"
    if rec.stage_of_operation and rec.stage_of_operation.upper() in {"CL", "CR", "DE", "TO", "AP", "LD"}:
        return "S2"
    return "S1"


def load(records: list[SdrsRecord], session: Session, run_id: int | None) -> int:
    known = {c for (c,) in session.execute(select(AtaChapter.code))}
    tails: dict[str, dict] = {}
    for r in records:
        if r.registry_n_number:
            reg = "N" + r.registry_n_number.upper().lstrip("N")
            tails.setdefault(reg, {"registration": reg, "aircraft_type": aircraft_family(r.aircraft_model), "operator": r.operator_designator})
    if tails:
        stmt = pg_insert(Tail).values(list(tails.values()))
        session.execute(stmt.on_conflict_do_nothing(index_elements=["registration"]))
    inserted = 0
    for r in records:
        reg = ("N" + r.registry_n_number.upper().lstrip("N")) if r.registry_n_number else None
        occurred = datetime.combine(r.difficulty_date, datetime.min.time(), tzinfo=timezone.utc) if r.difficulty_date else None
        snag_stmt = (
            pg_insert(Snag)
            .values(
                tail=reg,
                source="sdrs",
                source_doc_id=r.control_number,
                occurred_at=occurred,
                raw_text=r.discrepancy,
                ata_code=jasc_to_ata(r.jasc_code, known),
                ata_source="jasc",
                defect_type=defect_type(r.discrepancy),
                part_name=r.part_name,
                part_number=r.part_number,
                aircraft_type=aircraft_family(r.aircraft_model),
                ingest_run_id=run_id,
            )
            .on_conflict_do_nothing(index_elements=["source", "source_doc_id"])
            .returning(Snag.id)
        )
        snag_id = session.execute(snag_stmt).scalar()
        if snag_id is None:
            continue
        session.add(
            DefectEvent(
                snag_id=snag_id,
                tail=reg,
                ata_code=jasc_to_ata(r.jasc_code, known),
                severity=severity_prior(r),
                opened_at=occurred,
                work_order_id=r.control_number[-8:],
            )
        )
        inserted += 1
    session.flush()
    return inserted


def pull(start: date, end: date, *, step_days: int = 7, pause_s: float = 3.0) -> int:
    total = 0
    http = requests.Session()
    http.headers["User-Agent"] = USER_AGENT
    cur = start
    while cur <= end:
        win_end = min(cur + timedelta(days=step_days - 1), end)
        try:
            records, payload = fetch_window(cur, win_end, session=http)
        except (requests.RequestException, RuntimeError) as e:
            print(f"[sdrs] {cur}..{win_end} FAILED: {e}", file=sys.stderr)
            print(f"[sdrs] retry with: .venv/bin/python -m ingest.sdrs --from {cur} --to {win_end}", file=sys.stderr)
            raise SystemExit(2)
        with SessionLocal() as db:
            run = record_run(db, source="sdrs", source_url=f"{QUERY_URL}?from={cur}&to={win_end}", payload=payload, rows=len(records))
            n = load(records, db, run.id)
            db.commit()
        total += n
        print(f"[sdrs] {cur}..{win_end}: {len(records)} exported, {n} new", flush=True)
        cur = win_end + timedelta(days=1)
        time.sleep(pause_s)
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Pull FAA SDRS records into Postgres")
    ap.add_argument("--from", dest="start", required=True, type=date.fromisoformat)
    ap.add_argument("--to", dest="end", required=True, type=date.fromisoformat)
    ap.add_argument("--days", type=int, default=7, help="window size per request")
    a = ap.parse_args()
    n = pull(a.start, a.end, step_days=a.days)
    print(f"[sdrs] done: {n} new snags")
