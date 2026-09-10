create table if not exists public.website_diagnoses (
  id text primary key,
  document jsonb not null,
  created_at text not null
);
alter table public.website_diagnoses enable row level security;
create index if not exists website_diagnoses_created on public.website_diagnoses(created_at desc);
