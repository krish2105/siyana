"""Sentence embeddings for snags (all-MiniLM-L6-v2, 384 dims) written to snags.embedding."""
from __future__ import annotations

import os

import numpy as np
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from services.common.config import settings
from services.common.models import Snag
from services.daleel.normalise import normalise

EMBED_VERSION = f"{settings.embedding_model}@384"


class Embedder:
    """all-MiniLM-L6-v2 through sentence-transformers (torch) or, with SIYANA_EMBED_BACKEND=fastembed,
    through ONNX Runtime. Both produce the same 384-d normalised vectors (cosine 1.000 on spot checks);
    the ONNX path needs about a third of the memory, which is what a 512 MB host can afford."""

    _model = None
    _backend: str | None = None

    def __init__(self, model_name: str = settings.embedding_model):
        backend = os.environ.get("SIYANA_EMBED_BACKEND", "torch")
        if Embedder._model is None or Embedder._backend != backend:
            if backend == "fastembed":
                from fastembed import TextEmbedding

                Embedder._model = TextEmbedding(model_name)
            else:
                from sentence_transformers import SentenceTransformer

                Embedder._model = SentenceTransformer(model_name, device="cpu")
            Embedder._backend = backend
        self.model = Embedder._model
        self.backend = backend
        self.model_version = EMBED_VERSION

    def encode(self, texts: list[str]) -> np.ndarray:
        if self.backend == "fastembed":
            vecs = np.asarray(list(self.model.embed(texts, batch_size=64)), dtype=np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / np.maximum(norms, 1e-12)
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
