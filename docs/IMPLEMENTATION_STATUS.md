# MVP Implementation Status

Last updated: 2026-08-29

## Current deployed flow

```text
Next.js (Vercel project 1)
  -> POST /audits
  -> queued audit saved in Supabase Postgres
  -> run page POSTs /audits/{id}/process
  -> FastAPI function (Vercel project 2) atomically claims the audit
  -> LangGraph validates, crawls, checks, scores, and writes the report
  -> every stage persists to Supabase
  -> run page polls status and publishes the report
```

SQLite and `seo-audit-worker` remain available for local development. Neither
is required by the deployed web application.

## Implemented product surface

- Dummy login and protected agent workspace.
- Searchable agent catalogue with one active agent and coming-soon entries.
- Compact SEO Audit Agent URL form with closed optional context controls.
- Bounded, same-origin, read-only crawling with URL/network safety checks.
- Deterministic page extraction, SEO rules, explainable scoring, and optional Groq narrative.
- Persisted progress stages and friendly failure states.
- Prioritized report, quick wins, evidence, affected URLs, and limitations.
- Searchable/paginated history with delete actions.
- On-demand PDF downloads generated from stored report JSON.
- PostgreSQL repository mode for Supabase's transaction pooler.
- Two-project Vercel monorepo structure and Supabase migration.

## Verification

- 17 backend tests pass, including the serverless claim/process endpoint.
- Python compilation passes.
- PostgreSQL placeholder translation checks pass.
- Frontend ESLint, TypeScript, static generation, and production build pass.
- The deterministic report path works without an LLM key.
- Robots-blocked audits complete as limited reports without a misleading score.

## Known limitations

- The deployed process is bounded to one Vercel invocation; a durable queue is
  still recommended before increasing beyond the 20-page MVP crawl.
- HTTP HTML inspection only; selective browser rendering is not implemented.
- Sitemap indexes are not recursively expanded.
- The rule catalogue and site score remain an MVP, not an industry standard.
- Dummy login does not provide production user/workspace isolation.
- Production Supabase connectivity cannot be exercised until a project
  `DATABASE_URL` is supplied.

## Next recommended slice

Create the Supabase project, apply the migration, add both Vercel projects and
their environment variables, then run a deployed audit before expanding the
rule catalogue or authentication model.
