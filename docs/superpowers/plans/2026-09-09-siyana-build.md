# SIYANA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task inline (the user asked for no subagents). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship SIYANA end to end in the master spec's seven build steps: real public data in Postgres, DALEEL recurrence detection with an evaluated LLM judge, AJAL RUL and CP-SAT scheduling, the MIRAAT control room with a 3D hangar hero, NAZAR vision, and the evidence/audit spine, with Compose and deploy config.

**Architecture:** One FastAPI gateway mounts routers from `services/{nazar,ajal,daleel}` packages over Postgres 16 + pgvector; every AI output writes an `evidence` row in the same transaction. Ingestion adapters under `ingest/` pull SDRS, ASRS, C-MAPSS, MVTec, OpenSky and record `ingest_runs`. The Next 16 app in `web/` renders the spec shell with an R3F hangar hero gated behind progressive enhancement and an SVG plan view fallback.

**Tech Stack:** Python 3.14 venv at `.venv` (FastAPI, Pydantic v2, SQLAlchemy 2, psycopg2, pgvector, sentence-transformers, LightGBM, PyTorch, OR-Tools, anthropic), Postgres 16 pgvector (Docker or local 5432), Next 16.3.4, React 19.2.8, Tailwind v4, Motion 13 (`motion/react`), Lenis, Recharts, three + @react-three/fiber 9 + @react-three/drei 10.

## Global Constraints

- Every AI output writes an evidence row: model version, input hash, confidence, source document ids. No unattributable recommendation.
- Judge model id: `claude-sonnet-4-6`. Embedding model: `sentence-transformers/all-MiniLM-L6-v2` (384 dims). Retrieval k=20, same aircraft type, same ATA chapter.
- RUL cap 125. Report RMSE and NASA asymmetric score vs last-cycle-constant and GRU.
- Scheduler infeasibility is a licence-shortage finding, HTTP 200, not an error.
- Cards are `DRAFT` until approved with a licence number; approval logged.
- Themes `hangar` (default) and `ramp` via `data-theme` on `<html>`. Tokens exactly as in the master spec. Amber only for attention, red only for unserviceable.
- Fonts: Archivo (display), IBM Plex Sans (body), IBM Plex Mono (part numbers, ATA codes, work-order ids only).
- Import Motion from `motion/react`, never `framer-motion`.
- One non-user-triggered motion: airframe draw ~900ms then zones staggered by severity. Glass on exactly two surfaces with `@supports` fallback. Animate only transform/opacity.
- Responsive to 360px; real `<button>`/`<a>`; visible focus rings; logical tab order; reduced-motion honoured; body-text contrast >= 4.5:1 both themes; SVG plan view has a text table.
- Do not start Task 20+ (NAZAR) until the web shell renders real counts.
- No placeholders or TODOs in shipped files. Docs: `docs/ARCHITECTURE.md`, `docs/EVALUATION.md`, `README.md` with exact run commands.
- Python commands run from repo root with `.venv/bin/python`. Node commands run in `web/`.

---

## File map

