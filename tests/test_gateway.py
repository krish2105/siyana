import pytest
from fastapi.testclient import TestClient

from services.common.db import db_reachable
from services.gateway.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


@pytest.mark.db
def test_zones_shape():
    if not db_reachable():
        pytest.skip("db")
    r = client.get("/fleet/zones")
    assert r.status_code == 200
    for z in r.json():
        assert {"chapter", "title", "open_count", "max_severity_rank", "recurring", "tails"} <= set(z)


@pytest.mark.db
def test_summary_states_open_window():
    if not db_reachable():
        pytest.skip("db")
    r = client.get("/fleet/summary")
    assert r.status_code == 200 and r.json()["open_window_days"] == 90
