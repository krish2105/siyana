"""4-digit ATA chapter classifier for free-text snags.

TF-IDF (word 1-2 grams + char 3-5 grams) with logistic regression, trained on SDRS records whose
JASC code gives a known ATA chapter. Chapter-level (2-digit) accuracy is also reported because
section-level labels in SDRS are noisy.

Run: .venv/bin/python -m services.daleel.ata_classifier   -> data/models/ata_clf.joblib, data/metrics/daleel_ata.json
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.common.config import settings
from services.common.models import Snag
from services.daleel.normalise import normalise

MODEL_VERSION = "ata-clf/tfidf-lr/2026-09"
MODEL_PATH = settings.models_dir / "ata_clf.joblib"
METRICS_PATH = settings.metrics_dir / "daleel_ata.json"
MIN_PER_CLASS = 40


def build_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                FeatureUnion(
                    [
                        ("word", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=200_000)),
                        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True, max_features=200_000)),
                    ]
                ),
            ),
            ("clf", LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced")),
        ]
    )


def fetch_training_frame(session: Session) -> tuple[list[str], list[str]]:
    rows = session.execute(
        select(Snag.raw_text, Snag.ata_code).where(Snag.source == "sdrs", Snag.ata_code.is_not(None))
    ).all()
    texts = [normalise(t).text for t, _ in rows]
    labels = [c for _, c in rows]
    return texts, labels


def train_from_arrays(texts: list[str], labels: list[str], *, min_per_class: int = MIN_PER_CLASS, seed: int = 7) -> tuple[Pipeline, dict]:
    counts = Counter(labels)
    keep = [i for i, c in enumerate(labels) if counts[c] >= min_per_class]
    X = [texts[i] for i in keep]
    y = [labels[i] for i in keep]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)
    pipe = build_pipeline()
    pipe.fit(X_tr, y_tr)
    pred = pipe.predict(X_te)
    top20 = [c for c, _ in Counter(y).most_common(20)]
    mask = np.isin(y_te, top20)
    y_te_a = np.array(y_te)
    majority = Counter(y_tr).most_common(1)[0][0]
    nb = Pipeline([("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3)), ("nb", ComplementNB())]).fit(X_tr, y_tr)
    nb_pred = nb.predict(X_te)
    chapter = lambda arr: np.array([c[:2] for c in arr])  # noqa: E731
    metrics = {
        "model_version": MODEL_VERSION,
        "n_train": len(X_tr),
        "n_test": len(X_te),
        "n_classes": len(set(y)),
        "top20_classes": top20,
        "macro_f1_top20": float(f1_score(y_te_a[mask], pred[mask], average="macro", labels=top20)),
        "macro_f1_all": float(f1_score(y_te, pred, average="macro")),
        "accuracy_4digit": float(accuracy_score(y_te, pred)),
        "accuracy_chapter": float(accuracy_score(chapter(y_te_a), chapter(pred))),
        "baselines": {
            "majority_class": {"label": majority, "accuracy_4digit": float(np.mean(y_te_a == majority)), "macro_f1_top20": float(f1_score(y_te_a[mask], np.full(mask.sum(), majority), average="macro", labels=top20))},
            "char_ngram_complement_nb": {"accuracy_4digit": float(accuracy_score(y_te, nb_pred)), "macro_f1_top20": float(f1_score(y_te_a[mask], nb_pred[mask], average="macro", labels=top20))},
        },
    }
    return pipe, metrics


def train(session: Session) -> dict:
    texts, labels = fetch_training_frame(session)
    pipe, metrics = train_from_arrays(texts, labels)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    return metrics


class AtaClassifier:
    def __init__(self, path: Path = MODEL_PATH):
        self.pipe: Pipeline = joblib.load(path)
        self.model_version = MODEL_VERSION

    def predict(self, text: str) -> tuple[str, float]:
        norm = normalise(text).text
        proba = self.pipe.predict_proba([norm])[0]
        i = int(np.argmax(proba))
        return str(self.pipe.classes_[i]), float(proba[i])


if __name__ == "__main__":
    from services.common.db import SessionLocal

    with SessionLocal() as db:
        m = train(db)
    print(json.dumps({k: v for k, v in m.items() if k != "top20_classes"}, indent=2))
