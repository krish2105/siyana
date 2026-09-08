"""Stable hashes used for evidence rows and ingest run records."""
from __future__ import annotations

import hashlib


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))
