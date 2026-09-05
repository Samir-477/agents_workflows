create table if not exists public.internal_link_audits (
  id text primary key,
  requested_url text not null,
  normalized_origin text,
  business_description text,
  audit_goal text,
  important_urls_json text not null default '[]',
  crawl_limit integer not null,
  status text not null,
  stage text not null,
  progress integer not null default 0,
  result_json text,
  warnings_json text not null default '[]',
  error text,
  created_at text not null,
  updated_at text not null
);

create index if not exists idx_internal_link_audits_created_at
  on public.internal_link_audits (created_at desc);

alter table public.internal_link_audits enable row level security;
