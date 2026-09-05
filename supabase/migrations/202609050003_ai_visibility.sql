CREATE TABLE IF NOT EXISTS ai_visibility_audits (
  id TEXT PRIMARY KEY, requested_url TEXT NOT NULL, normalized_origin TEXT,
  business_name TEXT, product_name TEXT, audit_goal TEXT,
  important_urls_json TEXT NOT NULL DEFAULT '[]', crawl_limit INTEGER NOT NULL,
  status TEXT NOT NULL, stage TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
  result_json TEXT, warnings_json TEXT NOT NULL DEFAULT '[]', error TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_visibility_created_at ON ai_visibility_audits (created_at DESC);
ALTER TABLE ai_visibility_audits ENABLE ROW LEVEL SECURITY;