```
.env.example                      env contract (DATABASE_URL, ANTHROPIC_API_KEY, NEXT_PUBLIC_API_URL)
requirements.txt                  + jupyter nbformat nbconvert ipykernel matplotlib requests pyarrow pytest httpx python-multipart beautifulsoup4 lxml
pytest.ini                        testpaths=tests, pythonpath=.
db/migrations/001_init.sql        extensions, all tables, indexes
db/seed/ata_chapters.csv          4-digit ATA chapters + JASC crosswalk
db/migrate.py                     apply migrations in order, record in schema_migrations; seed ata_chapters
services/common/config.py         Settings from env
services/common/db.py             engine, SessionLocal, get_session
services/common/evidence.py       write_evidence(session, module, model_version, payload, confidence, source_ids) -> int
services/common/hashing.py        sha256_text / sha256_bytes
services/common/models.py         SQLAlchemy ORM for all tables
ingest/common.py                  record_run(), http_get_with_retry(), data paths
ingest/sdrs.py                    SDRS query-form scraper -> snags + defect_events + tails
ingest/asrs.py                    HF jsonl -> snags(source='asrs')
ingest/cmapss.py                  S3 zip -> data/processed/cmapss/*.parquet
ingest/mvtec.py                   HF Voxel51/mvtec-ad subset -> data/raw/mvtec/<category>/{train/good,test/*,ground_truth}
ingest/opensky.py                 live states -> utilisation
ingest/adapters/client_techlog.py CSV contract -> snags + defect_events
services/daleel/normalise.py      normalise(text) -> NormalisedSnag (de-identified text, extracted tokens)
services/daleel/ata_classifier.py train/predict 4-digit ATA (TF-IDF + logistic regression), saved to data/models/ata_clf.joblib
services/daleel/embed.py          Embedder (all-MiniLM-L6-v2), embed_all(session)
services/daleel/retrieve.py       neighbours(session, embedding, ata, aircraft_type, k=20)
services/daleel/judge.py          JUDGE_PROMPT, ClaudeJudge, EmbeddingJudge, get_judge()
services/daleel/recurrence.py     run_recurrence(session, snag_id) -> RecurrenceResult; batch scan -> signatures
services/daleel/cards.py          draft_card(session, signature_id) -> card; approve_card()
services/daleel/router.py         FastAPI router /daleel
services/daleel/eval.py           build candidate pairs, baselines, metrics -> data/metrics/daleel_recurrence.json
services/ajal/features.py         window_features(df, window=30), make_labels(df, cap=125)
services/ajal/rul.py              train_lgbm, predict, nasa_score, rmse; save data/models/rul_lgbm.txt
services/ajal/gru_baseline.py     GRU model + train loop
services/ajal/benchmark.py        run FD001 benchmark -> data/metrics/ajal_rul.json
services/ajal/scheduler.py        schedule(tasks, bays, engineers, horizon) -> ScheduleResult (with licence_shortage)
services/ajal/router.py           FastAPI router /ajal
services/nazar/patchcore.py       PatchCore memory bank on WideResNet50 features; fit / score
services/nazar/detector.py        RT-DETR (transformers) fine-tune + predict on COCO-format dataset
services/nazar/severity.py        severity(defect_type, bbox, image_size) -> 'S1'..'S4'
services/nazar/inference.py       Nazar.predict(img) -> list[Finding]
services/nazar/eval.py            AUROC/AUPRO, mAP, FNR@5%FPR -> data/metrics/nazar.json
services/nazar/router.py          FastAPI router /nazar
services/gateway/main.py          app, CORS, routers, /health
services/gateway/fleet.py         /fleet summary, zones, tails, heatmap, ata/{code}
services/gateway/evidence_api.py  /evidence/{id}, /audit/approvals
tests/                            pytest per module (unit tests do not need Postgres unless marked db)
notebooks/01_sdrs_eda.ipynb       executed EDA with recurring-defect long tail
notebooks/02_rul_benchmark.ipynb  executed benchmark table
notebooks/03_recurrence_eval.ipynb executed P/R/F1 vs baselines
web/app/layout.tsx                fonts, theme cookie -> data-theme, Lenis provider
web/app/page.tsx                  control room (server component fetching /fleet/*)
web/app/audit/page.tsx            approvals log
web/app/inspect/page.tsx          NAZAR upload
web/app/actions.ts                server actions: setTheme cookie
web/app/globals.css               tokens, glass, focus rings, reduced-motion
web/lib/api.ts                    typed fetchers + types
web/lib/severity.ts               rank/colour helpers
web/components/shell/{AtaRail,CommandBar,ThemeToggle,DrillDrawer}.tsx
web/components/hero/{HeroSwitch,HangarScene,Airframe3D,airframeGeometry.ts,AirframePlan,ZoneTable}.tsx
web/components/bays/{Bay,SignaturesBay,RulBay,GanttBay,HeatmapBay,DraftQueueBay}.tsx
web/components/palette/CommandPalette.tsx
web/components/demo/DemoMode.tsx
web/components/providers/{SmoothScroll,UiState}.tsx
docker-compose.yml                db + api + web
services/gateway/Dockerfile, web/Dockerfile
render.yaml, web/vercel.json
docs/ARCHITECTURE.md, docs/EVALUATION.md, README.md
```

---

## Step 1: Ingestion + EDA

### Task 1: Environment, config, schema, migration runner

**Files:** Create `.env.example`, `pytest.ini`, `db/migrations/001_init.sql`, `db/seed/ata_chapters.csv`, `db/migrate.py`, `services/common/{__init__,config,db,hashing,models,evidence}.py`, `tests/test_common.py`. Modify `requirements.txt`, `docker-compose.yml` (db healthcheck).

**Interfaces produced:**
- `services.common.config.settings.database_url: str` (default `postgresql+psycopg2://siyana:siyana@localhost:5432/siyana`), `settings.anthropic_api_key: str | None`, `settings.data_dir: Path`.
- `services.common.db.SessionLocal`, `get_session()` FastAPI dependency.
- `services.common.hashing.sha256_text(s: str) -> str`, `sha256_bytes(b: bytes) -> str`.
- `services.common.evidence.write_evidence(session, *, module: str, model_version: str, payload: str | bytes, confidence: float, source_ids: list[str | int]) -> int` returns evidence id, flushes, does not commit.
- ORM classes in `services.common.models`: `IngestRun, AtaChapter, Tail, Snag, DefectEvent, Signature, Card, Approval, Evidence, RulPrediction, Bay, Engineer, MaintTask, ScheduleRun, NazarFinding, Utilisation, RecurrenceLabel`.

