# SIYANA design spec — 2026-09-09

Status: approved by Krishna Mathur on 2026-09-09. This document records the decisions
that extend or deviate from `SIYANA_master_spec.md`. Where the two disagree, this
document wins; everywhere else the master spec is authoritative.

## 1. Decisions taken in brainstorming

| Axis | Decision | Reason |
|---|---|---|
| Hero | Full 3D hangar scene (React Three Fiber) with the SVG plan view as fallback and drawer view | User choice. 3D carries the pitch; SVG carries accessibility. |
| Theme toggle | Custom placard toggle, HANGAR / RAMP, lamp knob | 21st.dev catalog toggles are generic sun/moon; user asked for nothing stale. |
| Extra features | Cmd+K palette with live snag judge; tail x ATA recurrence heatmap; hangar Gantt; guided demo mode | User selected all four. |
| Framework | Keep Next 16.3.4 / React 19.2.8 / Motion 13 / Tailwind v4 as installed | Avoid re-scaffolding. Deviation from "Next 15" recorded in ARCHITECTURE.md. |
| SDRS source | Live query form at sdrs.faa.gov (ASP.NET postback, month windows) | Bulk hosts av-info.faa.gov and HF mirrors are down or gated as of 2026-09-09. |
| Notebook tooling | Add jupyter, nbformat, nbconvert, ipykernel, matplotlib, requests, pyarrow to the venv | Missing; notebooks must execute. |

## 2. Layout

The master spec shell is unchanged: left ATA rail, floating glass command bar,
bays of varying size below the hero, glass on exactly two surfaces (command bar,
drill-in drawer) with a solid `@supports` fallback.

The hero region holds `HangarScene` (R3F). It renders:
- N bays taken from the current CP-SAT schedule.
- One procedural airframe per scheduled tail, parked in its bay.
- ATA zone meshes on each airframe, emissive by open-defect severity: S3-S4 use `--tag-us`, S1-S2 use `--lamp`, no open defects use no emissive.
- Engine callouts showing predicted RUL for tails on the RUL watchlist.

`AirframePlan` (SVG) renders instead of the 3D scene when any of these hold:
viewport under 768px, `prefers-reduced-motion`, no WebGL context, or
`navigator.hardwareConcurrency <= 2`. It also renders inside the drill-in
drawer as the per-tail view regardless of device. Its text-equivalent table
(`ZoneTable`) always renders directly under the hero.

Bays below the hero (CSS grid, `grid-template-areas`, varying spans):
Recurring Signatures (wide), RUL Watchlist (tall), Hangar Gantt (wide),
Recurrence Heatmap tail x ATA (wide), DALEEL Draft Queue (wide).

## 3. Motion

Exactly one non-user-triggered motion. In the 3D scene: airframe edge lines draw
over 900ms (`Line` dash offset animated from full to zero), then zone glows fade
in ordered by severity rank, critical first, 80ms apart. In the SVG fallback:
`pathLength` 0 -> 1 over 900ms, then zone groups fade by severity rank.

Camera movement only on user click (tail or zone). Orbit is limited to a shallow
arc (azimuth +-35deg, polar 25-60deg). `frameloop="demand"` when nothing is
animating, invalidated on interaction. `dpr` capped at `[1, 1.75]`.

Under `prefers-reduced-motion` every draw and stagger is instant and Lenis is
not mounted.

## 4. Airframe geometry

Procedural, built in code, no external model:
- Fuselage: `LatheGeometry` from a profile array (nose, constant section, tail cone).
- Wings, horizontal and vertical stabilisers: `ExtrudeGeometry` from 2D shapes, swept back.
- Engines: two cylinders with inner ring.
- Zones: named groups mapping to ATA chapters 21, 27, 28, 29, 32, 34, 49, 52, 53, 55, 57, 71, 72, 73, 78. Each zone is a translucent shell mesh positioned on the airframe. `userData.ata` carries the chapter for picking.

## 5. Data

| Source | Adapter | Route verified 2026-09-09 | Target table |
|---|---|---|---|
| FAA SDRS | `ingest/sdrs.py` | `https://sdrs.faa.gov/Query.aspx` postback, difficulty-date window per month, results page parsed to rows | `defect_events` |
| NASA ASRS | `ingest/asrs.py` | HF `elihoole/asrs-aviation-reports` (Apache-2.0), jsonl train/val/test | `snags` (narratives) |
| NASA C-MAPSS | `ingest/cmapss.py` | `https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip` | `sensor_windows` (parquet in data/processed) |
| MVTec AD | `ingest/mvtec.py` | HF `Voxel51/mvtec-ad` (CC BY-NC-SA 4.0), subset of categories | files under data/raw/mvtec |
| OpenSky | `ingest/opensky.py` | `https://opensky-network.org/api/states/all` India bbox, anonymous | `utilisation` |
| Customer | `ingest/adapters/client_techlog.py` | CSV with documented column contract | `snags`, `defect_events` |

