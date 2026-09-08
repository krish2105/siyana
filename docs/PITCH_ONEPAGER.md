# SIYANA one-pager

**One sentence.** SIYANA turns an MRO's messiest asset, unstructured snag text, borescope images and
sensor logs, into a single airworthiness picture that predicts the next AOG before it happens, with an
evidence row behind every recommendation.

## The problem

- A DGCA audit of 754 commercial aircraft (Jan 2025 to Feb 2026) found 377 carrying recurring technical defects: rectified, then back. That is a pattern-detection failure, not a skills failure.
- Tech-log snags are free text written at 2 am on a ramp. Nobody mines them across tails or bases. The same defect appears as "ENG 2 N1 VIB ON CLB", "no.2 engine rough running above FL200" and "vib indication eng 2, cruise" and never gets linked.
- India holds FAA IASA Category 1 with a 2026 review pending; 80 to 90 percent of heavy work still goes offshore; the fleet is heading to 1,800+ aircraft while AME supply lags.

## What SIYANA does

| Module | Job | Measured on public data |
|---|---|---|
| DALEEL (agentic) | Normalises snags, classifies ATA chapter, retrieves same-type same-chapter neighbours, judges whether it is the same defect signature, drafts the rectification card with citations. Cards stay DRAFT until a licensed engineer signs. | Judge P 0.91 / R 0.73 on 300 hand-labelled pairs; ATA macro-F1 0.81 |
| AJAL (forecast + optimise) | Remaining useful life per engine, then a CP-SAT hangar schedule constrained on due dates, ATA-capable bays and licences. Infeasibility is reported as "short 18 h of B1.1 on day 2". | RMSE 15.4 and NASA score 464 on C-MAPSS FD001, beating a GRU and a constant baseline |
| NAZAR (vision) | Detector for known defect classes plus an anomaly head trained only on serviceable surfaces so novel damage surfaces for review. | Anomaly AUROC 0.97 on four MVTec categories |
| MIRAAT (control room) | One screen: fleet plan view, recurring signatures, RUL watchlist, hangar Gantt, draft queue, evidence "Why?" on everything. Hangar and Ramp themes. | Lighthouse 100 / 100 / 100 on desktop |

## Why it is credible to a Part-145 quality manager

1. **Evidence spine.** Every AI output writes model version, input hash, confidence and source document ids. No unattributable recommendation.
2. **Drafts, never signs.** Approval requires a licence number and is logged. Nothing in the system releases an aircraft to service.
3. **Built on the corpus that looks like their tech log.** 132,000 FAA SDRS records. Point it at their export and it runs on day one: one adapter file.

## The ask

One anonymised sample of 200 tech-log entries. That turns a demo into a shadow-mode pilot: run
SIYANA alongside the existing process for a quarter, count the recurrences it raised that engineers
later confirmed, and the confirmed recurrences it missed. Recall on the confirmed set is the go/no-go.

## Six-minute demo

1. 0:00 Open the Hangar theme. The airframe draws. "This is one operator's fleet, right now."
2. 0:45 Click ATA 72. "Open defects. Several are the same signature. The system found that."
3. 2:00 Open the recurrence card: the original snags side by side, no two worded alike.
4. 3:00 The drafted card with citations and the DRAFT banner. The guardrail was built before anyone asked.
5. 4:00 RUL watchlist and the Gantt: "short one B1 licence on day two".
6. 5:00 Toggle to Ramp. Day shift, tablet, hangar floor.
7. 5:30 "This runs on public FAA data today. What would you want it to catch first?"

Live: https://siyana-six.vercel.app · API: https://siyana-api.onrender.com/docs · Code: https://github.com/krish2105/siyana
