# SIYANA — AI Intelligence Platform for Indian MRO & Continuing Airworthiness

*Build + pitch specification. Written for Claude Code execution.*
*Prepared for Krishna Mathur · September 2026*

---

## 0. Why this one project covers all four of your goals

| Goal | How SIYANA serves it |
|---|---|
| Impress the MRO contact → referral / job | It solves a problem their organisation has *this quarter*, in their vocabulary (ATA chapters, MEL deferrals, CAMO, Part-145) |
| A real deployable pilot | Runs on public data out of the box; swaps to their tech-log export with one adapter file |
| Academic / term submission | Four distinct AI disciplines, clean evaluation metrics, viva-ready |
| Startup / product you own | Indian MRO is going from ~$4.4bn (2025) to ~$5.7bn (2030) with 80–90% of heavy work still offshore — this is a real wedge |

**One sentence pitch:** *SIYANA turns an MRO's messiest asset — unstructured snag text, borescope images and sensor logs — into a single airworthiness picture that predicts the next AOG before it happens.*

---

## 1. Problem statement

Indian continuing airworthiness is currently failing on a *data* problem, not an engineering-skill problem.

**The evidence you cite in the pitch:**

1. A DGCA audit of 754 commercial aircraft (Jan 2025 – Feb 2026) found 377 — nearly half the fleet reviewed — carrying **recurring technical defects**. Recurring means the defect was rectified and came back. That is a pattern-detection failure.
2. A July 2025 audit of one major carrier flagged ~100 safety lapses including 7 Level-1 violations requiring urgent remediation.
3. An annual DGCA audit found 263 safety lapses across Indian airlines.
4. India holds FAA IASA **Category 1** status, with a 2026 FAA review pending. A downgrade would break US routes and codeshares.
5. ~80–90% of Indian MRO work, especially engine overhaul, still goes offshore.
6. The fleet is heading to 1,800+ aircraft by 2030 while skilled AME supply lags.

**The operational failure mode SIYANA attacks:**

```
Snag raised  →  free-text tech log entry  →  rectified  →  entry closed
                        ↓
        (never linked to the 14 other times the same
         signature appeared on other tails / other bases)
                        ↓
        recurring defect  →  repeat MEL deferral  →  audit finding
                        ↓
                    AOG or Level-1
```

Every one of those tech-log entries is *text a human wrote at 2am on a ramp*. Nobody mines it. That is your opening.

---

## 2. The product — four modules

Each module maps to one of the four build types you asked for.

| Module | Build type | What it does |
|---|---|---|
| **NAZAR** ("sight") | Computer vision | Defect detection + severity grading on airframe skin / borescope / component imagery |
| **AJAL** ("term, deadline") | Forecasting + optimisation | Remaining-useful-life prediction and hangar/manpower slot scheduling |
| **DALEEL** ("evidence, guide") | LLM / agentic | Reads free-text snags, clusters recurring defect signatures, drafts the rectification card with regulatory citations |
| **MIRAAT** ("mirror") | Dashboard / BI + premium UI | The control room. Fleet airworthiness picture, floating aviation UI, Hangar/Ramp theme toggle |

---

## 3. Architecture

```
                        ┌─────────────────────────────────┐
                        │   MIRAAT — control room (UI)    │
                        │  Next.js · Motion · Tailwind    │
                        └───────────────┬─────────────────┘
                                        │ REST + SSE
                        ┌───────────────┴─────────────────┐
                        │      FastAPI gateway            │
                        │   auth · rate limit · audit log │
                        └──┬──────────┬──────────┬────────┘
                           │          │          │
            ┌──────────────▼──┐ ┌─────▼──────┐ ┌─▼───────────────┐
            │ NAZAR           │ │ AJAL       │ │ DALEEL          │
            │ vision service  │ │ forecast + │ │ agent service   │
            │ RT-DETR / YOLO  │ │ optimiser  │ │ LLM + RAG       │
            │ + anomaly head  │ │ LGBM+CP-SAT│ │ + tool calls    │
            └──────────────┬──┘ └─────┬──────┘ └─┬───────────────┘
                           │          │          │
                        ┌──▼──────────▼──────────▼──┐
                        │  Postgres + pgvector      │
                        │  defect_events · tails ·  │
                        │  ata_chapters · embeddings│
                        └───────────┬───────────────┘
                                    │
                        ┌───────────▼───────────────┐
                        │  ingestion adapters       │
                        │  SDRS · ASRS · C-MAPSS ·  │
                        │  client tech-log CSV      │
                        └───────────────────────────┘
```

**Design rule that makes it enterprise-credible:** every AI output writes an `evidence` row — model version, input hash, confidence, and the source documents used. No unattributable recommendations. In a regulated industry this single decision is what separates a demo from a pilot.

---

## 4. Datasets — all public, all real

