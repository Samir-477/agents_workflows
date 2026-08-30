# MVP Implementation Status

Last updated: 2026-08-30

## Current deployed flow

```text
One Vercel project and domain
  -> Next.js serves the Stellar frontend
  -> /api/* reaches api/index.py (FastAPI)
  -> FastAPI imports agent logic from backend/src/
  -> queued audit and progress persist in Supabase
  -> frontend polls same-origin API and publishes the report
```

The standalone worker remains available for local development and uses Supabase.

## Implemented product surface

- Demo login and protected agent workspace.
- Searchable agent catalogue with active and coming-soon agents.
- Compact audit form with closed optional context controls.
- Responsible bounded crawl, deterministic checks, and optional Groq summary.
- Persisted progress, prioritized findings, evidence, quick wins, and limitations.
- Paginated history, deletion, report pages, and PDF downloads.
- Supabase/Postgres storage in both local and deployed environments.
- One-project Next.js + FastAPI Vercel deployment boundary.

## Verification baseline

- 17 backend tests pass.
- FastAPI imports and health/docs endpoints pass locally.
- Frontend lint and production build pass.
- Deterministic reporting works without an LLM key.

## Known limitations

- Processing is bounded to one serverless invocation; larger crawls need a queue.
- Selective browser rendering is not implemented.
- Sitemap indexes are not recursively expanded.
- The score and rule catalogue remain MVP quality.
- Demo login is not production authentication.
