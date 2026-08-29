# Vercel + Supabase deployment

## Vercel Services deployment (recommended)

Create one Vercel project from the repository root. Leave **Root Directory**
set to `.` and choose the **Other** application preset. Vercel will show and
deploy both detected services: `frontend` as Next.js and `backend` as FastAPI.
The backend service path is `/api/backend`.

Add the backend variables below to this single Vercel project for Preview and
Production. Do not add `NEXT_PUBLIC_API_URL`; the frontend automatically uses
the same-origin `/api/backend` path in production. Root-level Vercel
environment variables are available to the services.

After deployment, use the generated frontend URL for the app. FastAPI docs are
available at `<deployment-url>/api/backend/docs`.

## Separate deployment (alternative)

The repository is deployed as **two Vercel projects**. Both projects use the
same Git repository but have different Root Directories. This keeps the
frontend and Python API independently configurable without relying on Vercel
Services private beta.

## Frontend: Vercel

Create a Vercel project from the repository and set its Root Directory to `frontend`.

Configure this environment variable for Preview and Production:

```text
NEXT_PUBLIC_API_URL=https://your-stellar-api.vercel.app
```

Next.js has first-class Vercel support. No custom build command is required when `frontend` is selected as the project root.

## Backend: Vercel Python / FastAPI

Create a second Vercel project from the same repository and set its Root
Directory to `backend`. Vercel discovers `backend/app.py` as the FastAPI
entrypoint. `backend/vercel.json` gives bounded audits the Hobby-plan maximum
duration of 300 seconds.

Set these backend environment variables:

```text
DATABASE_URL=postgresql://...supabase-pooler...:6543/postgres
SEO_AUDIT_CORS_ORIGINS=https://your-stellar-frontend.vercel.app
SEO_AUDIT_LLM_PROVIDER=groq
SEO_AUDIT_LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=your-secret-key
```

Use the Supabase **transaction pooler** connection string for `DATABASE_URL`,
not the browser-facing project URL or anon key. The repository disables Psycopg
prepared statements because transaction pooling does not support them.

Before the first deploy, run
`supabase/migrations/202608290001_initial_audit_schema.sql` in Supabase's SQL
editor. FastAPI also performs idempotent table initialization as a safety net.

## How production audit execution works

The API first inserts a queued run into Supabase. The run page then calls the
bounded `/audits/{id}/process` endpoint once and polls the saved progress. This
replaces the continuously running worker, which Vercel cannot host. The local
worker command is retained for local development and testing.

The MVP crawl limit should remain at 20 on the Hobby plan. A future large-site
version should use Vercel Queues or Workflow so each crawl is durable beyond one
function invocation.

PDFs are generated on demand from report JSON stored in Supabase. No production
feature depends on Vercel's ephemeral filesystem.
