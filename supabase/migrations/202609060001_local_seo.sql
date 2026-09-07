CREATE TABLE IF NOT EXISTS local_seo_generations (
    id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL,
    status TEXT NOT NULL,
    prompt TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS local_seo_created_idx ON local_seo_generations(created_at DESC);
ALTER TABLE local_seo_generations ENABLE ROW LEVEL SECURITY;
