"""NASA C-MAPSS turbofan degradation data.

Source: https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip
(an outer zip holding CMAPSSData.zip with train_FD00x.txt, test_FD00x.txt, RUL_FD00x.txt).

Run: .venv/bin/python -m ingest.cmapss   -> data/processed/cmapss/{train,test,rul}_FD00x.parquet
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from ingest.common import data_path, http_get_with_retry, record_run
from services.common.db import SessionLocal, db_reachable

URL = "https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
COLUMNS = ["unit", "cycle", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)]
SUBSETS = ("FD001", "FD002", "FD003", "FD004")


def parse_txt(text: str, *, rul: bool = False) -> pd.DataFrame | pd.Series:
    if rul:
        return pd.Series([int(x) for x in text.split()], name="rul")
    df = pd.read_csv(io.StringIO(text), sep=r"\s+", header=None)
    df = df.iloc[:, : len(COLUMNS)]
    df.columns = COLUMNS
    df["unit"] = df["unit"].astype(int)
    df["cycle"] = df["cycle"].astype(int)
    return df


def ensure_zip() -> Path:
    target = data_path("raw", "cmapss", "CMAPSSData.zip")
    if not target.exists() or target.stat().st_size < 1_000_000:
        r = http_get_with_retry(URL, timeout=300)
        target.write_bytes(r.content)
    return target


def extract(zip_path: Path) -> dict[str, str]:
    outer = zipfile.ZipFile(zip_path)
    inner_name = next(n for n in outer.namelist() if n.endswith("CMAPSSData.zip"))
    inner = zipfile.ZipFile(io.BytesIO(outer.read(inner_name)))
    wanted = ("train_", "test_", "RUL_")
    return {n: inner.read(n).decode("ascii", errors="ignore") for n in inner.namelist() if n.endswith(".txt") and n.startswith(wanted)}


def load_fd(name: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    base = data_path("processed", "cmapss", "x").parent
    train = pd.read_parquet(base / f"train_{name}.parquet")
    test = pd.read_parquet(base / f"test_{name}.parquet")
    rul = pd.read_parquet(base / f"rul_{name}.parquet")["rul"]
    return train, test, rul


def pull() -> dict[str, int]:
    zip_path = ensure_zip()
    files = extract(zip_path)
    counts: dict[str, int] = {}
    for fd in SUBSETS:
        train = parse_txt(files[f"train_{fd}.txt"])
        test = parse_txt(files[f"test_{fd}.txt"])
        rul = parse_txt(files[f"RUL_{fd}.txt"], rul=True)
        train.to_parquet(data_path("processed", "cmapss", f"train_{fd}.parquet"), index=False)
        test.to_parquet(data_path("processed", "cmapss", f"test_{fd}.parquet"), index=False)
        rul.to_frame().to_parquet(data_path("processed", "cmapss", f"rul_{fd}.parquet"), index=False)
        counts[fd] = len(train)
        print(f"[cmapss] {fd}: train {len(train)} rows / {train.unit.nunique()} units, test {len(test)} rows", flush=True)
    if db_reachable():
        with SessionLocal() as db:
            record_run(db, source="cmapss", source_url=URL, payload=zip_path.read_bytes(), rows=sum(counts.values()))
            db.commit()
    return counts


if __name__ == "__main__":
    pull()
