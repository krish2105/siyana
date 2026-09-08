# SIYANA

AI intelligence for aircraft maintenance (MRO) and continuing airworthiness. SIYANA mines free-text
tech-log snags for recurring defect signatures, predicts component remaining useful life, schedules
the hangar around it, inspects imagery for damage, and shows the whole picture in one control room.
Every AI output carries an evidence row: model version, input hash, confidence, source documents.

Four modules: **NAZAR** (vision), **AJAL** (forecasting and optimisation), **DALEEL** (agentic
recurrence detection and drafting), **MIRAAT** (the control room). Architecture in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); measured results in
[docs/EVALUATION.md](docs/EVALUATION.md).

## Prerequisites

- Python 3.12+ (the project venv is 3.14) with the packages in `requirements.txt`
- Node 20+ (built with Node 24) for `web/`
- Postgres 16 or 17 with the `vector` extension (Docker Compose provides one)
- Optional: `ANTHROPIC_API_KEY` for the Claude judge. Without it DALEEL uses the embedding judge and says so in every evidence row.

## Run it locally

```bash
# 1. Python environment (skip if .venv already exists)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
# 2. Database. Either Docker (host port 5433) ...
docker compose up -d db
```

```bash
# ... or a local Postgres: create the role and database, then enable pgvector
psql -d postgres -c "CREATE ROLE siyana LOGIN PASSWORD 'siyana' CREATEDB;" -c "CREATE DATABASE siyana OWNER siyana;" && psql -d siyana -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

```bash
# 3. Configuration
cp .env.example .env   # set DATABASE_URL (use port 5433 for the Compose database) and ANTHROPIC_API_KEY if you have one
```

```bash
# 4. Schema and ATA chapter seed (idempotent)
.venv/bin/python db/migrate.py
```

```bash
# 5. Ingest the public data. SDRS takes ~2.5 minutes per week of records; run several windows in parallel if you like.
.venv/bin/python -m ingest.sdrs --from 2025-01-01 --to 2025-12-31 --days 7
```

```bash
.venv/bin/python -m ingest.asrs
```

```bash
.venv/bin/python -m ingest.cmapss
```

```bash
.venv/bin/python -m ingest.mvtec --categories metal_nut screw grid tile
```

```bash
.venv/bin/python -m ingest.opensky
```

```bash
# 6. Derived artefacts: embeddings, vector index, demo fleet, recurrence scan, draft cards, RUL watchlist, hangar schedule, ATA classifier
scripts/refresh.sh
```

```bash
# 7. RUL benchmark (LightGBM vs GRU vs constant baseline on C-MAPSS FD001) and NAZAR anomaly head
.venv/bin/python -m services.ajal.benchmark
```

```bash
.venv/bin/python -m services.nazar.eval
```

```bash
# 8. NAZAR detector: derive boxes from MVTec masks, fine-tune RT-DETR, evaluate
.venv/bin/python -m ingest.nazar_boxes && .venv/bin/python -m services.nazar.detector --epochs 12 && .venv/bin/python -c "from services.nazar.eval import evaluate_detector; evaluate_detector()"
```

```bash
# 9. API
.venv/bin/uvicorn services.gateway.main:app --reload --port 8000
```

```bash
# 10. Web (in a second terminal)
cd web && cp .env.local.example .env.local && npm install && npm run dev
```

Open http://localhost:3000. API docs are at http://localhost:8000/docs.

### Your own tech log

Export your tech log to CSV with the columns documented at the top of
`ingest/adapters/client_techlog.py` and load it:

```bash
.venv/bin/python -m ingest.adapters.client_techlog path/to/techlog.csv && scripts/refresh.sh --skip-classifier
```

## Evaluate

```bash
# DALEEL: 300 hand-labelled pairs (already labelled in data/labels/recurrence_pairs.csv)
.venv/bin/python -m services.daleel.eval evaluate
```

```bash
# Notebooks, executed in place
cd notebooks && ../.venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=siyana 01_sdrs_eda.ipynb 02_rul_benchmark.ipynb 03_recurrence_eval.ipynb
```

Register the kernel once with `.venv/bin/python -m ipykernel install --user --name siyana`.

## Test

```bash
.venv/bin/python -m pytest -q
```

```bash
cd web && npm run lint && npm run build && node scripts/contrast.mjs
```

Database-backed tests skip automatically when `DATABASE_URL` is unreachable.

## Docker Compose (everything)

```bash
docker compose up --build
```

Postgres on 5433, API on 8000, web on 3000. The `data/` directory is mounted into the API
container, so ingest once on the host and the containers see the same corpus.

## Deploy

- **API + database on Render**: `render.yaml` defines the web service (Docker) and a Postgres 16 instance. Set `ANTHROPIC_API_KEY` in the Render dashboard; `DATABASE_URL` is injected from the database.
- **Web on Vercel**: import `web/` as the project root; `web/vercel.json` pins the framework and region. Set `NEXT_PUBLIC_API_URL` to the Render service URL and add that Vercel origin to `CORS_ORIGINS` on the API.

## Safety posture

SIYANA triages and drafts. It never releases an aircraft to service. Rectification cards stay
`DRAFT` until a licensed engineer approves them with a licence number, and that approval is logged
with the evidence behind the card. Severity grades from NAZAR are triage priors, not airworthiness
determinations.

## Data licences

FAA SDRS and NASA ASRS are public US government data. NASA C-MAPSS is public. MVTec AD is
CC BY-NC-SA 4.0 (research use only; do not use the fitted anomaly banks commercially).
OpenSky anonymous API data is for non-commercial use.
