import numpy as np
import pytest

from services.common.models import Snag
from services.daleel.retrieve import neighbours


@pytest.mark.db
def test_neighbours_filters_by_chapter_and_type(db_session):
    rng = np.random.default_rng(1)
    base = rng.normal(size=384).astype(np.float32)
    base /= np.linalg.norm(base)
    far = -base
    rows = [
        Snag(source="test", source_doc_id="a", raw_text="ENGINE VIBRATION", ata_code="7200", aircraft_type="A320", embedding=base.tolist()),
        Snag(source="test", source_doc_id="b", raw_text="ENGINE ROUGH RUNNING", ata_code="7250", aircraft_type="A320", embedding=(base + 0.01 * rng.normal(size=384)).tolist()),
        Snag(source="test", source_doc_id="c", raw_text="GEAR SHIMMY", ata_code="3200", aircraft_type="A320", embedding=far.tolist()),
        Snag(source="test", source_doc_id="d", raw_text="ENGINE VIBRATION 737", ata_code="7200", aircraft_type="B737", embedding=base.tolist()),
    ]
    db_session.add_all(rows)
    db_session.flush()
    out = neighbours(db_session, base, ata_code="7200", aircraft_type="A320", k=20, exclude_id=rows[0].id)
    ids = {n.id for n in out}
    assert rows[1].id in ids
    assert rows[2].id not in ids
    assert rows[3].id not in ids
    assert out[0].similarity > 0.5