Every adapter records `source_url`, `fetched_at`, and SHA-256 of the raw payload in
`ingest_runs`. If SDRS is unreachable at run time the adapter exits non-zero with
the HTTP status and the retry command; it does not fabricate rows.

JASC codes from SDRS map to 4-digit ATA chapters via `db/seed/ata_chapters.csv`.

## 6. Backend

One FastAPI application in `services/gateway/main.py` mounts routers:
`/nazar`, `/ajal`, `/daleel`, `/fleet`, `/evidence`, `/audit`. Services are
Python packages under `services/` importable by the gateway. SQLAlchemy 2 with
psycopg2, pgvector column type on `snags.embedding` (384 dims, all-MiniLM-L6-v2).

Evidence spine: table `evidence(id, module, model_version, input_sha256,
confidence, source_ids jsonb, created_at)`. Every AI output inserts one row inside
the same transaction as the output and returns `evidence_id`. The web client
shows a "Why?" control on every AI-derived value that opens the evidence row.

DALEEL judge: `claude-sonnet-4-6` via the Anthropic SDK when `ANTHROPIC_API_KEY`
is set in `.env`. Otherwise `EmbeddingJudge` decides recurrence by cosine
similarity >= 0.82 with the same JSON output shape, and the evidence row's
`model_version` is `embedding-judge/all-MiniLM-L6-v2`. The eval notebook reports
both judges when the key is present.

Rectification cards: `status` in {DRAFT, APPROVED, REJECTED}. Transition out of
DRAFT only via `POST /daleel/cards/{id}/approve` with `licence_number` and
`engineer_name`; writes `approvals` row. The UI never offers approval without a
licence number field.

Scheduler: CP-SAT with hard due dates and ATA-capable bays, engineers as
optional intervals per licence category. On INFEASIBLE the endpoint returns
HTTP 200 with `status: "infeasible"` and a `licence_shortage` list computed by
relaxing engineer capacity one category at a time.

## 7. Web

- `app/layout.tsx`: reads `theme` cookie, sets `data-theme` on `<html>`, loads Archivo, IBM Plex Sans, IBM Plex Mono via `next/font/google`.
- `components/shell/`: `AtaRail`, `CommandBar` (glass), `ThemeToggle` (placard), `DrillDrawer` (glass).
- `components/hero/`: `HangarScene` (R3F, dynamic import, ssr false), `Airframe3D`, `AirframePlan` (SVG), `ZoneTable`, `HeroSwitch` (progressive-enhancement gate).
- `components/bays/`: `SignaturesBay`, `RulBay`, `GanttBay`, `HeatmapBay`, `DraftQueueBay`.
- `components/palette/`: `CommandPalette` (Cmd+K, listbox with roving tabindex, snag paste runs `POST /daleel/judge`).
- `components/demo/`: `DemoMode` stepper firing the same handlers as user clicks.
- `lib/api.ts`: typed fetchers against `NEXT_PUBLIC_API_URL`.
- Lenis via `lenis/react`, mounted only when reduced-motion is off.
- Charts: Recharts for RUL sparklines; Gantt and heatmap are CSS grid, not a chart library.

## 8. Evaluation

Documented in `docs/EVALUATION.md` with actual numbers from the notebooks.

| Module | Metric | Baselines |
|---|---|---|
| DALEEL recurrence | P / R / F1 on 300 labelled SDRS pairs | TF-IDF cosine; embedding-only kNN |
| DALEEL ATA classification | Macro-F1 top-20 chapters | Majority; logistic regression on TF-IDF |
| AJAL RUL | RMSE and NASA score on FD001 test | Last-cycle-constant; GRU |
| AJAL scheduler | Weighted lateness, solve time | Greedy EDD |
| NAZAR anomaly | Image AUROC, pixel AUPRO on MVTec subset | none |
| NAZAR detector | mAP@0.5, FNR at 5% FPR | none |
| MIRAAT | Lighthouse perf and a11y, both themes at 360px | none |

## 9. Build order

Unchanged from the master spec: (1) ingestion + EDA, (2) DALEEL + eval,
(3) AJAL RUL + benchmark, (4) MIRAAT shell on real counts, (5) NAZAR,
(6) CP-SAT scheduler, (7) evidence/audit + Compose + deploy. The 3D hero is
part of step 4 with the SVG fallback built first.

## 10. Out of scope

Acoustic channel, multilingual snags, AMM linking, federated learning, CAMO
scoring, mobile native apps.
