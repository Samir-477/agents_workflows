-- Prompt-first Meta Title and Description Generator persistence.

create table if not exists public.metadata_generations (
  id text primary key,
  prompt text not null,
  status text not null check (status in ('queued', 'running', 'complete', 'failed')),
  stage text not null check (
    stage in (
      'queued', 'parsing', 'generating', 'validating', 'deduplicating',
      'recommending', 'complete', 'failed'
    )
  ),
  progress integer not null default 0 check (progress between 0 and 100),
  parsed_brief_json text,
  result_json text,
  warnings_json text not null default '[]',
  error text,
  created_at text not null,
  updated_at text not null
);

create index if not exists idx_metadata_generations_created_at
  on public.metadata_generations (created_at desc);

-- The browser accesses runs through FastAPI. Workspace/user policies will be
-- added when demo authentication is replaced with production authentication.
alter table public.metadata_generations enable row level security;