- [ ] Step 1: install missing packages into venv: `.venv/bin/pip install jupyter nbformat nbconvert ipykernel matplotlib requests pyarrow pytest httpx python-multipart beautifulsoup4 lxml joblib` then `.venv/bin/pip freeze > requirements.txt`.
- [ ] Step 2: write `tests/test_common.py`:

```python
from services.common.hashing import sha256_text
from services.common.evidence import write_evidence
from services.common import models

def test_sha256_text_is_stable():
    assert sha256_text("ENG 2 N1 VIB") == sha256_text("ENG 2 N1 VIB")
    assert len(sha256_text("x")) == 64

def test_evidence_row_shape(db_session):
    eid = write_evidence(db_session, module="daleel", model_version="test/0", payload="abc", confidence=0.5, source_ids=[1, 2])
    row = db_session.get(models.Evidence, eid)
    assert row.input_sha256 == sha256_text("abc")
    assert row.source_ids == [1, 2]
```
`tests/conftest.py` provides `db_session` that skips when `DATABASE_URL` is unreachable.
- [ ] Step 3: run `pytest tests/test_common.py -v`, expect import failures.
- [ ] Step 4: write the SQL schema (all tables listed in the file map, `CREATE EXTENSION IF NOT EXISTS vector`, `snags.embedding vector(384)`, ivfflat index `ON snags USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`, `cards.status` CHECK in ('DRAFT','APPROVED','REJECTED')), the migrate runner, config, db, hashing, models, evidence.
- [ ] Step 5: `docker compose up -d db` (or use local 5432 with a created `siyana` role and db), `.venv/bin/python db/migrate.py`, `pytest tests/test_common.py -v` passes.
- [ ] Step 6: commit `feat(db): schema, migration runner, evidence writer`.

### Task 2: SDRS adapter

**Files:** Create `ingest/__init__.py`, `ingest/common.py`, `ingest/sdrs.py`, `tests/test_sdrs_parse.py`, `tests/fixtures/sdrs_results_sample.html` (a saved page from one small live query).

**Interfaces:** `ingest.sdrs.parse_results(html: str) -> list[SdrsRecord]` (pydantic: `control_number, difficulty_date, registration, aircraft_make, aircraft_model, jasc_code, part_name, part_number, discrepancy: str`). `ingest.sdrs.fetch_month(year, month, aircraft_model: str | None) -> list[SdrsRecord]` performs the ASP.NET postback (GET form, read `__VIEWSTATE`, `__EVENTVALIDATION`, POST with `tbDifficultyDateFrom/To` and `btnQuery`). `ingest.sdrs.load(records, session) -> int` upserts tails, snags(source='sdrs'), defect_events. `jasc_to_ata(jasc: str) -> str` returns 4-digit chapter.

- [ ] Step 1: save one live results page as fixture; write `test_parse_results_extracts_rows()` asserting >= 1 row with non-empty discrepancy and 4-char JASC.
- [ ] Step 2: run, fails.
- [ ] Step 3: implement parser with BeautifulSoup (table rows), fetcher with `requests.Session`, retry x3, `record_run(source='sdrs', url, payload)`; CLI `python -m ingest.sdrs --from 2023-01 --to 2025-12 --model 737` writes to DB and prints row counts. Non-zero exit with status code on HTTP failure.
- [ ] Step 4: tests pass; run a real pull for a 36-month window of B737 and A320 family; print counts.
- [ ] Step 5: commit `feat(ingest): FAA SDRS adapter via query form`.

### Task 3: ASRS, C-MAPSS, MVTec, OpenSky adapters and the customer adapter

**Files:** Create `ingest/asrs.py`, `ingest/cmapss.py`, `ingest/mvtec.py`, `ingest/opensky.py`, `ingest/adapters/__init__.py`, `ingest/adapters/client_techlog.py`, `tests/test_adapters.py`, `tests/fixtures/client_techlog_sample.csv`.

**Interfaces:** `ingest.cmapss.load_fd(name: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]` (train, test, rul) with columns `unit, cycle, op1..op3, s1..s21`. `ingest.adapters.client_techlog.COLUMNS = ["tail","occurred_at","ata_code","text","work_order_id","closed_at"]`, `load_csv(path, session) -> int`. `ingest.opensky.fetch_states(bbox) -> list[dict]`.

- [ ] Step 1: tests: C-MAPSS parser column count on a 5-line fixture; client adapter rejects a CSV missing `text` with `ValueError` naming the column; ASRS mapper turns a jsonl record into a `Snag` with source 'asrs'.
- [ ] Step 2: fail, implement, pass. Run all four real pulls (ASRS via `huggingface_hub.hf_hub_download`; MVTec categories `metal_nut, screw, grid, tile`; OpenSky India bbox).
- [ ] Step 3: commit `feat(ingest): ASRS, C-MAPSS, MVTec, OpenSky, customer adapter`.

