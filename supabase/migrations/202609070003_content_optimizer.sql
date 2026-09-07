CREATE TABLE IF NOT EXISTS content_optimizer_runs (
    id TEXT PRIMARY KEY,
    request_json TEXT NOT NULL,
    status TEXT NOT NULL,
    stage TEXT NOT NULL,
    progress INTEGER NOT NULL,
    result_json TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_content_optimizer_created_at
    ON content_optimizer_runs (created_at DESC);

ALTER TABLE content_optimizer_runs ENABLE ROW LEVEL SECURITY;