| Dataset | Source | Used by | Why it matters |
|---|---|---|---|
| **FAA SDRS** (Service Difficulty Reporting System) | FAA public download | DALEEL, MIRAAT | Hundreds of thousands of structured defect records with ATA chapter, part number, discrepancy narrative. **This is the core dataset.** It is the closest public proxy to an Indian tech-log corpus. |
| **NASA ASRS** | ASRS public database, CSV export | DALEEL | Rich free-text incident narratives — perfect for training/eval of snag classification and de-identification |
| **NASA C-MAPSS** (turbofan degradation) | NASA PCoE / Kaggle | AJAL | The standard RUL benchmark. FD001–FD004 subsets. |
| **MVTec AD** | MVTec, research licence | NAZAR | Industrial surface anomaly benchmark — pretrain the anomaly head here before fine-tuning on aircraft imagery |
| **MIMII** | Zenodo | NAZAR (stretch) | Machine sound anomaly — optional acoustic channel for engine/APU |
| **Roboflow Universe** — search "aircraft surface defect", "corrosion", "rivet" | Roboflow | NAZAR | Aircraft-specific bounding-box data. *Check each dataset's licence before use.* |
| **OpenSky Network** | opensky-network.org | AJAL | ADS-B history → derive flight hours / cycles per tail as a utilisation proxy |
| **DGCA monthly + annual reports** | dgca.gov.in | MIRAAT | Indian fleet counts, incident stats — grounds the demo in Indian numbers |
| **ATA 100 / iSpec 2200 chapter list** | Public standard | All | The taxonomy the whole product hangs on |

> **Pitch line:** "I built this on FAA SDRS because it's the only open corpus that looks like your tech logs. Point it at your export and it works on day one."

---

## 5. Tech stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend | Next.js 15 (App Router), Tailwind, **Motion** (`motion/react`), Lenis | Production SaaS stack; Motion v12 for 120fps scroll-linked work |
| Charts | Recharts (or visx if you want finer control) | Fast, composable |
| Backend | FastAPI + Pydantic v2 | Type-safe, async, auto OpenAPI docs — reads as engineering-grade |
| DB | Postgres 16 + **pgvector** | One database for relational *and* semantic search. No separate vector DB to justify. |
| Vision | PyTorch, RT-DETR or YOLOv11, PatchCore for anomaly | Detection for known defects, anomaly for unknowns |
| Forecasting | LightGBM + a small 1D-CNN/GRU baseline | LGBM wins on tabular sensor windows and trains in seconds |
| Optimisation | Google OR-Tools CP-SAT | Hangar slot + AME shift assignment |
| LLM | Anthropic API (Claude) via server-side calls | Agentic tool use + long-context document reading |
| Embeddings | `sentence-transformers` (all-MiniLM or BGE-small) | Local, free, fast enough for 500k snags |
| Orchestration | Docker Compose | One `docker compose up` for the demo |
| Deploy | Vercel (frontend) + Render (API + Postgres) | Both already in your toolkit |

---

## 6. Module specifications

### 6.1 NAZAR — vision

**Job:** given an inspection image, return `{defect_type, bbox, severity, ata_chapter_hint, confidence}`.

Two heads, because MRO reality has two cases:

1. **Known defect detection** — supervised detector for dent, crack, corrosion, lightning strike, paint delamination, missing fastener.
2. **Unknown anomaly** — PatchCore-style memory bank trained only on *serviceable* imagery. Anything far from the normal manifold gets flagged for human review. This matters because a supervised model can only find defects you already labelled, and the expensive ones are the novel ones.

```python
# nazar/inference.py
from dataclasses import dataclass
import torch, numpy as np
from PIL import Image

@dataclass
class Finding:
    defect_type: str          # 'corrosion' | 'dent' | 'crack' | 'anomaly'
    bbox: tuple               # (x1, y1, x2, y2) in pixels
    confidence: float
    severity: str             # 'S1' minor .. 'S4' airworthiness-critical
    ata_hint: str | None      # e.g. '53' (fuselage)

class Nazar:
    def __init__(self, detector_path: str, anomaly_bank_path: str, device="cpu"):
        # Supervised detector: finds the defect classes we have labels for
        self.detector = torch.load(detector_path, map_location=device).eval()
        # Memory bank of embeddings from *serviceable* surfaces only.
        # Anything far from this manifold is novel -> flag for human review.
        self.bank = np.load(anomaly_bank_path)
        self.device = device

    def _severity(self, defect_type: str, bbox, image_size) -> str:
        """Severity from defect class + relative area.
        NOTE: this is a triage prior, NOT an airworthiness determination.
        The certifying engineer always makes the final call."""
        x1, y1, x2, y2 = bbox
        area_frac = ((x2 - x1) * (y2 - y1)) / (image_size[0] * image_size[1])
        base = {"crack": 3, "corrosion": 2, "dent": 1,
                "delamination": 1, "anomaly": 2}.get(defect_type, 1)
        bump = 1 if area_frac > 0.05 else 0        # large-area defects escalate
        return f"S{min(base + bump, 4)}"

    def predict(self, img: Image.Image) -> list[Finding]:
        findings = []
        # --- head 1: supervised detection ---
        for cls, box, conf in self.detector.detect(img):
            findings.append(Finding(cls, box, conf,
                                    self._severity(cls, box, img.size),
                                    ATA_HINT.get(cls)))
        # --- head 2: anomaly on patches the detector said nothing about ---
        for box, score in self._patch_anomalies(img):
            if score > self.ANOMALY_THRESHOLD:
                findings.append(Finding("anomaly", box, score,
                                        self._severity("anomaly", box, img.size),
                                        None))
        return findings
```

