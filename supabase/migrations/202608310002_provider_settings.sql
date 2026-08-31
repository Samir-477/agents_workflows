-- Provider API keys are encrypted at rest by Supabase Vault. The application
-- table stores only the Vault UUID and a four-character display suffix.

create extension if not exists supabase_vault with schema vault;

create table if not exists public.agent_provider_settings (
  provider text primary key check (provider in ('groq', 'openai')),
  vault_secret_id uuid,
  key_suffix text,
  model_id text,
  updated_at text not null
);

alter table public.agent_provider_settings enable row level security;

-- The browser never reads this table or Vault directly. Settings are accessed
-- only through the authenticated FastAPI settings endpoints.
