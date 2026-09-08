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


def test_request_id_header_and_ready_shape():
    r = client.get("/health")
    assert "x-request-id" in r.headers and r.json()["version"]
    if db_reachable():
        body = client.get("/health/ready").json()
        assert {"ready", "snags", "fleet_tails", "auth", "judge"} <= set(body)


def test_api_key_gate(monkeypatch):
    monkeypatch.setenv("SIYANA_API_KEY", "secret-1")
    r = client.post("/daleel/cards/1/approve", json={"engineer_name": "A B", "licence_number": "L-1", "decision": "APPROVED"})
    assert r.status_code == 401
    monkeypatch.delenv("SIYANA_API_KEY")


def test_rate_limit_on_judge(monkeypatch):
    from services.gateway import middleware

    middleware.RATE_LIMITED["/daleel/judge"] = (2, 60.0)
    middleware._buckets.clear()
    payload = {"text": "x" * 30}
    codes = [client.post("/daleel/judge", json=payload).status_code for _ in range(3)]
    middleware.RATE_LIMITED["/daleel/judge"] = (20, 60.0)
    middleware._buckets.clear()
    assert codes[-1] == 429