### Task 4: EDA notebook

**Files:** Create `notebooks/01_sdrs_eda.ipynb` (executed with `jupyter nbconvert --to notebook --execute --inplace`).

Cells: row counts by source; top-20 ATA chapters; per-tail repeat-chapter counts within 90 days; the long-tail plot of "chapters that reappear on the same tail after closure"; share of tails with at least one repeat. Save figures to `docs/figures/`.

- [ ] Execute, confirm no error cells, commit `docs(eda): SDRS recurring-defect EDA`.

## Step 2: DALEEL

### Task 5: Normalise + de-identify

**Files:** `services/daleel/__init__.py`, `services/daleel/normalise.py`, `tests/test_normalise.py`.

**Interface:** `normalise(text: str) -> NormalisedSnag(text: str, tails: list[str], dates: list[str], work_orders: list[str], names_removed: int)`. Rules: uppercase, collapse whitespace, replace N-numbers and `VT-XXX` with `<TAIL>`, dates with `<DATE>`, `WO[- ]?\d+` with `<WO>`, expand abbreviations from a dict (`ENG`->`ENGINE`, `VIB`->`VIBRATION`, `R/H`->`RIGHT`, `L/H`->`LEFT`, `U/S`->`UNSERVICEABLE`, `N/A`, `INOP`->`INOPERATIVE`, `FLT`->`FLIGHT`, `CLB`->`CLIMB`, `CRZ`->`CRUISE`).

- [ ] Tests: `"N123AB ENG 2 N1 VIB ON CLB 12/03/2024"` -> contains `<TAIL>`, `ENGINE`, `VIBRATION`, `CLIMB`, `<DATE>`; tails list == ["N123AB"].
- [ ] Implement, pass, commit.

### Task 6: ATA classifier

**Files:** `services/daleel/ata_classifier.py`, `tests/test_ata_classifier.py`.

**Interface:** `train(session) -> dict(metrics)` fits TF-IDF (1-2 grams) + LogisticRegression on SDRS snags with known JASC->ATA labels, stratified 80/20, saves `data/models/ata_clf.joblib` and `data/metrics/daleel_ata.json` (macro-F1 over top-20 chapters, baselines majority and TF-IDF+LR is the model itself so also report a char-ngram NB baseline). `predict(text) -> tuple[str, float]`.

- [ ] Test: after `train` on a tiny synthetic frame, `predict("ENGINE VIBRATION")` returns a 4-char code and probability in [0,1].
- [ ] Implement, run on real data, commit with metrics file.

### Task 7: Embedding + retrieval

**Files:** `services/daleel/embed.py`, `services/daleel/retrieve.py`, `tests/test_retrieve.py`.

**Interface:** `Embedder().encode(texts: list[str]) -> np.ndarray[float32, (n,384)]`; `embed_all(session, batch=256) -> int`. `neighbours(session, vec, *, ata_code: str, aircraft_type: str, k=20, exclude_id=None) -> list[Neighbour(id, text, tail, occurred_at, work_order_id, distance)]` using `<=>` cosine on pgvector filtered by `ata_code` and `tails.aircraft_type`.

- [ ] Test (db): insert three snags, two same chapter; neighbours for one returns the other and not the third chapter.
- [ ] Implement, run `embed_all`, commit.

### Task 8: Judge (Claude + fallback), recurrence, cards, router

**Files:** `services/daleel/judge.py`, `services/daleel/recurrence.py`, `services/daleel/cards.py`, `services/daleel/router.py`, `tests/test_judge.py`, `tests/test_cards.py`.

**Interfaces:**
```python
class Verdict(BaseModel):
    is_recurrence: bool
    matched_ids: list[int]
    signature: str          # <=12 words
    reasoning: str          # <=40 words
    confidence: float

class Judge(Protocol):
    model_version: str
    def judge(self, candidate: str, neighbours: list[Neighbour]) -> Verdict: ...

class ClaudeJudge:   # model "claude-sonnet-4-6", JUDGE_PROMPT from master spec, strict JSON parse with one retry
class EmbeddingJudge:  # cosine >= 0.82 -> recurrence; signature = shortest matched text truncated to 12 words
def get_judge(settings) -> Judge  # Claude if key present else EmbeddingJudge

@dataclass
class RecurrenceResult: snag_id: int; verdict: Verdict; neighbours: list[Neighbour]; evidence_id: int; signature_id: int | None
def run_recurrence(session, snag_id: int, judge: Judge) -> RecurrenceResult
def judge_free_text(session, text: str, aircraft_type: str, judge: Judge) -> RecurrenceResult  # used by Cmd+K; snag_id = -1
def scan(session, judge, limit: int) -> int   # groups verdicts into signatures rows (count >= 2)

def draft_card(session, signature_id: int, judge_model_version: str) -> Card  # body: {title, signature, source_snag_ids, work_order_ids, proposed_action, references:[AMM chapter, CAR-145 A.50]}, status DRAFT, evidence row
def approve_card(session, card_id: int, *, engineer_name: str, licence_number: str, decision: Literal["APPROVED","REJECTED"], note: str) -> Card  # raises ValueError if licence_number empty
```
Router: `GET /daleel/signatures`, `POST /daleel/judge`, `GET /daleel/cards`, `POST /daleel/cards/{id}/draft`, `POST /daleel/cards/{id}/approve`.

