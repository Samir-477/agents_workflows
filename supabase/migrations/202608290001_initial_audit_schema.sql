-- Stellar SEO Audit Agent persistence.
-- Apply this migration in the Supabase SQL editor before deploying the API.

create table if not exists public.audits (
  id text primary key,
  requested_url text not null,
  normalized_origin text,
  business_description text,
  audit_reason text,
  important_urls_json text not null default '[]',
  crawl_limit integer not null check (crawl_limit between 1 and 100),
  status text not null check (status in ('queued', 'running', 'complete', 'failed')),
  stage text not null check (stage in ('queued', 'validating', 'crawling', 'auditing', 'scoring', 'reporting', 'complete', 'failed')),
  progress integer not null default 0 check (progress between 0 and 100),
  warnings_json text not null default '[]',
  error text,
  report_json text,
  created_at text not null,
  updated_at text not null
);

create index if not exists idx_audits_created_at
  on public.audits (created_at desc);

create table if not exists public.pages (
  id text primary key,
  audit_id text not null references public.audits(id) on delete cascade,
  requested_url text not null,
  final_url text not null,
  status_code integer,
  depth integer not null,
  content_type text,
  title text,
  meta_description text,
  canonical text,
  robots_directives_json text not null default '[]',
  h1_json text not null default '[]',
  h2_json text not null default '[]',
  word_count integer not null default 0,
  internal_links_json text not null default '[]',
  images_total integer not null default 0,
  images_missing_alt integer not null default 0,
  schema_types_json text not null default '[]',
  has_viewport integer not null default 0,
  content_hash text,
  fetch_error text
);

create index if not exists idx_pages_audit on public.pages(audit_id);

create table if not exists public.findings (
  id text primary key,
  audit_id text not null references public.audits(id) on delete cascade,
  rule_id text not null,
  title text not null,
  severity text not null check (severity in ('critical', 'important', 'minor')),
  confidence text not null check (confidence in ('high', 'medium', 'low')),
  evidence text not null,
  why_it_matters text not null,
  recommendation text not null,
  affected_urls_json text not null default '[]',
  score real not null default 0
);

create index if not exists idx_findings_audit on public.findings(audit_id);

-- The browser never connects to these tables directly in this MVP. Keep access
-- behind FastAPI; production authentication/workspace policies can be added later.
alter table public.audits enable row level security;
alter table public.pages enable row level security;
alter table public.findings enable row level security;