**Evaluation:** mAP@0.5 for detection, AUROC + pixel-AUPRO for the anomaly head, and — most persuasive to an MRO — **false-negative rate at a fixed 5% false-positive budget**, because in maintenance a missed crack costs infinitely more than a wasted inspection.

---

### 6.2 AJAL — forecasting + optimisation

Two stages. Stage one predicts *when*, stage two decides *what to do about it*.

**Stage 1 — RUL prediction (C-MAPSS)**

```python
# ajal/rul.py
import numpy as np, pandas as pd, lightgbm as lgb

SENSOR_COLS = [f"s{i}" for i in range(1, 22)]

def window_features(df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    """Turn raw per-cycle sensor readings into a feature row per (unit, cycle).
    Degradation shows up as drift and variance change, so we encode both:
    rolling mean (level), rolling std (noise), and slope (trend)."""
    out = []
    for unit, g in df.groupby("unit"):
        g = g.sort_values("cycle")
        feats = {"unit": unit, "cycle": g["cycle"].values}
        for c in SENSOR_COLS:
            r = g[c].rolling(window, min_periods=5)
            feats[f"{c}_mean"] = r.mean().values
            feats[f"{c}_std"]  = r.std().values
            # slope over the window == is this sensor drifting, and how fast
            feats[f"{c}_slope"] = (g[c] - g[c].shift(window)).values / window
        out.append(pd.DataFrame(feats))
    return pd.concat(out, ignore_index=True)

def make_labels(df: pd.DataFrame, cap: int = 125) -> np.ndarray:
    """RUL = cycles remaining until failure, capped.
    Capping matters: a healthy engine at cycle 5 and one at cycle 50 are both
    'fine', and letting the model chase RUL=300 wastes capacity on the easy region."""
    last = df.groupby("unit")["cycle"].transform("max")
    return np.minimum(last - df["cycle"], cap).values

def train(train_df: pd.DataFrame):
    X = window_features(train_df).drop(columns=["unit", "cycle"])
    y = make_labels(train_df)
    model = lgb.LGBMRegressor(
        n_estimators=1200, learning_rate=0.03,
        num_leaves=63, subsample=0.8, colsample_bytree=0.8,
        objective="regression_l1",   # L1: robust to the noisy tail of run-to-failure data
    )
    model.fit(X, y)
    return model
```

**Metric to report:** RMSE *and* the NASA asymmetric scoring function — which penalises **late** predictions far harder than early ones. Say that out loud in the pitch. It shows you understand that in maintenance, optimism is the expensive error.

**Stage 2 — hangar slot + manpower assignment (CP-SAT)**

```python
# ajal/scheduler.py
from ortools.sat.python import cp_model

def schedule(tasks, bays, engineers, horizon_hours: int):
    """tasks: [{id, tail, est_hours, due_by, ata, licence_required, priority}]
       bays:  [{id, capable_ata: set, available_from}]
       engineers: [{id, licences: set, shift_hours}]

    Returns a start hour + bay + engineer for each task, or proves infeasible.
    Infeasibility is itself a finding: it tells the planner they are short a
    licence category before the week begins, not on the morning it breaks."""
    m = cp_model.CpModel()
    starts, ends, intervals, bay_of = {}, {}, {}, {}

    for t in tasks:
        s = m.NewIntVar(0, horizon_hours, f"s_{t['id']}")
        e = m.NewIntVar(0, horizon_hours, f"e_{t['id']}")
        m.Add(e == s + t["est_hours"])
        m.Add(e <= t["due_by"])                    # hard: airworthiness limit
        starts[t["id"]], ends[t["id"]] = s, e
        intervals[t["id"]] = m.NewIntervalVar(s, t["est_hours"], e, f"i_{t['id']}")

        # a task may only run in a bay rated for its ATA chapter
        allowed = [b for b in bays if t["ata"] in b["capable_ata"]]
        bay_of[t["id"]] = m.NewIntVarFromDomain(
            cp_model.Domain.FromValues([b["id"] for b in allowed]), f"b_{t['id']}")

    # one task per bay at a time
    for b in bays:
        m.AddNoOverlap([intervals[t["id"]] for t in tasks
                        if b["ata"] if False else t["ata"] in b["capable_ata"]])

    # objective: finish high-priority work earliest, minimise total lateness risk
    m.Minimize(sum(t["priority"] * ends[t["id"]] for t in tasks))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 20.0
    return solver, solver.Solve(m), starts, bay_of
```

