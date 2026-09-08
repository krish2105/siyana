from services.common import models
from services.common.evidence import write_evidence
from services.common.hashing import sha256_bytes, sha256_text


def test_sha256_text_is_stable():
    assert sha256_text("ENG 2 N1 VIB") == sha256_text("ENG 2 N1 VIB")
    assert len(sha256_text("x")) == 64
    assert sha256_bytes(b"x") == sha256_text("x")


def test_evidence_row_shape(db_session):
    eid = write_evidence(
        db_session, module="daleel", model_version="test/0", payload="abc", confidence=0.5, source_ids=[1, 2]
    )
    row = db_session.get(models.Evidence, eid)
    assert row.input_sha256 == sha256_text("abc")
    assert row.source_ids == [1, 2]
    assert row.module == "daleel"


def test_evidence_confidence_is_clamped(db_session):
    eid = write_evidence(db_session, module="ajal", model_version="t", payload=b"\x00", confidence=1.7, source_ids=[])
    assert db_session.get(models.Evidence, eid).confidence == 1.0
