"""Recurrence evaluation on 300 hand-labelled SDRS pairs.

Pairs are sampled in three strata so the set has both hard positives and easy negatives:
  nn      100 nearest-neighbour pairs (same aircraft family, same chapter, cosine >= 0.6)
  chapter 100 random same-chapter, same-family pairs
  cross   100 random cross-chapter pairs
Labels: 1 = same underlying defect signature (system, symptom, condition align), 0 = not.
Labelled by reading each pair; the labeller is recorded in the CSV and in EVALUATION.md.

Run:
  .venv/bin/python -m services.daleel.eval build     -> data/labels/recurrence_pairs.csv (label column blank)
  .venv/bin/python -m services.daleel.eval evaluate  -> data/metrics/daleel_recurrence.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score, precision_score, recall_score
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.common.config import settings
from services.common.db import SessionLocal
from services.daleel.embed import Embedder
from services.daleel.judge import ClaudeJudge, EmbeddingJudge, Judge
from services.daleel.normalise import normalise
from services.daleel.retrieve import Neighbour

LABELS_PATH = settings.data_dir / "labels" / "recurrence_pairs.csv"
METRICS_PATH = settings.metrics_dir / "daleel_recurrence.json"
DEV_SIZE = 60


def build_pairs(session: Session, n_per_stratum: int = 100, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = """select s.id, s.norm_text, s.raw_text, s.ata_code, s.aircraft_type, s.tail
              from snags s where s.source='sdrs' and s.embedding is not null and s.ata_code is not null
              and s.aircraft_type in ('B737','A320','A321','E170','E190','CRJ') and length(s.raw_text) > 40"""
    pool = pd.read_sql(text(base + " order by random() limit 6000"), session.connection())
    pool["chapter"] = pool.ata_code.str[:2]
    rows = []
    # nn stratum: for random anchors, take their nearest same-chapter same-type neighbour above 0.6
    anchors = pool.sample(min(400, len(pool)), random_state=seed)
    for _, a in anchors.iterrows():
        r = session.execute(
            text(
                """select s.id, s.raw_text, 1 - (s.embedding <=> (select embedding from snags where id=:id)) as sim
                   from snags s where s.id <> :id and left(s.ata_code,2) = :ch and s.aircraft_type = :t and s.embedding is not null
                   order by s.embedding <=> (select embedding from snags where id=:id) limit 1"""
            ),
            {"id": int(a.id), "ch": a.chapter, "t": a.aircraft_type},
        ).first()
        if r and r.sim >= 0.6:
            rows.append(("nn", int(a.id), int(r.id), a.raw_text, r.raw_text, float(r.sim)))
        if sum(1 for x in rows if x[0] == "nn") >= n_per_stratum:
            break
    # chapter stratum
    grouped = pool.groupby(["chapter", "aircraft_type"])
    keys = [k for k, g in grouped if len(g) >= 2]
    while sum(1 for x in rows if x[0] == "chapter") < n_per_stratum:
        k = keys[rng.integers(len(keys))]
        g = grouped.get_group(k).sample(2, random_state=int(rng.integers(1 << 30)))
        a, b = g.iloc[0], g.iloc[1]
        rows.append(("chapter", int(a.id), int(b.id), a.raw_text, b.raw_text, None))
    # cross stratum
    while sum(1 for x in rows if x[0] == "cross") < n_per_stratum:
        a, b = pool.sample(2, random_state=int(rng.integers(1 << 30))).itertuples()
        if a.chapter != b.chapter:
            rows.append(("cross", int(a.id), int(b.id), a.raw_text, b.raw_text, None))
    df = pd.DataFrame(rows, columns=["stratum", "snag_a", "snag_b", "text_a", "text_b", "nn_similarity"])
    df.insert(0, "pair_id", range(1, len(df) + 1))
    df["label"] = ""
    df["labeller"] = ""
    return df


def _pair_neighbour(snag_id: int, txt: str, sim: float) -> Neighbour:
    return Neighbour(id=snag_id, text=txt, norm_text=normalise(txt).text, tail=None, occurred_at=None, work_order_id=None, ata_code=None, distance=1.0 - sim)


def _prf(y, p) -> dict:
    return {"precision": float(precision_score(y, p, zero_division=0)), "recall": float(recall_score(y, p, zero_division=0)), "f1": float(f1_score(y, p, zero_division=0)), "n": int(len(y))}


def _best_threshold(scores: np.ndarray, y: np.ndarray) -> float:
    best, best_f1 = 0.5, -1.0
    for th in np.linspace(0.1, 0.95, 86):
        f = f1_score(y, scores >= th, zero_division=0)
        if f > best_f1:
            best, best_f1 = float(th), f
    return best


def evaluate(judges: list[Judge] | None = None) -> dict:
    df = pd.read_csv(LABELS_PATH)
    df = df[df.label.isin([0, 1, "0", "1"])].copy()
    df["label"] = df.label.astype(int)
    if len(df) < 100:
        raise SystemExit(f"only {len(df)} labelled pairs in {LABELS_PATH}; label the CSV first")
    emb = Embedder()
    na = [normalise(t).text for t in df.text_a]
    nb_ = [normalise(t).text for t in df.text_b]
    va, vb = emb.encode(na), emb.encode(nb_)
    cos = np.sum(va * vb, axis=1)
    tf = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit(na + nb_)
    A, B = tf.transform(na), tf.transform(nb_)
    tfidf_cos = np.asarray(A.multiply(B).sum(axis=1)).ravel()

    rng = np.random.default_rng(11)
    idx = rng.permutation(len(df))
    dev, test = idx[:DEV_SIZE], idx[DEV_SIZE:]
    y = df.label.to_numpy()

    th_tfidf = _best_threshold(tfidf_cos[dev], y[dev])
    th_emb = _best_threshold(cos[dev], y[dev])
    results = {
        "n_pairs": int(len(df)),
        "n_dev": int(len(dev)),
        "n_test": int(len(test)),
        "positives_test": int(y[test].sum()),
        "strata": df.stratum.value_counts().to_dict(),
        "labeller": str(df.labeller.dropna().iloc[0]) if df.labeller.notna().any() else "",
        "models": {
            "tfidf_cosine": {"threshold": th_tfidf, **_prf(y[test], tfidf_cos[test] >= th_tfidf)},
            "embedding_cosine": {"threshold": th_emb, **_prf(y[test], cos[test] >= th_emb)},
        },
        "per_stratum": {},
    }
    for j in judges or [EmbeddingJudge()]:
        preds = []
        for i in range(len(df)):
            r = df.iloc[i]
            v = j.judge(na[i], [_pair_neighbour(int(r.snag_b), r.text_b, float(cos[i]))])
            preds.append(1 if v.is_recurrence else 0)
        preds = np.asarray(preds)
        key = "embedding_judge" if isinstance(j, EmbeddingJudge) else "claude_judge"
        results["models"][key] = {"model_version": j.model_version, **_prf(y[test], preds[test])}
        for st in df.stratum.unique():
            m = (df.stratum.to_numpy() == st)
            m_test = m[test]
            results["per_stratum"].setdefault(st, {})[key] = _prf(y[test][m_test], preds[test][m_test]) if m_test.any() else None
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "evaluate"
    if cmd == "build":
        with SessionLocal() as db:
            df = build_pairs(db)
        LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(LABELS_PATH, index=False)
        print(f"[eval] {len(df)} pairs -> {LABELS_PATH}")
    else:
        judges: list[Judge] = [EmbeddingJudge()]
        if settings.anthropic_api_key:
            judges.append(ClaudeJudge())
        res = evaluate(judges)
        for k, v in res["models"].items():
            print(f"{k:18s} P {v['precision']:.2f}  R {v['recall']:.2f}  F1 {v['f1']:.2f}")
