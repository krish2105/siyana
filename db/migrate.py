"""Apply db/migrations/*.sql in order and seed reference tables.

Run: .venv/bin/python db/migrate.py
Idempotent: applied files are recorded in schema_migrations and skipped next time.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.common.db import engine  # noqa: E402

MIGRATIONS = Path(__file__).parent / "migrations"
SEED = Path(__file__).parent / "seed"


def apply_migrations() -> list[str]:
    applied: list[str] = []
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
        )
        done = {r[0] for r in conn.execute(text("SELECT filename FROM schema_migrations"))}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in done:
                continue
            conn.execute(text(path.read_text()))
            conn.execute(text("INSERT INTO schema_migrations(filename) VALUES (:f)"), {"f": path.name})
            applied.append(path.name)
    return applied


def seed_ata_chapters() -> int:
    rows = list(csv.DictReader((SEED / "ata_chapters.csv").open()))
    with engine.begin() as conn:
        for r in rows:
            conn.execute(
                text(
                    "INSERT INTO ata_chapters(code, chapter, title, system) "
                    "VALUES (:code, :chapter, :title, :system) "
                    "ON CONFLICT (code) DO UPDATE SET title = EXCLUDED.title, system = EXCLUDED.system"
                ),
                r,
            )
    return len(rows)


if __name__ == "__main__":
    applied = apply_migrations()
    n = seed_ata_chapters()
    print(f"migrations applied: {applied or 'none (up to date)'}")
    print(f"ata_chapters seeded: {n}")