---

### 6.3 DALEEL — the agentic layer (this is the differentiator)

**Job:** read a free-text snag, decide whether it is a *recurrence*, and draft the response with citations.

Pipeline:

```
raw snag text
   ↓ normalise      strip tail numbers, dates, names (privacy + generalisation)
   ↓ classify       ATA chapter (4-digit) + system + symptom  [fine-tuned classifier OR LLM]
   ↓ embed          sentence-transformers → pgvector
   ↓ retrieve       k-NN over historical snags, filtered to same ATA + same type
   ↓ judge          LLM decides: is this the SAME underlying defect signature?
   ↓ act            if recurrence count ≥ N in window W:
                      - raise a Recurring Defect Alert
                      - draft the rectification card
                      - cite the AMM task, the CAR clause, prior work orders
```

The **judge** step is what a keyword search cannot do. "ENG 2 N1 vibration on climb", "no.2 engine rough running above FL200" and "vib indication eng 2, cruise" are the same defect and share almost no keywords.

```python
# daleel/recurrence.py
JUDGE_PROMPT = """You are assisting a Part-145 certifying engineer.

CANDIDATE SNAG:
{candidate}

HISTORICAL SNAGS ON THE SAME AIRCRAFT TYPE AND ATA CHAPTER:
{neighbours}

Decide whether the candidate describes the SAME underlying defect signature as
any historical entry. Two entries match if the failing system, the symptom, and
the operating condition align — even if the wording differs completely.

Return ONLY JSON, no preamble, no markdown fences:
{{"is_recurrence": bool,
  "matched_ids": [int],
  "signature": "<=12 word canonical description",
  "reasoning": "<=40 words",
  "confidence": 0.0-1.0}}
"""

async def judge(candidate: str, neighbours: list[dict]) -> dict:
    resp = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(
            candidate=candidate,
            neighbours="\n".join(f"[{n['id']}] {n['text']}" for n in neighbours))}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return json.loads(text.replace("```json", "").replace("```", "").strip())
```

**Guardrail you must state in the pitch and the report:** DALEEL drafts, it never signs. Every card is `status = DRAFT` until a licensed engineer approves it, and the approval is logged with their licence number. Say this before anyone asks — it's the first question a Part-145 quality manager will have.

**Evaluation:** hand-label ~300 SDRS pairs as recurrence / not. Report precision, recall, F1 against a TF-IDF and a pure-embedding baseline. Your LLM judge should beat both, and you can show exactly where.

---

## 7. MIRAAT — the interface

### 7.1 Design direction

**Subject grounding:** this is a night hangar and a day ramp. The visual language comes from maintenance tags, placards, and inspection lamps — not from generic SaaS.

**Tokens**

```css
:root[data-theme="hangar"] {          /* dark — night shift */
  --surface-0:  #0F1E27;   /* hangar dusk, a real petrol blue, not tinted black */
  --surface-1:  #162C38;   /* floating panel */
  --surface-2:  #1D3846;   /* raised panel */
  --hairline:   #2F4E5F;
  --ink:        #E6EDF1;
  --ink-muted:  #8FA8B5;
  --lamp:       #E8A317;   /* inspection-lamp amber — CAUTION only */
  --tag-us:     #C4342B;   /* unserviceable tag red */
  --tag-serv:   #4E8C6A;   /* serviceable tag green */
}
:root[data-theme="ramp"] {            /* light — day shift */
  --surface-0:  #E4E6E3;   /* brushed aluminium, cool not cream */
  --surface-1:  #F2F3F1;
  --surface-2:  #FFFFFF;
  --hairline:   #C2C8C6;
  --ink:        #0F1E27;
  --ink-muted:  #56666E;
  --lamp:       #B67B0B;   /* darkened for contrast on light */
  --tag-us:     #A62B23;
  --tag-serv:   #3C6E53;
}
```

The colour system is **semantic, not decorative**. Amber never appears unless something needs attention; red never appears unless a tail is unserviceable. A user learns the palette in thirty seconds and then reads status peripherally. That is the whole point.

**Type**

- Display / placards: **Archivo** (and Archivo Narrow for dense table headers) — the condensed grotesque family reads like aircraft placards and cockpit labelling.
- Body: **IBM Plex Sans**.
- Part numbers, ATA codes, work-order IDs: **IBM Plex Mono**. Monospace is justified here because these genuinely are fixed-width codes that engineers scan column-wise — not as a decorative "tech" cue.

**Layout — "bays, not cards"**

