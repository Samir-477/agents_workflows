create table if not exists public.keyword_cluster_generations (
  id text primary key,
  raw_keywords text not null,
  status text not null,
  stage text not null,
  progress integer not null default 0 check (progress between 0 and 100),
  parsed_keywords_json text not null default '[]',
  result_json text,
  warnings_json text not null default '[]',
  error text,
  created_at text not null,
  updated_at text not null
);

create index if not exists idx_keyword_cluster_created_at
  on public.keyword_cluster_generations (created_at desc);

alter table public.keyword_cluster_generations enable row level security;

revoke all on table public.keyword_cluster_generations from anon, authenticated;
