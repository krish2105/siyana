from datetime import datetime, timezone
from types import SimpleNamespace

from services.daleel.judge import ClaudeJudge, EmbeddingJudge, Verdict, format_neighbours
from services.daleel.retrieve import Neighbour


def _n(i, text, dist):
    return Neighbour(id=i, text=text, norm_text=text, tail=f"N{i}", occurred_at=datetime(2025, 1, 1, tzinfo=timezone.utc), work_order_id=f"WO{i}", ata_code="7200", distance=dist)


def test_embedding_judge_recurrence_and_shape():
    j = EmbeddingJudge(threshold=0.8)
    v = j.judge("ENGINE 2 VIBRATION ON CLIMB", [_n(1, "ENGINE VIBRATION CLIMB", 0.1), _n(2, "GEAR SHIMMY", 0.7)])
    assert isinstance(v, Verdict)
    assert v.is_recurrence and v.matched_ids == [1]
    assert len(v.signature.split()) <= 12 and 0 <= v.confidence <= 1
    v2 = j.judge("ENGINE 2 VIBRATION", [_n(2, "GEAR SHIMMY", 0.7)])
    assert not v2.is_recurrence and v2.matched_ids == []


def test_claude_judge_uses_parsed_output_and_filters_ids():
    verdict = Verdict(is_recurrence=True, matched_ids=[1, 99], signature="engine two n1 vibration during climb phase of flight extra words here", reasoning="same system same symptom", confidence=0.9)
    fake_messages = SimpleNamespace(parse=lambda **kw: SimpleNamespace(parsed_output=verdict))
    fake_client = SimpleNamespace(messages=fake_messages)
    j = ClaudeJudge(model="claude-sonnet-4-6", client=fake_client)
    out = j.judge("candidate", [_n(1, "x", 0.2)])
    assert out.matched_ids == [1]
    assert len(out.signature.split()) == 12
    assert j.model_version == "anthropic/claude-sonnet-4-6"


def test_claude_judge_without_neighbours_is_not_recurrence():
    j = ClaudeJudge(model="claude-sonnet-4-6", client=SimpleNamespace(messages=None))
    assert j.judge("ENGINE VIBRATION", []).is_recurrence is False


def test_format_neighbours():
    assert format_neighbours([_n(7, "TEXT", 0.1)]).startswith("[7] TEXT")