```
┌────────────────────────────────────────────────────────────────┐
│ ▸ floating command bar (glass, sticky)      [Hangar ⇄ Ramp]   │
├──────┬─────────────────────────────────────────────────────────┤
│ ATA  │        ╭──────── AIRCRAFT PLAN VIEW (SVG) ────────╮      │
│ rail │        │   zones glow by open-defect severity     │      │
│      │        │   click a zone → drills into ATA chapter │      │
│ 21   │        ╰──────────────────────────────────────────╯      │
│ 27   ├─────────────────────┬──────────────┬─────────────────────┤
│ 32   │ RECURRING SIGNATURES│ RUL WATCHLIST│ HANGAR SCHEDULE     │
│ 49   │ (wide bay)          │ (tall bay)   │ (wide bay)          │
│ 53   ├─────────────────────┴──────────────┴─────────────────────┤
│ 72   │ DALEEL DRAFT QUEUE — cards awaiting engineer sign-off    │
└──────┴─────────────────────────────────────────────────────────┘
```

The ATA rail is numbered because ATA chapters **are** a real numbered taxonomy — the numbering encodes information rather than decorating.

### 7.2 The signature moment

**One** bold element: the aircraft plan view. On load, the airframe outline draws itself once (SVG path stroke-dashoffset, ~900ms), then defect zones fade up staggered by severity — critical first. Every other surface stays quiet and disciplined.

```tsx
// components/AirframePlan.tsx
"use client";
import { motion, useReducedMotion } from "motion/react";

export function AirframePlan({ zones }: { zones: Zone[] }) {
  const reduce = useReducedMotion();
  return (
    <svg viewBox="0 0 800 420" role="img"
         aria-label="Aircraft plan view showing open defects by zone">
      {/* outline draws itself once on mount — the one non-user-triggered motion */}
      <motion.path
        d={AIRFRAME_PATH}
        fill="none" stroke="var(--hairline)" strokeWidth={1.5}
        initial={reduce ? false : { pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
      />
      {zones.map((z, i) => (
        <motion.g key={z.id}
          initial={reduce ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          // critical zones surface first: stagger by severity, not by index
          transition={{ delay: 0.9 + (4 - z.severityRank) * 0.08, duration: 0.3 }}>
          <circle cx={z.x} cy={z.y} r={z.count > 4 ? 14 : 9}
                  fill={z.severityRank >= 3 ? "var(--tag-us)" : "var(--lamp)"}
                  fillOpacity={0.18} stroke="currentColor" strokeWidth={1} />
          <text x={z.x} y={z.y + 4} textAnchor="middle"
                className="font-mono text-[11px] fill-[var(--ink)]">{z.ata}</text>
        </motion.g>
      ))}
    </svg>
  );
}
```

### 7.3 Floating glass — used surgically

`backdrop-filter: blur()` costs 15–30% FPS on mid-tier Android, so it goes on **exactly two** surfaces: the command bar and the drill-in drawer. Never on bays, never on the background.

```css
.glass {
  background: color-mix(in oklab, var(--surface-1) 72%, transparent);
  backdrop-filter: blur(14px) saturate(1.15);
  border: 1px solid color-mix(in oklab, var(--hairline) 60%, transparent);
  box-shadow: 0 12px 32px -12px rgb(0 0 0 / 0.45);
}
@supports not (backdrop-filter: blur(1px)) {
  .glass { background: var(--surface-1); }   /* solid fallback, still correct */
}
```

### 7.4 Theme toggle

Name the themes **Hangar** and **Ramp** (night shift / day shift), not "dark/light" — it costs nothing and immediately signals you know the domain.

```tsx
// components/ThemeToggle.tsx
"use client";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"hangar" | "ramp">("hangar");

  useEffect(() => {
    // Persist across sessions. In a real deployment use a cookie so the server
    // renders the right theme and there is no flash of the wrong palette.
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  return (
    <button
      type="button"
      onClick={() => setTheme(t => (t === "hangar" ? "ramp" : "hangar"))}
      aria-label={`Switch to ${theme === "hangar" ? "Ramp" : "Hangar"} theme`}
      className="glass rounded-full px-3 py-1.5 text-sm focus-visible:outline
                 focus-visible:outline-2 focus-visible:outline-[var(--lamp)]"
    >
      {theme === "hangar" ? "Hangar" : "Ramp"}
    </button>
  );
}
```

> Dark mode is designed first here and light is derived deliberately — the amber and red both darken on the light theme so contrast stays ≥ 4.5:1 rather than being a naive inversion.

### 7.5 Quality floor — non-negotiable before you call it done

- Responsive to 360px; nothing clips or needs horizontal scroll
- Real `<button>`/`<a>`, visible focus rings, logical tab order
- `prefers-reduced-motion` honoured — the airframe draw and all staggers become instant
- Only `transform`/`opacity` animate; no layout-property animation on scroll
- Contrast ≥ 4.5:1 for body text in **both** themes
- The SVG plan view has a text-equivalent table beneath it for screen readers

