from pathlib import Path

from ingest.common import aircraft_family
from ingest.sdrs import defect_type, jasc_to_ata, parse_export, severity_prior

FIXTURE = Path(__file__).parent / "fixtures" / "sdrs_export_sample.html"


def test_parse_export_extracts_rows():
    records = parse_export(FIXTURE.read_text())
    assert len(records) >= 15
    first = records[0]
    assert first.control_number
    assert first.discrepancy and len(first.discrepancy) > 20
    assert first.jasc_code and len(first.jasc_code) == 4
    assert first.difficulty_date is not None and first.difficulty_date.year == 2025
    assert first.raw["Discrepancy"].strip().startswith(first.discrepancy[:10])


def test_jasc_to_ata_falls_back_to_chapter():
    known = {"5300", "5330", "7200"}
    assert jasc_to_ata("5330", known) == "5330"
    assert jasc_to_ata("5399", known) == "5300"
    assert jasc_to_ata("9999", known) is None
    assert jasc_to_ata(None, known) is None


def test_defect_type_and_severity():
    assert defect_type("CRACK FOUND ON FRAME") == "crack"
    assert defect_type("CORROSION ON PLATES") == "corrosion"
    assert defect_type("RIVETS MISSING ON PANEL") == "missing-fastener"
    rec = parse_export(FIXTURE.read_text())[0]
    assert severity_prior(rec) in {"S1", "S2", "S3", "S4"}


def test_aircraft_family():
    assert aircraft_family("737-8H4") == "B737"
    assert aircraft_family("737800") == "B737"
    assert aircraft_family("A320-232") == "A320"
    assert aircraft_family("ERJ170100SE") == "E170"
    assert aircraft_family("CL6002D24") == "CRJ"
    assert aircraft_family(None) == "UNKNOWN"
