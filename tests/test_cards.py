import pytest

from services.common.evidence import write_evidence
from services.common.models import Approval, DefectEvent, Signature, Snag, Tail
from services.daleel.cards import approve_card, draft_card


def _seed(db):
    db.add(Tail(registration="N1TEST", aircraft_type="A320"))
    db.flush()
    s1 = Snag(source="test", source_doc_id="c1", raw_text="ENG 2 N1 VIB ON CLB", ata_code="7200", aircraft_type="A320", tail="N1TEST")
    s2 = Snag(source="test", source_doc_id="c2", raw_text="NO.2 ENGINE ROUGH RUNNING", ata_code="7200", aircraft_type="A320", tail="N1TEST")
    db.add_all([s1, s2])
    db.flush()
    db.add_all([DefectEvent(snag_id=s1.id, tail="N1TEST", ata_code="7200", work_order_id="WO1"), DefectEvent(snag_id=s2.id, tail="N1TEST", ata_code="7200", work_order_id="WO2")])
    eid = write_evidence(db, module="daleel", model_version="t", payload="x", confidence=0.9, source_ids=[s1.id, s2.id])
    sig = Signature(ata_code="7200", aircraft_type="A320", canonical="engine 2 vibration on climb", member_snag_ids=[s1.id, s2.id], count=2, evidence_id=eid)
    db.add(sig)
    db.flush()
    return sig


@pytest.mark.db
def test_draft_card_is_draft_with_citations_and_evidence(db_session):
    sig = _seed(db_session)
    card = draft_card(db_session, sig.id, "test-judge/0")
    assert card.status == "DRAFT"
    assert card.body["work_order_ids"] == ["WO1", "WO2"]
    assert len(card.body["source_snags"]) == 2
    assert card.evidence_id is not None
    assert "not a maintenance instruction" in card.body["disclaimer"].lower()


@pytest.mark.db
def test_approval_requires_licence_and_is_logged(db_session):
    sig = _seed(db_session)
    card = draft_card(db_session, sig.id, "test-judge/0")
    with pytest.raises(ValueError, match="licence_number"):
        approve_card(db_session, card.id, engineer_name="A. Engineer", licence_number="", decision="APPROVED")
    approved = approve_card(db_session, card.id, engineer_name="A. Engineer", licence_number="DGCA-B1-12345", decision="APPROVED", note="ok")
    assert approved.status == "APPROVED"
    logged = db_session.query(Approval).filter_by(card_id=card.id).one()
    assert logged.licence_number == "DGCA-B1-12345"
    with pytest.raises(ValueError, match="already"):
        approve_card(db_session, card.id, engineer_name="B", licence_number="X-1", decision="REJECTED")
