# SIYANA scorecard, 2026-09-09

Scored after the first public deployment. Three lenses, each out of 100, then a weighted overall.
Every claim links to something you can open.

| Lens | Score | One-line verdict |
|---|---|---|
| Real deployed MVP | **86** | Web, API and database are live on public URLs with the real 107k-snag corpus, every module answers, and the judge runs end to end. Free-tier limits cap what the hosted API can serve. |
| SaaS ready | **64** | Evidence trail, licensed approvals, API-key auth, rate limits, request ids, CI, weekly ingest and uptime checks exist. No tenancy, login, billing or SLA yet. |
| Pitch ready | **90** | Pitch page, one-pager, six-minute demo mode, measured numbers against baselines, viva answers, live links. The Claude judge result is the one number a sharp listener will ask for. |
| **Overall (0.4 / 0.3 / 0.3)** | **81** | |

## What is live

| URL | What you get |
|---|---|
| https://siyana-six.vercel.app | Control room: 24 fleet tails, 218 open defects in the last 90 days (corpus current to 7 Sep 2026, refreshed weekly by GitHub Actions), 255 signatures, 14 drafts awaiting sign-off, RUL watchlist, hangar Gantt with the licence-shortage finding |
| https://siyana-six.vercel.app/pitch | Pitch page with live counts pulled from the API |
| https://siyana-api.onrender.com/docs | OpenAPI reference; `/health/ready` reports corpus counts, judge, backend and auth mode |
| https://github.com/krish2105/siyana | Public repository, CI badge, release `models-v1` with the trained weights |

Verified on 2026-09-09: Lighthouse on the live site scores 93 / 100 / 100 / 100 (desktop) and 90 / 100 / 100 / 100 (360 px mobile, simulated 4G) with zero layout shift; CI is green; the weekly ingest workflow ran against production; `GET /fleet/summary` returns the fleet; `POST /daleel/judge` on a pasted snag returns 20 neighbours, a verdict and an evidence id; the Gantt shows *Short 31 h of B1.1 on day 2: 115 h due, 84 h rostered*; the weekly ingest workflow backfilled January to August 2026 and runs every Monday.

## Where the points went

**Deployed MVP, minus 16.**
- The API runs on Render's free 512 MB plan. Vision inference (`SIYANA_ENABLE_NAZAR=0`) and the 400 MB ATA classifier (`SIYANA_ATA_CLASSIFIER=0`) are switched off there; both run locally and in Docker Compose. A paid plan needs a card on the Render account, which only you can add. (-8)
- Cold start after 15 minutes idle is about 30 s; the uptime workflow pings every 10 minutes to hide it, and the first judge call downloads the ONNX model (-2).
- The database is a dedicated `siyana` schema inside your existing free Supabase project, holding the narrow-body corpus (132k snags including the 2026 backfill, 337 MB, no ANN index; retrieval is a sequential scan of about a second). Free Supabase projects pause after a week without traffic; the uptime workflow's readiness call keeps it active. (-4)
- The detector is trained on stand-in imagery (mAP 0.43). (-2)

**SaaS ready, minus 36.**
- No user accounts, roles or tenancy: one fleet, one open deployment. (-14)
- No billing, plans or usage metering. (-8)
- No SLA tooling: no error tracker, no alerting beyond the GitHub uptime job, no backups beyond Supabase's daily ones. (-6)
- Approval auth is optional and off in production because the web host cannot yet hold the key server-side. (-4)
- No customer onboarding flow for the CSV adapter beyond the documented contract. (-4)

**Pitch ready, minus 10.**
- The Claude judge (`claude-sonnet-4-6`) has not been scored; the table shows the embedding fallback at F1 0.81. Adding the key and running one command fills the row. (-6)
- No screenshots or a recorded walkthrough in the repo for someone who cannot open the live site. (-2)
- The detector row in the evaluation is honest but weak. (-2)

## Path to 95 and above, in order of value per hour

1. **Run the Claude judge** (10 min). Put `ANTHROPIC_API_KEY` in `.env`, run `python -m services.daleel.eval evaluate`, commit `data/metrics/daleel_recurrence.json`, then set the key on Render so the live judge is Claude. Closes the biggest pitch gap and likely lifts recurrence recall on the paraphrase stratum.
2. **Add a card to Render and move the API to the 2 GB plan** (5 min plus $25/mo). Flip `SIYANA_ENABLE_NAZAR=1` and `SIYANA_ATA_CLASSIFIER=0` to `1`; vision and ATA classification then serve live. Optionally create a Render Postgres and restore `data/` with the full 150k corpus and the ivfflat index.
3. **Accounts and tenancy** (2 to 3 days). Auth.js or Clerk on the web, an `operators` table, `operator_id` on tails, snags, cards and evidence, row-level security in Postgres, the API key per operator. This is the single largest SaaS gap.
4. **Server-side key handling on the web** (1 hour). Set `SIYANA_API_KEY` on Vercel and route approvals through a Next route handler that attaches it; then enable the key on Render.
5. **Error tracking and alerting** (1 hour). Sentry on API and web, Render health-check path set to `/health/ready`, alert on the uptime workflow.
6. **Real aircraft defect imagery** (partner dependent). A licensed set of skin and borescope images with boxes; the training loop is ready.
7. **Onboarding** (1 day). A `/onboard` page that validates a customer CSV against the adapter contract, previews the mapped rows, and runs the refresh pipeline.
8. **Billing** (1 to 2 days). Stripe with two plans (fleet size tiers) and metering on judge calls.
9. **Walkthrough assets** (1 hour). Screenshots in `docs/figures/`, a two-minute recording linked from the README.

Items 1, 2, 4 and 9 alone take the overall to about 90; item 3 is what makes it a product rather than a deployed demo.
