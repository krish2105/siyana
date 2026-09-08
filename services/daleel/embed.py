"""Sentence embeddings for snags (all-MiniLM-L6-v2, 384 dims) written to snags.embedding."""
from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from services.common.config import settings
from services.common.models import Snag
from services.daleel.normalise import normalise

EMBED_VERSION = f"{settings.embedding_model}@384"


class Embedder:
    _model: SentenceTransformer | None = None

    def __init__(self, model_name: str = settings.embedding_model):
        if Embedder._model is None:
            Embedder._model = SentenceTransformer(model_name, device="cpu")
        self.model = Embedder._model
        self.model_version = EMBED_VERSION

    def encode(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)


def embed_all(session: Session, *, batch: int = 512, embedder: Embedder | None = None) -> int:
    emb = embedder or Embedder()
    done = 0
    while True:
        rows = session.execute(
            select(Snag.id, Snag.raw_text, Snag.norm_text).where(Snag.embedding.is_(None)).order_by(Snag.id).limit(batch)
        ).all()
        if not rows:
            break
        norms = [n or normalise(t).text for _, t, n in rows]
        vecs = emb.encode(norms)
        session.execute(
            update(Snag),
            [{"id": i, "norm_text": n, "embedding": v.tolist()} for (i, _, _), n, v in zip(rows, norms, vecs, strict=True)],
        )
        session.commit()
        done += len(rows)
        print(f"[embed] {done} snags embedded", flush=True)
    return done


if __name__ == "__main__":
    from services.common.db import SessionLocal

    with SessionLocal() as db:
        print(f"[embed] done: {embed_all(db)}")
