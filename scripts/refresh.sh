#!/usr/bin/env bash
# Rebuild every derived artefact after an ingest. Safe to re-run; each step is idempotent.
# Usage: scripts/refresh.sh [--skip-classifier]
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python

echo "== 1. embed new snags";            $PY -m services.daleel.embed
echo "== 2. rebuild vector index";       psql "${DATABASE_URL_PSQL:-postgresql://siyana:siyana@localhost:5432/siyana}" -c "REINDEX INDEX ix_snags_embedding;"
echo "== 3. select demo fleet";          $PY -m ingest.fleet --families A320 A321 B737 --n 24
echo "== 4. recurrence scan";            $PY -m services.daleel.recurrence --limit 600
echo "== 5. draft cards for top signatures"
for id in $(psql "${DATABASE_URL_PSQL:-postgresql://siyana:siyana@localhost:5432/siyana}" -tAc "select s.id from signatures s left join cards c on c.signature_id=s.id where c.id is null order by s.count desc limit 8"); do
  $PY - "$id" <<'PYEOF'
import sys
from services.common.db import SessionLocal
from services.daleel.cards import draft_card
from services.daleel.judge import get_judge
with SessionLocal() as db:
    c = draft_card(db, int(sys.argv[1]), get_judge().model_version); db.commit(); print("   card", c.id, c.status, c.body["title"][:70])
PYEOF
done
echo "== 6. RUL watchlist";              $PY -m services.ajal.watchlist
echo "== 7. hangar schedule";            $PY -m services.ajal.seed_schedule
if [[ "${1:-}" != "--skip-classifier" ]]; then
  echo "== 8. ATA classifier (several minutes)"; $PY -m services.daleel.ata_classifier
fi
echo "== done"