- [ ] Tests: EmbeddingJudge returns Verdict shape; ClaudeJudge parses a fenced JSON string (mock client); `approve_card` without licence raises; approved card writes `approvals` row; every path creates an evidence row.
- [ ] Implement, pass, commit `feat(daleel): judge, recurrence, draft cards, router`.

### Task 9: 300-pair eval

**Files:** `services/daleel/eval.py`, `data/labels/recurrence_pairs.csv`, `notebooks/03_recurrence_eval.ipynb`, `data/metrics/daleel_recurrence.json`.

- [ ] `build_pairs(session, n=300, seed=7)` samples candidate pairs stratified: 100 nearest-neighbour pairs, 100 random same-chapter, 100 cross-chapter. Write CSV with `pair_id, snag_a, snag_b, text_a, text_b, label(blank)`.
- [ ] Label all 300 by reading them (labeller column = "claude-fable-5.1 hand-labelled, rubric in EVALUATION.md"). Save.
- [ ] `evaluate()` computes P/R/F1 for TF-IDF cosine (threshold tuned on 50-pair dev split), embedding-only (threshold tuned same), EmbeddingJudge, ClaudeJudge (if key). Write JSON. Notebook renders table and confusion matrices.
- [ ] Commit `eval(daleel): 300-pair recurrence benchmark`.

## Step 3: AJAL RUL

### Task 10: Features, LightGBM, NASA score, GRU, benchmark

**Files:** `services/ajal/__init__.py`, `services/ajal/features.py`, `services/ajal/rul.py`, `services/ajal/gru_baseline.py`, `services/ajal/benchmark.py`, `tests/test_ajal.py`, `notebooks/02_rul_benchmark.ipynb`, `data/metrics/ajal_rul.json`.

**Interfaces:** `window_features(df, window=30) -> DataFrame` (mean/std/slope per sensor, keeps unit, cycle); `make_labels(df, cap=125) -> ndarray`; `nasa_score(y_true, y_pred) -> float` (`d = pred - true; sum(exp(-d/13)-1 if d<0 else exp(d/10)-1)`); `rmse`; `train_lgbm(X, y) -> Booster`; `last_cycle_constant_baseline(train_df, test_df) -> ndarray` (predicts mean capped RUL at last cycle); `GRUModel(n_features, hidden=64)`, `train_gru(...)`; `run_benchmark(fd="FD001") -> dict` with keys `lgbm, gru, baseline` each `{rmse, nasa_score}` plus `predictions` for the watchlist.

- [ ] Tests: `nasa_score` on `true=[10], pred=[20]` equals `exp(1)-1`; late penalised more than early of equal magnitude; `make_labels` caps at 125; `window_features` has `s2_slope` column.
- [ ] Implement, run FD001 benchmark (LightGBM 1200 trees L1; GRU 15 epochs seq 30), write JSON, execute notebook, commit.

### Task 11: RUL watchlist persistence + router

**Files:** `services/ajal/router.py`, `services/ajal/watchlist.py`.

- [ ] `persist_watchlist(session, predictions, model_version)` maps C-MAPSS test units to fleet tails (round-robin over the SDRS fleet tails, engine positions 1 and 2), writes `rul_predictions` with an evidence row each. `GET /ajal/rul/watchlist` returns tails sorted ascending RUL with sparkline series (last 30 cycles of s11 normalised). `GET /ajal/rul/benchmark` returns the metrics JSON.
- [ ] Test: watchlist rows each have `evidence_id`. Commit.

## Step 4: MIRAAT shell on real counts

### Task 12: Gateway app and fleet endpoints

**Files:** `services/gateway/main.py`, `services/gateway/fleet.py`, `services/gateway/evidence_api.py`, `tests/test_gateway.py`.

