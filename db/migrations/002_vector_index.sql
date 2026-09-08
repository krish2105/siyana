-- ivfflat needs rows to build useful lists; created after schema so ingest can run first.
-- lists = 100 suits 10k-1M rows. Rebuild with REINDEX after large loads.
CREATE INDEX IF NOT EXISTS ix_snags_embedding
  ON snags USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
