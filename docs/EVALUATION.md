# SIYANA evaluation

Every number below is produced by a command in this repository and stored under `data/metrics/`.
Where a result falls short of the target it is reported as measured, with the reason.

| Module | Metric | Baseline(s) | Result | Target (master spec) |
|---|---|---|---|---|
| DALEEL recurrence | Precision / Recall / F1 on 240 held-out labelled pairs | TF-IDF cosine F1 0.84; embedding cosine F1 0.86 (both at permissive tuned thresholds) | Production embedding judge: **P 0.91 · R 0.73 · F1 0.81** | F1 ≥ 0.85, recall prioritised. Not met by the fallback judge; see notes |
| DALEEL ATA classification | Macro-F1 over the 20 most frequent 4-digit codes | Majority class 0.02; char n-gram Complement NB 0.60 | **0.81** (4-digit accuracy 0.78, chapter accuracy 0.91) | Macro-F1 ≥ 0.80. Met |
| AJAL RUL (C-MAPSS FD001) | RMSE · NASA asymmetric score | Last-cycle-constant 41.94 · 33,354; GRU 16.92 · 954.6 | **LightGBM 15.36 · 463.9** | Beat published LightGBM baselines on FD001. In range of published tabular results (RMSE 13–17) |
| AJAL scheduler | Priority-weighted lateness · solve time | Greedy earliest-due-date 990 | **CP-SAT 0 (relaxed plan) · 0.03 s**, infeasibility reported as a licence finding | ≥ 20% lateness reduction, < 20 s. Met |
| NAZAR anomaly (PatchCore) | Image AUROC · pixel AUPRO, 4 MVTec categories | none | **mean AUROC 0.970 · mean AUPRO 0.851** | AUROC ≥ 0.95. Met |
| NAZAR detector (RT-DETR) | mAP@0.5 · FNR at 5% FPR (image level) | none | **mAP 0.43 · FNR 0.90** on 61 val images | FNR is the headline. Not met; see notes |
| MIRAAT | Lighthouse (production build) | none | **Desktop: perf 100 · a11y 100 · best practices 100. Mobile 360 px, simulated throttling: perf 89 · a11y 100 · best practices 100** | ≥ 90 perf and a11y. Met on desktop; mobile performance one point short under simulated 4G, see notes |

## DALEEL: recurrence judge

**Set.** 300 SDRS pairs built by `services/daleel/eval.py build` in three strata: 100 nearest-neighbour
pairs (same 2-digit chapter, same aircraft family, cosine ≥ 0.6), 100 random same-chapter same-family
pairs, 100 random cross-chapter pairs. 60 pairs form a dev split used only to tune thresholds; the
240 others are the test set (83 positives).

**Labelling rubric.** Label 1 when the failing component or system, the failure mode, and the
operating condition align, even if the wording differs completely. Location differences within the
same structural element (left/right, adjacent stations, a different rib of the same stabiliser) do
not break a match. Different failure modes on the same component (chafed vs corroded intercostal),
different components in the same system (fan air valve vs anti-ice duct), and different symptoms
(reservoir low level vs gear not retracting) are label 0. All 300 pairs were labelled by reading
them; the labeller is recorded in `data/labels/recurrence_pairs.csv`. Positives: 85 of 100
nearest-neighbour pairs, 21 of 100 same-chapter pairs, 0 of 100 cross-chapter pairs.

**Results on the 240 test pairs** (`data/metrics/daleel_recurrence.json`):

| Method | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|
| TF-IDF cosine (word 1–2 grams) | 0.10 (dev-tuned) | 0.76 | 0.93 | 0.84 |
| all-MiniLM-L6-v2 cosine | 0.59 (dev-tuned) | 0.80 | 0.93 | 0.86 |
| **EmbeddingJudge (production)** | 0.775 | **0.91** | **0.73** | **0.81** |
| ClaudeJudge (claude-sonnet-4-6) | n/a | not run: no `ANTHROPIC_API_KEY` in this environment | | |

Per stratum, the production judge scores F1 0.89 on nearest-neighbour pairs and 0.11 on same-chapter
pairs: the recall gap is entirely in true paraphrases whose cosine falls below the threshold.

**Why the production threshold is 0.775 and not the F1-optimal 0.59.** The evaluation is pairwise,
but production compares each candidate against 20 same-chapter neighbours. A threshold of 0.59 would
merge most of a chapter into one signature and raise false alerts to a certifying engineer. The
production point is the highest-recall threshold whose dev precision is at least 0.90; the full sweep
is in the metrics file and plotted in `notebooks/03_recurrence_eval.ipynb`.

**What the LLM judge is for.** The same-chapter stratum is the case the Claude judge exists to cover.
`services/daleel/eval.py evaluate` adds a `claude_judge` row to the table automatically when
`ANTHROPIC_API_KEY` is set; every verdict it produces is stamped `anthropic/claude-sonnet-4-6` in
the evidence table, so results from the two judges are never mixed.

## DALEEL: ATA classification

Trained on 132,459 SDRS narratives whose JASC code gives a 4-digit ATA label (stratified 80/20 split,
125 classes with at least 40 examples). `data/metrics/daleel_ata.json`.

