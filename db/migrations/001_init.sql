-- SIYANA schema. Applied by db/migrate.py in filename order.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS ingest_runs (
  id SERIAL PRIMARY KEY,
  source VARCHAR(32) NOT NULL,
  source_url TEXT NOT NULL,
  payload_sha256 VARCHAR(64) NOT NULL,
  rows INTEGER NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'ok',
  detail TEXT,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ata_chapters (
  code VARCHAR(4) PRIMARY KEY,
  chapter VARCHAR(2) NOT NULL,
  title TEXT NOT NULL,
  system TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ata_chapters_chapter ON ata_chapters(chapter);

CREATE TABLE IF NOT EXISTS tails (
  registration VARCHAR(16) PRIMARY KEY,
  aircraft_type VARCHAR(32) NOT NULL,
  operator VARCHAR(64),
  base VARCHAR(8),
  status VARCHAR(16) NOT NULL DEFAULT 'serviceable' CHECK (status IN ('serviceable','unserviceable')),
  in_fleet BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_tails_type ON tails(aircraft_type);
CREATE INDEX IF NOT EXISTS ix_tails_in_fleet ON tails(in_fleet);

CREATE TABLE IF NOT EXISTS evidence (
  id SERIAL PRIMARY KEY,
  module VARCHAR(16) NOT NULL,
  model_version TEXT NOT NULL,
  input_sha256 VARCHAR(64) NOT NULL,
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  source_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_evidence_module ON evidence(module);
CREATE INDEX IF NOT EXISTS ix_evidence_hash ON evidence(input_sha256);

CREATE TABLE IF NOT EXISTS snags (
  id BIGSERIAL PRIMARY KEY,
  tail VARCHAR(16) REFERENCES tails(registration),
  source VARCHAR(16) NOT NULL,
  source_doc_id VARCHAR(64) NOT NULL,
  occurred_at TIMESTAMPTZ,
  raw_text TEXT NOT NULL,
  norm_text TEXT,
  ata_code VARCHAR(4) REFERENCES ata_chapters(code),
  ata_source VARCHAR(16),
  defect_type VARCHAR(32),
  part_name TEXT,
  part_number TEXT,
  aircraft_type VARCHAR(32),
  embedding vector(384),
  ingest_run_id INTEGER REFERENCES ingest_runs(id),
  UNIQUE (source, source_doc_id)
);
CREATE INDEX IF NOT EXISTS ix_snags_tail ON snags(tail);
CREATE INDEX IF NOT EXISTS ix_snags_source ON snags(source);
CREATE INDEX IF NOT EXISTS ix_snags_ata ON snags(ata_code);
CREATE INDEX IF NOT EXISTS ix_snags_type ON snags(aircraft_type);
CREATE INDEX IF NOT EXISTS ix_snags_occurred ON snags(occurred_at);

CREATE TABLE IF NOT EXISTS signatures (
  id SERIAL PRIMARY KEY,
  ata_code VARCHAR(4) NOT NULL,
  aircraft_type VARCHAR(32),
  canonical TEXT NOT NULL,
  member_snag_ids BIGINT[] NOT NULL,
  count INTEGER NOT NULL,
  first_seen TIMESTAMPTZ,
  last_seen TIMESTAMPTZ,
  evidence_id INTEGER NOT NULL REFERENCES evidence(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_signatures_ata ON signatures(ata_code);

CREATE TABLE IF NOT EXISTS defect_events (
  id BIGSERIAL PRIMARY KEY,
  snag_id BIGINT NOT NULL REFERENCES snags(id),
  tail VARCHAR(16) REFERENCES tails(registration),
  ata_code VARCHAR(4),
  severity VARCHAR(2) NOT NULL DEFAULT 'S1' CHECK (severity IN ('S1','S2','S3','S4')),
  opened_at TIMESTAMPTZ,
  closed_at TIMESTAMPTZ,
  work_order_id VARCHAR(32),
  signature_id INTEGER REFERENCES signatures(id)
);
CREATE INDEX IF NOT EXISTS ix_defect_events_snag ON defect_events(snag_id);
CREATE INDEX IF NOT EXISTS ix_defect_events_tail ON defect_events(tail);
CREATE INDEX IF NOT EXISTS ix_defect_events_ata ON defect_events(ata_code);
CREATE INDEX IF NOT EXISTS ix_defect_events_signature ON defect_events(signature_id);

CREATE TABLE IF NOT EXISTS cards (
  id SERIAL PRIMARY KEY,
  signature_id INTEGER NOT NULL REFERENCES signatures(id),
  status VARCHAR(8) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','APPROVED','REJECTED')),
  body JSONB NOT NULL,
  evidence_id INTEGER NOT NULL REFERENCES evidence(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_cards_signature ON cards(signature_id);
CREATE INDEX IF NOT EXISTS ix_cards_status ON cards(status);

CREATE TABLE IF NOT EXISTS approvals (
  id SERIAL PRIMARY KEY,
  card_id INTEGER NOT NULL REFERENCES cards(id),
  engineer_name TEXT NOT NULL,
  licence_number VARCHAR(64) NOT NULL CHECK (length(licence_number) > 0),
  decision VARCHAR(8) NOT NULL CHECK (decision IN ('APPROVED','REJECTED')),
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_approvals_card ON approvals(card_id);

CREATE TABLE IF NOT EXISTS rul_predictions (
  id SERIAL PRIMARY KEY,
  tail VARCHAR(16) NOT NULL REFERENCES tails(registration),
  engine_pos INTEGER NOT NULL,
  unit_id INTEGER NOT NULL,
  dataset VARCHAR(8) NOT NULL,
  predicted_rul DOUBLE PRECISION NOT NULL,
  series JSONB NOT NULL DEFAULT '[]'::jsonb,
  evidence_id INTEGER NOT NULL REFERENCES evidence(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_rul_tail ON rul_predictions(tail);

CREATE TABLE IF NOT EXISTS bays (
  id VARCHAR(8) PRIMARY KEY,
  name TEXT NOT NULL,
  capable_ata VARCHAR(2)[] NOT NULL,
  available_from INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS engineers (
  id VARCHAR(8) PRIMARY KEY,
  name TEXT NOT NULL,
  licences VARCHAR(8)[] NOT NULL,
  shift_hours INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS maint_tasks (
  id VARCHAR(16) PRIMARY KEY,
  tail VARCHAR(16) NOT NULL REFERENCES tails(registration),
  ata_code VARCHAR(4) NOT NULL,
  est_hours INTEGER NOT NULL,
  due_by INTEGER NOT NULL,
  priority INTEGER NOT NULL,
  licence_required VARCHAR(8) NOT NULL,
  description TEXT NOT NULL,
  defect_event_id BIGINT REFERENCES defect_events(id)
);
CREATE INDEX IF NOT EXISTS ix_maint_tasks_tail ON maint_tasks(tail);

CREATE TABLE IF NOT EXISTS schedule_runs (
  id SERIAL PRIMARY KEY,
  status VARCHAR(16) NOT NULL,
  objective INTEGER,
  solve_seconds DOUBLE PRECISION NOT NULL,
  horizon_hours INTEGER NOT NULL,
  assignments JSONB NOT NULL,
  licence_shortage JSONB NOT NULL DEFAULT '[]'::jsonb,
  baseline JSONB NOT NULL DEFAULT '{}'::jsonb,
  evidence_id INTEGER NOT NULL REFERENCES evidence(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS nazar_findings (
  id SERIAL PRIMARY KEY,
  image_sha256 VARCHAR(64) NOT NULL,
  filename TEXT,
  findings JSONB NOT NULL,
  evidence_id INTEGER NOT NULL REFERENCES evidence(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_nazar_hash ON nazar_findings(image_sha256);

CREATE TABLE IF NOT EXISTS utilisation (
  id BIGSERIAL PRIMARY KEY,
  icao24 VARCHAR(8) NOT NULL,
  callsign VARCHAR(12),
  origin_country TEXT,
  velocity DOUBLE PRECISION,
  baro_altitude DOUBLE PRECISION,
  on_ground BOOLEAN,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ingest_run_id INTEGER REFERENCES ingest_runs(id)
);
CREATE INDEX IF NOT EXISTS ix_utilisation_icao ON utilisation(icao24);

CREATE TABLE IF NOT EXISTS recurrence_labels (
  pair_id INTEGER PRIMARY KEY,
  snag_a BIGINT NOT NULL REFERENCES snags(id),
  snag_b BIGINT NOT NULL REFERENCES snags(id),
  stratum VARCHAR(16) NOT NULL,
  label INTEGER NOT NULL CHECK (label IN (0,1)),
  labeller TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