**Endpoints and shapes:**
```
GET /health -> {status:"ok", db:true}
GET /fleet/summary -> {tails:int, open_defects:int, recurring_signatures:int, drafts_pending:int, unserviceable_tails:int}
GET /fleet/zones -> [{ata:"7200", chapter:"72", title:"Engine", open_count:int, max_severity_rank:1-4, recurring:int}]
GET /fleet/tails -> [{registration, aircraft_type, status:"serviceable"|"unserviceable", open_defects, bay_id|null}]
GET /fleet/heatmap -> {tails:[...], chapters:[...], cells:[{tail, chapter, count, recurring}]}
GET /fleet/ata/{chapter} -> {chapter, title, snags:[...], signatures:[...], cards:[...]}
GET /evidence/{id} -> evidence row
GET /audit/approvals -> [...]
```
Severity rank per defect_event derived from card/signature presence and age: recurring + open > 30d = 4, recurring = 3, open > 30d = 2, else 1.

- [ ] Tests with `httpx.AsyncClient(app)`: `/health` 200; `/fleet/zones` items have the keys above.
- [ ] Implement, `uvicorn services.gateway.main:app --reload`, commit.

### Task 13: Web foundation: tokens, fonts, theme cookie, Lenis, shell

**Files:** `web/app/globals.css`, `web/app/layout.tsx`, `web/app/actions.ts`, `web/components/providers/SmoothScroll.tsx`, `web/components/providers/UiState.tsx`, `web/components/shell/{AtaRail,CommandBar,ThemeToggle,DrillDrawer}.tsx`, `web/lib/api.ts`, `web/lib/severity.ts`, `web/.env.local.example`. Remove Geist fonts and template page content.

- `globals.css`: `:root[data-theme="hangar"]` and `[data-theme="ramp"]` token blocks verbatim from the spec; `@theme inline` mapping to Tailwind colour utilities (`bg-surface-0`, `text-ink`, ...); `.glass` with `@supports not (backdrop-filter: blur(1px))` fallback; `:focus-visible { outline: 2px solid var(--lamp); outline-offset: 2px }`; reduced-motion guard.
- `layout.tsx`: `cookies().get("theme")` -> `data-theme`; fonts Archivo, IBM_Plex_Sans, IBM_Plex_Mono with variables `--font-display`, `--font-body`, `--font-mono`.
- `ThemeToggle`: `<button role="switch" aria-checked>` labelled HANGAR / RAMP; knob is a lamp dot; spring on `x` only; calls server action `setTheme` and sets `document.documentElement.dataset.theme` immediately.
- `AtaRail`: `<nav aria-label="ATA chapters">` list of `<a href="/?ata=NN">` with mono chapter number and title, current chapter `aria-current="page"`.
- `CommandBar`: sticky glass bar with search button that opens the palette (Task 16), summary counts, theme toggle.
- `DrillDrawer`: glass `<dialog>`-like panel driven by `?ata=` search param, focus trap, Escape closes, contains `AirframePlan` for the chapter and the `/fleet/ata/{chapter}` lists.

- [ ] Verify in the browser at 1280px and 360px, both themes; contrast check of `--ink-muted` on `--surface-1` in both themes with a script (`web/scripts/contrast.mjs`) asserting >= 4.5.
- [ ] Commit `feat(web): tokens, fonts, theme cookie, shell`.

### Task 14: SVG plan view + zone table + bays on real counts

**Files:** `web/components/hero/{AirframePlan,ZoneTable,HeroSwitch}.tsx`, `web/components/bays/{Bay,SignaturesBay,RulBay,GanttBay,HeatmapBay,DraftQueueBay}.tsx`, `web/app/page.tsx`.

- `AirframePlan({zones, onSelect})`: `viewBox 0 0 800 420`, one `motion.path` outline with `pathLength` 0->1 over 0.9s ease `[0.16,1,0.3,1]`, zone `<g>` groups as `<a href="/?ata=NN">` with `opacity` stagger `0.9 + (4 - rank) * 0.08`; `useReducedMotion` makes both instant; fill `var(--tag-us)` for rank >= 3 else `var(--lamp)`; zones with zero open defects use `var(--hairline)` stroke only.
- `ZoneTable`: `<table>` with caption "Open defects by ATA chapter", columns chapter, title, open, max severity, recurring; visually present under the hero, not hidden.
- `HeroSwitch`: client component; renders `AirframePlan` immediately; after mount, if width >= 768 and no reduced motion and WebGL available and cores > 2, swaps in `HangarScene` (Task 15) via `next/dynamic`.
- Bays: CSS grid with named areas, `Bay({title, area, children, eyebrow})` uses Archivo for the title. `SignaturesBay` lists signatures (mono ids, count, chapters); `RulBay` lists watchlist with Recharts `LineChart` sparkline per row; `GanttBay` and `HeatmapBay` are CSS grids (Task 17 fills Gantt from schedule API; heatmap from `/fleet/heatmap`); `DraftQueueBay` lists DRAFT cards with an approve form requiring licence number.
- [ ] Browser check: real counts from the API render; Lighthouse a11y >= 90; commit `feat(web): plan view, zone table, bays on live data`.