---

## 8. Repository structure

```
siyana/
├── docker-compose.yml
├── README.md
├── data/
│   ├── raw/                    # SDRS, ASRS, C-MAPSS downloads (gitignored)
│   └── processed/
├── ingest/
│   ├── sdrs.py                 # FAA SDRS → defect_events
│   ├── asrs.py                 # ASRS narratives → snag corpus
│   ├── cmapss.py               # C-MAPSS → sensor windows
│   └── adapters/
│       └── client_techlog.py   # ← the one file a customer swaps
├── services/
│   ├── nazar/                  # vision
│   ├── ajal/                   # rul + scheduler
│   ├── daleel/                 # embeddings, retrieval, judge, card drafting
│   └── gateway/                # FastAPI, auth, audit log
├── db/
│   └── migrations/             # incl. pgvector extension + ivfflat index
├── notebooks/
│   ├── 01_sdrs_eda.ipynb
│   ├── 02_rul_benchmark.ipynb
│   └── 03_recurrence_eval.ipynb
├── web/                        # Next.js — MIRAAT
└── docs/
    ├── ARCHITECTURE.md
    ├── EVALUATION.md
    └── PITCH_ONEPAGER.md
```

---

## 9. Build order (each step ships something demoable)

| Step | Deliverable | Rough effort |
|---|---|---|
| 1 | Ingest SDRS + ASRS into Postgres, EDA notebook showing the recurring-defect long tail | 1 day |
| 2 | DALEEL v1: embeddings + retrieval + LLM judge, evaluated on 300 hand-labelled pairs | 2 days |
| 3 | AJAL RUL on C-MAPSS, RMSE + NASA score vs baselines | 1 day |
| 4 | MIRAAT shell: layout, tokens, theme toggle, airframe plan view wired to real counts | 2 days |
| 5 | NAZAR: PatchCore anomaly head on MVTec, then fine-tune detector on aircraft imagery | 2 days |
| 6 | CP-SAT hangar scheduler + the "you are short a licence category" infeasibility report | 1 day |
| 7 | Audit-log/evidence layer, draft-approval workflow, Docker Compose, deploy | 1 day |
| 8 | Pitch one-pager + 6-minute demo script | half day |

Ship step 4 before step 5. A working interface with two real modules pitches better than four modules and no interface.

---

## 10. Evaluation table (for the report and the viva)

| Module | Metric | Baseline to beat | Target |
|---|---|---|---|
| DALEEL recurrence | Precision / Recall / F1 | TF-IDF cosine; embedding-only k-NN | F1 ≥ 0.85, recall prioritised |
| DALEEL ATA classification | Macro-F1 over top-20 chapters | Majority class; logistic regression on TF-IDF | Macro-F1 ≥ 0.80 |
| AJAL RUL | RMSE + NASA asymmetric score | Last-cycle-constant; linear regression | Beat published LGBM baselines on FD001 |
| AJAL scheduler | Total weighted lateness; solve time | Greedy earliest-due-date | ≥ 20% lateness reduction, < 20s solve |
| NAZAR detection | mAP@0.5; FNR @ 5% FPR | — | FNR is the headline number |
| NAZAR anomaly | Image AUROC; pixel AUPRO | — | AUROC ≥ 0.95 on MVTec subset |
| MIRAAT | Lighthouse perf/a11y; FPS on mid-tier Android | — | ≥ 90 both; 60fps |

---

## 11. Limitations — say these before they ask

1. **SDRS is a US corpus.** Reporting culture, terminology and part naming differ from Indian tech logs. The recurrence model will need re-tuning on client data; the architecture doesn't change, the thresholds do.
2. **No airworthiness authority.** SIYANA triages and drafts. A certifying engineer signs. Nothing in the system releases an aircraft to service.
3. **Aircraft defect imagery is scarce and often proprietary.** The anomaly head exists precisely because you cannot get enough labelled cracks.
4. **C-MAPSS is simulated.** It proves the method, not the numbers. Real engine data has sensor dropouts, maintenance resets and censored histories that C-MAPSS does not.
5. **LLM judge cost and latency.** At 500k historical snags you cannot judge every pair — retrieval narrows to k≈20 first, and that retrieval step is where recall is actually won or lost.
6. **Regulatory acceptance of AI in continuing airworthiness is unsettled.** ICAO and national regulators are still defining what "safe" looks like for learning systems. Position SIYANA as decision *support* with a full audit trail, which is the only posture that survives a Part-145 quality audit today.

---

## 12. Future improvements

- Acoustic channel (MIMII-style) for APU/engine run-up anomaly
- Multilingual snag ingestion — Hindi/Hinglish ramp entries are real and unhandled by every existing tool
- Parts-positioning optimiser: which spare at which base, given predicted RUL across the fleet
- Link to the AMM (aircraft maintenance manual) so the drafted card cites the exact task number
- Fleet-federated learning so multiple operators improve one recurrence model without sharing raw logs
- CAMO module: airworthiness review certificate readiness scoring

