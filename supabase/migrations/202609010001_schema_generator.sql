-- Prompt-first Schema Markup Generator persistence.
create table if not exists public.schema_generations (
  id text primary key,
  prompt text not null,
  status text not null check (status in ('queued', 'running', 'complete', 'failed')),
  stage text not null check (stage in ('queued', 'interpreting', 'compiling', 'validating', 'recommending', 'complete', 'failed')),
  progress integer not null default 0 check (progress between 0 and 100),
  parsed_brief_json text,
  result_json text,
  warnings_json text not null default '[]',
  error text,
  created_at text not null,
  updated_at text not null
);
create index if not exists idx_schema_generations_created_at on public.schema_generations (created_at desc);
alter table public.schema_generations enable row level security;