### Task 15: 3D hangar hero

**Files:** `web/components/hero/{HangarScene,Airframe3D}.tsx`, `web/components/hero/airframeGeometry.ts`. Install `three @react-three/fiber @react-three/drei @types/three`.

- `airframeGeometry.ts`: `buildFuselage(): LatheGeometry` from profile points; `buildWing(side)`, `buildStabilisers()`, `buildEngine(side)`; `ZONE_ANCHORS: Record<chapter, {position:[x,y,z], size:[x,y,z]}>` for chapters 21,27,28,29,32,34,49,52,53,55,57,71,72,73,78; `airframeEdges(): Float32Array` line segments for the draw animation.
- `Airframe3D({tail, zones, drawProgress, onZoneSelect})`: meshes with `meshStandardMaterial` colour from CSS var read once via `getComputedStyle`; zone shells `transparent opacity 0.35`, emissive lamp/tag-us by rank, emissiveIntensity animated 0 -> 1 after draw by severity order; `<Line>` from drei with `dashed`, `dashOffset` from `drawProgress`.
- `HangarScene({tails, zones, bays, onTailSelect, onZoneSelect})`: `<Canvas dpr={[1,1.75]} frameloop="demand" camera fov 38>`; floor grid; N bay outlines; one `Airframe3D` per tail in its bay; `OrbitControls` with `minPolarAngle 0.44, maxPolarAngle 1.05, minAzimuthAngle -0.61, maxAzimuthAngle 0.61, enablePan false, enableZoom false`; draw progress driven by Motion `animate` 0->1 over 0.9s calling `invalidate()`; click on a tail lerps camera target to it (user-triggered); `<Html>` callouts for RUL on watchlisted engines.
- [ ] Browser check on desktop: draws once, no continuous frames when idle (check with `performance` in devtools). Commit `feat(web): 3D hangar hero with SVG fallback`.

### Task 16: Command palette with live snag judge

**Files:** `web/components/palette/CommandPalette.tsx`.

- Opens on Cmd/Ctrl+K or the CommandBar button. `role="dialog"` with `aria-modal`, `<input role="combobox">`, `<ul role="listbox">` with roving `aria-activedescendant`; groups: Tails, ATA chapters, Work orders (from `/fleet/*`), and "Judge this snag" when input length > 25 chars: `POST /daleel/judge {text, aircraft_type}` and render neighbours (mono ids, texts), the verdict, and an "Evidence #id" link that opens the evidence row.
- [ ] Keyboard-only walkthrough in browser. Commit.

### Task 17: Demo mode

**Files:** `web/components/demo/DemoMode.tsx`.

- Button "Run demo" in the command bar. Steps from the pitch script: open ATA 72 drawer, focus first signature, open its draft card, scroll to RUL bay, scroll to Gantt, toggle theme. Each step is a button press ("Next") that calls the same handlers as user clicks. `aria-live="polite"` narration line.
- [ ] Commit.

## Step 5: NAZAR

### Task 18: PatchCore anomaly head

**Files:** `services/nazar/__init__.py`, `services/nazar/patchcore.py`, `services/nazar/severity.py`, `tests/test_nazar.py`.

- `PatchCore(backbone="wide_resnet50_2", layers=("layer2","layer3"), coreset_ratio=0.1)`, `fit(image_paths)`, `score(img) -> (image_score: float, heatmap: ndarray)`, `save(path)`, `load(path)`. Trained per MVTec category on `train/good` only.
- `severity(defect_type, bbox, image_size)` exactly as the spec (base map, +1 if area > 5%, cap S4).
- [ ] Tests: `severity("crack", (0,0,10,10), (1000,1000)) == "S3"`; large crack -> "S4"; PatchCore `score` on a 64x64 random image returns a float and a 2D array.
- [ ] Fit on the four MVTec categories, evaluate image AUROC + pixel AUPRO -> `data/metrics/nazar.json`. Commit.

### Task 19: Detector, inference, eval, router

**Files:** `services/nazar/detector.py`, `services/nazar/inference.py`, `services/nazar/eval.py`, `services/nazar/router.py`.