---

## 13. Viva Q&A

**Q1. Why not just use keyword search over the tech logs?**
Because the same defect is written five different ways by five engineers. "ENG 2 N1 vib on climb" and "no.2 engine rough running above FL200" share no meaningful keywords but are one signature. Semantic retrieval plus an LLM judge catches that; TF-IDF does not — and the eval in §10 shows exactly by how much.

**Q2. What is a recurring defect and why does it matter legally?**
A defect that reappears after rectification, indicating the root cause was never fixed. It matters because regulators treat repeat defects as evidence of a systemic maintenance-control failure rather than an isolated snag — which is precisely what the DGCA audit finding of 377 out of 754 aircraft represents.

**Q3. Why LightGBM for RUL and not an LSTM?**
Because on C-MAPSS-scale tabular sensor windows, gradient boosting matches or beats sequence models while training in seconds and giving feature importances an engineer can interrogate. I include a GRU baseline to show the comparison rather than assert it. Interpretability is not a nice-to-have in a regulated domain.

**Q4. Why cap RUL at 125 cycles?**
Because an engine at 300 cycles remaining and one at 200 are both simply healthy. Uncapped labels make the model spend capacity fitting a region nobody acts on, at the cost of accuracy near failure, which is the only region that matters.

**Q5. Why does the NASA asymmetric score matter more than RMSE?**
RMSE treats a 10-cycle-early prediction the same as a 10-cycle-late one. Operationally they are not the same: early costs an unnecessary inspection, late costs an in-service failure. The asymmetric score encodes that, so it's the honest headline metric.

**Q6. What stops the LLM from hallucinating a maintenance instruction?**
Three things: it only drafts from retrieved documents and cites them, every output is `status = DRAFT` until a licensed engineer approves it, and the evidence table records the model version, input hash and source documents for every recommendation. The system is designed to be auditable, not autonomous.

**Q7. Why PatchCore alongside a supervised detector?**
A supervised detector can only find defect classes that were labelled. The costly failures are the novel ones. PatchCore learns what serviceable looks like and flags departures from it, so unknown defects surface for human review instead of being silently passed.

**Q8. How does CP-SAT infeasibility help the planner?**
When the model proves no valid schedule exists, that is a finding, not a failure: it says the hangar is short a specific licence category before the week starts. A greedy heuristic would just produce a bad schedule and hide the shortage until the morning it breaks.

**Q9. How would you validate this before a real deployment?**
Shadow mode. Run SIYANA in parallel with the existing process for one quarter without acting on its outputs, then measure how many recurring-defect alerts it raised that the humans later confirmed, and how many confirmed recurrences it missed. Recall on the confirmed set is the go/no-go number.

**Q10. What is the business case in one line?**
Every prevented AOG and every avoided repeat MEL deferral pays for the system many times over — and the same evidence trail that catches recurrences is exactly what an audit asks for.

---

## 14. Pitch pack for your MRO contact

**The six-minute demo script:**

1. **0:00** — Open MIRAAT on the Hangar theme. Airframe draws. "This is one operator's fleet, right now."
2. **0:45** — Click the ATA 72 zone. "Eleven open defects. Four of them are the same signature — the system found that, nobody flagged it."
3. **2:00** — Open the recurrence card. Show the four original snag texts side by side. "No two of these are worded alike."
4. **3:00** — Show the drafted rectification card with citations, and the `DRAFT — awaiting engineer approval` banner. Pause there. Let them notice you built the guardrail before they asked.
5. **4:00** — RUL watchlist: two tails predicted into the window. Show the scheduler moving them into bays and the "short one B1 licence on Thursday" warning.
6. **5:00** — Toggle to Ramp theme. "Day shift uses it on a tablet on the floor."
7. **5:30** — "This runs on public FAA data today. Point it at your tech-log export and it runs on yours. What would you want it to catch first?"

**Ask them for exactly one thing:** an anonymised sample of 200 tech-log entries. That single ask converts a demo into a collaboration, and a collaboration into a referral.

---

## 15. Master prompt for Claude Code

Paste this into Claude Code in an empty repo.