| Model | Macro-F1 top-20 | 4-digit accuracy |
|---|---|---|
| Majority class (5300) | 0.02 | 0.16 |
| Char n-gram Complement Naive Bayes | 0.60 | 0.66 |
| **TF-IDF word + char n-grams, logistic regression** | **0.81** | **0.78** (chapter-level 0.91) |

## AJAL: remaining useful life

FD001, 100 train and 100 test engines, RUL capped at 125, 30-cycle rolling mean, std and slope
features over the 14 informative sensors. `data/metrics/ajal_rul.json`, `notebooks/02_rul_benchmark.ipynb`.

| Model | RMSE | NASA score | Fit time |
|---|---|---|---|
| Last-cycle-constant (train-mean capped RUL) | 41.94 | 33,354 | 0 s |
| GRU (2 layers, hidden 64, 30-cycle windows) | 16.92 | 954.6 | 31 s |
| **LightGBM (L1, 1,200 trees)** | **15.36** | **463.9** | 17 s |

On engines within 30 cycles of failure, the region that triggers a hangar slot, LightGBM's RMSE is
5.6. The NASA score gap between LightGBM and the GRU is larger than the RMSE gap because the GRU's
errors skew late, which the score penalises harder. C-MAPSS is simulated: it proves the method, not
the numbers.

## AJAL: hangar scheduler

22 tasks built from the fleet's open defect events (hours by chapter, due dates by severity rank),
4 bays with ATA capability sets, 6 engineers with B1.1 / B2 licences and day shifts. CP-SAT with hard
due dates, bay capability, licence and shift constraints, minimising priority-weighted completion.

| Solver | Status | Weighted lateness | Solve time |
|---|---|---|---|
| Greedy earliest-due-date | tasks unplaced or late | 990 | < 0.01 s |
| **CP-SAT** | infeasible; relaxed plan stored | **0** | **0.03 s** |

The infeasibility is the finding: *Short 18 h of B1.1 on day 2: 102 h due, 84 h rostered*. The
Gantt shows the relaxed plan and the finding; a planner sees the licence gap before the week starts.

## NAZAR: vision

**Anomaly head (PatchCore).** wide_resnet50_2 layers 2+3, 10% coreset, fitted on `train/good`
only, scored on the MVTec test split. `data/metrics/nazar.json`.

| Category | Image AUROC | Pixel AUPRO | FNR @ 5% FPR |
|---|---|---|---|
| metal_nut | 0.998 | 0.901 | 0.022 |
| screw | 0.924 | 0.876 | 0.303 |
| grid | 0.960 | 0.836 | 0.088 |
| tile | 1.000 | 0.792 | 0.000 |
| **mean** | **0.970** | **0.851** | |

**Detector (RT-DETR r50vd, fine-tuned 8 epochs).** No licensed aircraft defect box set was
retrievable, so the detector is trained on 185 images whose boxes are derived from MVTec masks and
mapped to the SIYANA classes (`ingest/nazar_boxes.py`). On the 61 held-out images: mAP@0.5 0.43
(corrosion 0.69, missing-fastener 0.67, crack 0.34, delamination 0.27, dent 0.19); image AUROC 0.73;
FNR at 5% FPR 0.90. This is the honest state of a detector with fewer than 200 training images and it
is why NAZAR's inference merges both heads: the anomaly head, which needs no defect labels, catches
what the detector misses and marks it for review. The training loop and evaluation are what an
operator reuses on their own borescope and skin imagery; these weights are not.

## MIRAAT: interface

Lighthouse 12, headless Chrome, production build served by `next start`. Reports in `data/logs/`.

| Form factor | Performance | Accessibility | Best practices | LCP | TBT | CLS |
|---|---|---|---|---|---|---|
| Desktop, local production server | 100 | 100 | 100 | 0.7 s | 0 ms | 0 |
| Mobile 360 px, local production server, simulated 4G | 89 | 100 | 100 | 3.6 s | 140 ms | 0 |
| Desktop, live site (siyana-six.vercel.app, API on Render) | 93 | 100 | 100 | 0.6 s | 0 ms | 0 |
| Mobile 360 px, live site, simulated 4G | 90 | 100 | 100 | 2.9 s | 130 ms | 0 |

Two earlier runs showed CLS 0.9: first the command bar wrapping as the placard font swapped in, then,
on Vercel only, the header streaming in behind a Suspense boundary after the body had painted. The bar
no longer wraps at desktop widths, the hero has a fixed box for both the SVG and the 3D scene, and the
shell renders inline, so the shift is gone on both hosts. The one remaining
mobile point is largest-contentful-paint under simulated 4G on a page that ships live fleet data; the
3D bundle is never loaded below 768 px. Contrast for every text/background token pair in both themes
is checked by `web/scripts/contrast.mjs` (all text pairs ≥ 4.5:1).

## Reproduce

```bash
.venv/bin/python -m services.daleel.eval evaluate
.venv/bin/python -m services.daleel.ata_classifier
.venv/bin/python -m services.ajal.benchmark
.venv/bin/python -m services.ajal.seed_schedule
.venv/bin/python -m services.nazar.eval
.venv/bin/python -c "from services.nazar.eval import evaluate_detector; evaluate_detector()"
cd web && npm run build && npm run start -- -p 3001 & npx lighthouse http://localhost:3001 --preset=desktop
```
