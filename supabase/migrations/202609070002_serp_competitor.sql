create table if not exists public.serp_competitor_runs (
  id text primary key,
  request_json text not null,
  status text not null check (status in ('queued', 'running', 'complete', 'failed')),
  stage text not null,
  progress integer not null default 0 check (progress between 0 and 100),
  result_json text,
  error text,
  created_at text not null,
  updated_at text not null
);
create index if not exists idx_serp_competitor_created_at on public.serp_competitor_runs (created_at desc);
alter table public.serp_competitor_runs enable row level security;