```
Build SIYANA, an AI intelligence platform for aircraft maintenance (MRO) and
continuing airworthiness. Follow this spec exactly; ask before deviating.

CONTEXT
Indian MRO carries a recurring-defect problem: roughly half of a recently audited
fleet showed defects that returned after rectification. Tech-log snags are free
text and are never mined across tails or bases. SIYANA finds those patterns,
predicts component failure, schedules the hangar around it, and presents the
whole picture in one control room.

MODULES
1. NAZAR  — computer vision. Supervised defect detector (RT-DETR or YOLOv11) for
   dent/crack/corrosion/delamination/missing-fastener, PLUS a PatchCore anomaly
   head trained only on serviceable imagery so novel defects surface for review.
   Output: {defect_type, bbox, confidence, severity S1-S4, ata_hint}.
2. AJAL   — forecasting + optimisation. LightGBM RUL model on NASA C-MAPSS with
   rolling mean/std/slope features and RUL capped at 125. Report RMSE AND the
   NASA asymmetric score against a last-cycle-constant baseline and a GRU.
   Then an OR-Tools CP-SAT scheduler assigning tasks to bays and licensed
   engineers, hard-constrained on airworthiness due dates and ATA-capable bays.
   Report infeasibility as a licence-shortage finding, not an error.
3. DALEEL — agentic layer. Normalise and de-identify snag text, classify to
   4-digit ATA chapter, embed with sentence-transformers into pgvector, retrieve
   k=20 same-type same-chapter neighbours, then use the Anthropic API
   (claude-sonnet-4-6) as a judge to decide whether the candidate is the SAME
   defect signature. On recurrence, draft a rectification card citing the source
   snags and work orders. Every card is status=DRAFT until a licensed engineer
   approves; log the approval.
4. MIRAAT — Next.js 15 App Router + Tailwind + Motion (import from "motion/react",
   NOT framer-motion) + Lenis.

STACK
FastAPI + Pydantic v2 gateway; Postgres 16 + pgvector; PyTorch; LightGBM;
OR-Tools; Docker Compose; deploy target Vercel (web) + Render (api + db).

DATA (ingestion adapters, all public)
FAA SDRS (primary defect corpus), NASA ASRS (narratives), NASA C-MAPSS (RUL),
MVTec AD (anomaly pretraining), OpenSky (utilisation proxy).
Include ingest/adapters/client_techlog.py as the single file a customer swaps.

NON-NEGOTIABLE: every AI output writes an evidence row — model version, input
hash, confidence, source document ids. No unattributable recommendation.

UI DIRECTION
Themes named "hangar" (dark, default, designed first) and "ramp" (light),
toggled via data-theme on <html>. Tokens:
  hangar: surface-0 #0F1E27, surface-1 #162C38, surface-2 #1D3846,
          hairline #2F4E5F, ink #E6EDF1, ink-muted #8FA8B5,
          lamp #E8A317, tag-us #C4342B, tag-serv #4E8C6A
  ramp:   surface-0 #E4E6E3, surface-1 #F2F3F1, surface-2 #FFFFFF,
          hairline #C2C8C6, ink #0F1E27, ink-muted #56666E,
          lamp #B67B0B, tag-us #A62B23, tag-serv #3C6E53
Colour is SEMANTIC: amber only for attention, red only for unserviceable.
Type: Archivo (display/placards), IBM Plex Sans (body), IBM Plex Mono (part
numbers, ATA codes, work-order ids only).
Layout: left rail of ATA chapters; floating glass command bar; a top-down
aircraft SVG plan view as the hero where zones glow by open-defect severity and
click-through drills into that ATA chapter; below it bays (varying sizes, not
identical cards) for Recurring Signatures, RUL Watchlist, Hangar Schedule, and
the DALEEL draft queue.
ONE signature motion: the airframe outline draws itself on load (pathLength,
~900ms), then zones fade in staggered by SEVERITY not index. Nothing else
animates unless the user triggers it.
Glassmorphism on exactly two surfaces: command bar and drill-in drawer, with a
solid @supports fallback. Animate only transform/opacity.

QUALITY BAR — all must pass:
responsive to 360px; real button/a elements with visible focus rings; logical
tab order; prefers-reduced-motion honoured (draw and staggers become instant);
contrast >= 4.5:1 for body text in BOTH themes; 60fps on mid-tier Android;
the SVG plan view has a text-equivalent table for screen readers.

BUILD ORDER
Ship in this sequence, each step runnable: (1) ingestion + EDA notebook,
(2) DALEEL with eval on 300 hand-labelled pairs, (3) AJAL RUL with benchmark
table, (4) MIRAAT shell wired to real counts, (5) NAZAR, (6) CP-SAT scheduler,
(7) evidence/audit layer + Docker Compose + deploy.
Do not start step 5 until step 4 renders with real data.

Write docs/ARCHITECTURE.md, docs/EVALUATION.md and a README with exact run
commands. No placeholders, no TODOs left in shipped files.
```

---

## 16. What to submit (academic version)

- `docs/ARCHITECTURE.md` — the diagram in §3 plus data-flow narrative
- `docs/EVALUATION.md` — the table in §10 with your actual numbers and the baseline comparisons
- Three notebooks: SDRS EDA, RUL benchmark, recurrence evaluation
- Deployed URL + GitHub repo link
- A 10-slide deck: problem (with the DGCA audit numbers), architecture, one screenshot per module, evaluation table, limitations, roadmap
- The viva answers in §13, rehearsed
