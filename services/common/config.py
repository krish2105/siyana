"""Runtime settings. Values come from the environment or a .env file at repo root."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL", "postgresql+psycopg2://siyana:siyana@localhost:5432/siyana"
        )
    )
    anthropic_api_key: str | None = field(
        default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY") or None
    )
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("SIYANA_DATA_DIR", REPO_ROOT / "data")).resolve()
    )
    judge_model: str = "claude-sonnet-4-6"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def metrics_dir(self) -> Path:
        return self.data_dir / "metrics"


settings = Settings()