- `detector.py`: `RTDETRDetector(model_id="PekingU/rtdetr_r50vd")` via `transformers`, `fine_tune(coco_json_dir, epochs)`, `detect(img) -> list[(cls, bbox, conf)]`. Dataset: `ingest/nazar_boxes.py` derives COCO boxes from MVTec ground-truth masks with class map `crack->crack, scratch->crack, bent->dent, color/contamination->corrosion, thread->delamination, missing->missing-fastener` (documented as a stand-in for aircraft imagery in EVALUATION.md). If a public aircraft-defect COCO set is retrievable at build time, use it instead and record the source.
- `inference.py`: `Nazar.predict(img) -> list[Finding]` (detector head + anomaly head on regions the detector left empty), `ATA_HINT = {"crack":"5300","corrosion":"5300","dent":"5300","delamination":"5700","missing-fastener":"5300","anomaly":None}`.
- `eval.py`: mAP@0.5, FNR at 5% FPR, writes into `data/metrics/nazar.json`.
- Router: `POST /nazar/inspect` multipart image -> findings + `evidence_id` (input hash = image sha256), stores `nazar_findings`.
- [ ] Test: router returns 200 with `findings` list and `evidence_id` for a small PNG. Web page `web/app/inspect/page.tsx` with upload, bbox overlay (SVG rects over the image), severity chips. Commit.

## Step 6: Scheduler

### Task 20: CP-SAT scheduler with licence-shortage finding, Gantt

**Files:** `services/ajal/scheduler.py`, `services/ajal/seed_schedule.py`, `tests/test_scheduler.py`, `web/components/bays/GanttBay.tsx` (fill).

**Interface:**
```python
class Task(BaseModel): id: str; tail: str; est_hours: int; due_by: int; ata: str; licence_required: str; priority: int
class BaySpec(BaseModel): id: str; capable_ata: set[str]; available_from: int = 0
class Engineer(BaseModel): id: str; licences: set[str]; shift_hours: int
class Assignment(BaseModel): task_id: str; bay_id: str; engineer_id: str; start: int; end: int
class ScheduleResult(BaseModel):
    status: Literal["optimal","feasible","infeasible"]
    assignments: list[Assignment]
    objective: int | None
    solve_seconds: float
    licence_shortage: list[dict]   # [{licence:"B1.1", tasks:[...], hours_required:int, hours_available:int}]
def schedule(tasks, bays, engineers, horizon_hours: int, time_limit_s: float = 20.0) -> ScheduleResult
def greedy_edd(tasks, bays, engineers, horizon_hours) -> ScheduleResult   # baseline
```
Model: per task interval, bay choice via optional intervals per allowed bay with exactly-one; engineer choice via optional intervals per engineer holding the licence; NoOverlap per bay and per engineer; `end <= due_by` hard; minimise `sum(priority * end)`. On INFEASIBLE: compute shortage by summing `est_hours` per licence vs sum of shift hours of engineers holding it, and re-solving with the due-date constraint relaxed for each licence category to find which relaxation restores feasibility.

- [ ] Tests: two tasks, one bay -> no overlap; task needing licence nobody holds -> `status == "infeasible"` and shortage names that licence; weighted lateness of CP-SAT <= greedy on a 12-task seed.
- [ ] Seed real tasks from open defect_events (est_hours by chapter table, due_by from severity), 4 bays, 6 engineers with B1.1/B2 licences arranged so Thursday is short one B1.1. Router `POST /ajal/schedule/solve`, `GET /ajal/schedule/latest`. GanttBay renders bays x hours, hatched slot for the shortage. Commit.

## Step 7: Evidence UI, Compose, deploy, docs

### Task 21: Evidence "Why?" and audit page

- `web/components/shell/EvidenceLink.tsx` (`<button>` "Why?" opening a popover with model version, hash prefix, confidence, source ids linking to `?snag=`); used in SignaturesBay, RulBay, DraftQueueBay, palette result, inspect page. `web/app/audit/page.tsx` lists approvals. Commit.

### Task 22: Docker Compose, Dockerfiles, deploy config

- `services/gateway/Dockerfile` (python:3.12-slim, install requirements without torch CUDA, run migrate then uvicorn), `web/Dockerfile` (node:24-alpine, `next build`, standalone). Compose: db (healthcheck), api (depends_on healthy, env), web. `render.yaml` (web service api + postgres), `web/vercel.json`. `docker compose up --build` renders `/` on 3000 with data. Commit.

### Task 23: Docs

- `README.md`: exact commands for venv, DB, migrate, each ingest pull, each training/eval, gateway, web, compose, deploy, tests. `docs/ARCHITECTURE.md`: spec diagram + data flow narrative + evidence spine + deviations (Next 16, SDRS query route, 3D hero). `docs/EVALUATION.md`: tables filled from `data/metrics/*.json` with baselines and the labelling rubric. Commit.

### Task 24: Final verification

- `pytest -q` green; `npm run build` and `npm run lint` clean; browser screenshots at 360px and 1280px in both themes; reduced-motion emulation shows instant draw; Lighthouse perf and a11y >= 90; no "TODO" or "placeholder" strings in shipped files (`grep -rn "TODO\|TBD\|placeholder" --include=*.py --include=*.ts --include=*.tsx --include=*.md . | grep -v node_modules | grep -v .venv` returns only the plan file).
