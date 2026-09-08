from pathlib import Path

import pytest

from ingest.adapters.client_techlog import COLUMNS, read_rows
from ingest.asrs import is_maintenance_report, to_snag_values
from ingest.cmapss import COLUMNS as CMAPSS_COLUMNS
from ingest.cmapss import parse_txt

FIX = Path(__file__).parent / "fixtures"


def test_cmapss_parse_columns():
    text = "1 1 -0.0007 -0.0004 100.0 518.67 641.82 1589.70 1400.60 14.62 21.61 554.36 2388.06 9046.19 1.30 47.47 521.66 2388.02 8138.62 8.4195 0.03 392 2388 100.00 39.06 23.4190\n" * 5
    df = parse_txt(text)
    assert list(df.columns) == CMAPSS_COLUMNS
    assert len(df) == 5 and df.unit.dtype.kind == "i"
    assert list(parse_txt("112\n98\n", rul=True)) == [112, 98]


def test_client_adapter_reads_contract_columns():
    rows = read_rows(FIX / "client_techlog_sample.csv")
    assert len(rows) == 3
    assert set(COLUMNS) <= set(rows[0].keys())


def test_client_adapter_rejects_missing_text_column():
    with pytest.raises(ValueError, match="text"):
        read_rows(FIX / "client_techlog_missing_text.csv")


def test_asrs_mapping():
    rec = {
        "acn_num_ACN": 1234,
        "Time_Date": "202408",
        "Aircraft 1.2_Make Model Name": "B737-800",
        "Component_Aircraft Component": "Hydraulic System",
        "Report 1_Narrative": "During the walkaround we found hydraulic fluid leaking from the left main gear actuator.",
    }
    assert is_maintenance_report(rec)
    v = to_snag_values(rec)
    assert v["source"] == "asrs" and v["source_doc_id"] == "1234"
    assert v["aircraft_type"] == "B737" and v["occurred_at"].year == 2024
    assert not is_maintenance_report({"Report 1_Narrative": "ATC handoff issue", "Person 1.3_Function": "Enroute"})


def test_mvtec_layout():
    from ingest.mvtec import layout_path, select_samples

    samples = [
        {"filepath": "data/data_0/001.png", "category": {"label": "grid"}, "defect": {"label": "good"}, "split": "train"},
        {"filepath": "data/data_1/009-101.png", "category": {"label": "grid"}, "defect": {"label": "thread"}, "split": "test",
         "defect_mask": {"mask_path": "fields/defect_mask/defect_mask_12/009_mask-71.png"}},
        {"filepath": "data/data_2/002.png", "category": {"label": "pill"}, "defect": {"label": "good"}, "split": "train"},
    ]
    chosen = select_samples(samples, ("grid",))
    assert len(chosen) == 2
    img, mask = layout_path(chosen[1], Path("/tmp/mv"))
    assert img.as_posix() == "/tmp/mv/grid/test/thread/009-101.png"
    assert mask.as_posix() == "/tmp/mv/grid/ground_truth/thread/009-101_mask.png"
    assert layout_path(chosen[0], Path("/tmp/mv"))[1] is None
