"""Shared helpers for ingestion adapters: HTTP with retry, run records, paths."""
from __future__ import annotations

import re
import time
from pathlib import Path

import requests
from sqlalchemy.orm import Session

from services.common.config import settings
from services.common.hashing import sha256_bytes
from services.common.models import IngestRun

USER_AGENT = "SIYANA/0.1 (aircraft maintenance research; contact via repository)"


def data_path(*parts: str) -> Path:
    path = settings.data_dir.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def http_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def http_get_with_retry(url: str, *, attempts: int = 3, timeout: int = 60, **kwargs) -> requests.Response:
    last: Exception | None = None
    for i in range(attempts):
        try:
            r = http_session().get(url, timeout=timeout, **kwargs)
            if r.status_code < 500:
                r.raise_for_status()
                return r
            last = requests.HTTPError(f"{r.status_code} from {url}")
        except requests.RequestException as e:  # network, timeout
            last = e
        time.sleep(2 ** i)
    raise RuntimeError(f"GET {url} failed after {attempts} attempts: {last}")


def record_run(
    session: Session,
    *,
    source: str,
    source_url: str,
    payload: bytes,
    rows: int,
    status: str = "ok",
    detail: str | None = None,
) -> IngestRun:
    run = IngestRun(
        source=source,
        source_url=source_url,
        payload_sha256=sha256_bytes(payload),
        rows=rows,
        status=status,
        detail=detail,
    )
    session.add(run)
    session.flush()
    return run


_FAMILY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^(B)?7(3)7"), "B737"),
    (re.compile(r"^(B)?7(4)7"), "B747"),
    (re.compile(r"^(B)?7(5)7"), "B757"),
    (re.compile(r"^(B)?7(6)7"), "B767"),
    (re.compile(r"^(B)?7(7)7"), "B777"),
    (re.compile(r"^(B)?7(8)7"), "B787"),
    (re.compile(r"^A?318"), "A318"),
    (re.compile(r"^A?319"), "A319"),
    (re.compile(r"^A?320"), "A320"),
    (re.compile(r"^A?321"), "A321"),
    (re.compile(r"^A?330"), "A330"),
    (re.compile(r"^A?340"), "A340"),
    (re.compile(r"^A?350"), "A350"),
    (re.compile(r"^A?380"), "A380"),
    (re.compile(r"^(ERJ|EMB)?\s?-?1(70|75)"), "E170"),
    (re.compile(r"^(ERJ|EMB)?\s?-?1(90|95)"), "E190"),
    (re.compile(r"^(EMB|ERJ)?\s?-?145"), "ERJ145"),
    (re.compile(r"^CL[- ]?600"), "CRJ"),
    (re.compile(r"^CRJ"), "CRJ"),
    (re.compile(r"^DHC[- ]?8"), "DHC8"),
    (re.compile(r"^ATR"), "ATR"),
    (re.compile(r"^EC[- ]?135"), "EC135"),
    (re.compile(r"^EC[- ]?130"), "EC130"),
    (re.compile(r"^AS[- ]?350"), "AS350"),
    (re.compile(r"^MD[- ]?(11|80|82|83|88|90)"), "MD"),
    (re.compile(r"^C[- ]?208"), "C208"),
    (re.compile(r"^C[- ]?172"), "C172"),
    (re.compile(r"^PC[- ]?12"), "PC12"),
]


def aircraft_family(model: str | None) -> str:
    """Collapse manufacturer model strings ('737-8H4', 'A320-232', 'ERJ170100SE') to a family code."""
    if not model:
        return "UNKNOWN"
    m = model.strip().upper().replace(" ", "")
    for pattern, family in _FAMILY_RULES:
        if pattern.match(m):
            return family
    token = re.match(r"[A-Z0-9]{1,6}", m)
    return token.group(0) if token else "UNKNOWN"
