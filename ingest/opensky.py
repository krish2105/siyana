"""OpenSky Network live state vectors as a utilisation proxy.

Anonymous access to /api/states/all is rate limited (about 400 credits/day); one pull over the
India bounding box is a few hundred aircraft. Stored in utilisation with the ingest run id.

Run: .venv/bin/python -m ingest.opensky
"""
from __future__ import annotations

import json

from ingest.common import http_get_with_retry, record_run
from services.common.db import SessionLocal
from services.common.models import Utilisation

INDIA_BBOX = {"lamin": 6.5, "lomin": 68.0, "lamax": 37.5, "lomax": 97.5}
URL = "https://opensky-network.org/api/states/all"


def fetch_states(bbox: dict[str, float] = INDIA_BBOX) -> tuple[list[dict], bytes]:
    r = http_get_with_retry(URL, params=bbox, timeout=60)
    payload = r.content
    data = json.loads(payload)
    out = []
    for s in data.get("states") or []:
        out.append(
            {
                "icao24": s[0],
                "callsign": (s[1] or "").strip() or None,
                "origin_country": s[2],
                "velocity": s[9],
                "baro_altitude": s[7],
                "on_ground": s[8],
            }
        )
    return out, payload


def pull() -> int:
    states, payload = fetch_states()
    with SessionLocal() as db:
        run = record_run(db, source="opensky", source_url=URL, payload=payload, rows=len(states))
        db.add_all([Utilisation(**s, ingest_run_id=run.id) for s in states])
        db.commit()
    print(f"[opensky] {len(states)} state vectors over India", flush=True)
    return len(states)


if __name__ == "__main__":
    pull()
