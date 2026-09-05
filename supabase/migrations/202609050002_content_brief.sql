create table if not exists public.content_brief_generations (
  id text primary key,
  request_json text not null,
  target_keyword text not null,
  audience text not null,
  status text not null,
  stage text not null,
  progress integer not null default 0 check (progress between 0 and 100),
  draft_json text,
  result_json text,
  warnings_json text not null default '[]',
  error text,
  created_at text not null,
  updated_at text not null
);

create index if not exists idx_content_briefs_created_at
  on public.content_brief_generations (created_at desc);

alter table public.content_brief_generations enable row level security;
