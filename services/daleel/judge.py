"""The recurrence judge. Decides whether a candidate snag is the SAME defect signature as any
retrieved neighbour. Two implementations share one interface:

- ClaudeJudge: claude-sonnet-4-6 via the Anthropic SDK with a validated structured output.
- EmbeddingJudge: cosine-similarity fallback used when no ANTHROPIC_API_KEY is configured, so
  every build step stays runnable. Its verdicts are stamped with their own model_version in the
  evidence table so nobody mistakes them for LLM verdicts.
"""
from __future__ import annotations

from typing import Protocol

import anthropic
from pydantic import BaseModel, Field, field_validator

from services.common.config import Settings, settings
from services.daleel.retrieve import Neighbour

JUDGE_PROMPT = """You are assisting a Part-145 certifying engineer.

CANDIDATE SNAG:
{candidate}

HISTORICAL SNAGS ON THE SAME AIRCRAFT TYPE AND ATA CHAPTER:
{neighbours}

Decide whether the candidate describes the SAME underlying defect signature as
any historical entry. Two entries match if the failing system, the symptom, and
the operating condition align, even if the wording differs completely.
Return matched_ids only for entries that match; an empty list means no recurrence.
signature: at most 12 words naming the canonical defect. reasoning: at most 40 words.
"""

EMBEDDING_THRESHOLD = 0.775  # tuned on the 60-pair dev split: highest recall with precision >= 0.90 (see EVALUATION.md)


class Verdict(BaseModel):
    is_recurrence: bool
    matched_ids: list[int] = Field(default_factory=list)
    signature: str = Field(description="canonical description, at most 12 words")
    reasoning: str = Field(description="at most 40 words")
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("signature")
    @classmethod
    def _trim_signature(cls, v: str) -> str:
        return " ".join(v.split()[:12])

    @field_validator("reasoning")
    @classmethod
    def _trim_reasoning(cls, v: str) -> str:
        return " ".join(v.split()[:40])


class Judge(Protocol):
    model_version: str

    def judge(self, candidate: str, neighbours: list[Neighbour]) -> Verdict: ...


def format_neighbours(neighbours: list[Neighbour]) -> str:
    return "\n".join(f"[{n.id}] {n.norm_text or n.text}" for n in neighbours) or "(none)"


class ClaudeJudge:
    def __init__(self, model: str = settings.judge_model, client: anthropic.Anthropic | None = None):
        self.model = model
        self.model_version = f"anthropic/{model}"
        self.client = client or anthropic.Anthropic()

    def judge(self, candidate: str, neighbours: list[Neighbour]) -> Verdict:
        if not neighbours:
            return Verdict(is_recurrence=False, matched_ids=[], signature=" ".join(candidate.split()[:12]), reasoning="No historical snags in this chapter for this type.", confidence=0.5)
        prompt = JUDGE_PROMPT.format(candidate=candidate, neighbours=format_neighbours(neighbours))
        response = self.client.messages.parse(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            output_format=Verdict,
        )
        verdict: Verdict = response.parsed_output
        valid = {n.id for n in neighbours}
        verdict.matched_ids = [i for i in verdict.matched_ids if i in valid]
        if verdict.is_recurrence and not verdict.matched_ids:
            verdict.is_recurrence = False
        return verdict


class EmbeddingJudge:
    """Deterministic fallback: a neighbour above the cosine threshold is a recurrence."""

    def __init__(self, threshold: float = EMBEDDING_THRESHOLD):
        self.threshold = threshold
        self.model_version = f"embedding-judge/all-MiniLM-L6-v2@cos>={threshold}"

    def judge(self, candidate: str, neighbours: list[Neighbour]) -> Verdict:
        matched = [n for n in neighbours if n.similarity >= self.threshold]
        if not matched:
            best = max((n.similarity for n in neighbours), default=0.0)
            return Verdict(
                is_recurrence=False,
                matched_ids=[],
                signature=" ".join(candidate.split()[:12]),
                reasoning=f"Best cosine similarity {best:.2f} below threshold {self.threshold}.",
                confidence=float(min(0.95, max(0.0, 1.0 - best))) if neighbours else 0.5,
            )
        top = max(matched, key=lambda n: n.similarity)
        return Verdict(
            is_recurrence=True,
            matched_ids=[n.id for n in matched],
            signature=" ".join((top.norm_text or top.text).split()[:12]),
            reasoning=f"{len(matched)} neighbour(s) at cosine >= {self.threshold}; best {top.similarity:.2f}.",
            confidence=float(min(1.0, max(0.0, top.similarity))),
        )


def get_judge(cfg: Settings = settings) -> Judge:
    if cfg.anthropic_api_key:
        return ClaudeJudge(model=cfg.judge_model, client=anthropic.Anthropic(api_key=cfg.anthropic_api_key))
    return EmbeddingJudge()
