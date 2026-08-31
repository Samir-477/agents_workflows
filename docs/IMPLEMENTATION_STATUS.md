# MVP Implementation Status

Last updated: 2026-08-31

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

## Meta Title and Description Generator pipeline

- Prompt-first input for one page or a batch of up to 10; no URL crawling in this agent.
- Metadata writing is chunked into groups of three pages for bounded model calls.
- Structured prompt parsing that preserves supplied, inferred, and missing context.
- Four titles and three descriptions per page through constrained model output.
- Deterministic counts, length labels, numeric-claim checks, scoring, option
  similarity, cross-page duplication checks, and recommended pair selection.
- Up to two validation-driven repair passes; preferred-range misses degrade to
  explicit warnings rather than failing an otherwise usable run.
- Persisted queued/running/complete/failed lifecycle in Supabase.
- Namespaced API routes under `/api/agents/meta-title-description`.
- Shared agent registration/composition layer for future backend agents.
- Screenshot-inspired generator landing page and prompt examples.
- Integrated progress, retry/error states, recommended SERP-style previews,
  full option review, validation warnings, and copy actions.
- Exports, refinement, and shared-history presentation are not yet implemented.

## Verification baseline

- 30 backend tests pass.
- FastAPI imports and health/docs endpoints pass locally.
- Frontend lint and production build pass.
- Deterministic reporting works without an LLM key.

## Known limitations

- Processing is bounded to one serverless invocation; larger crawls need a queue.
- Selective browser rendering is not implemented.
- Sitemap indexes are not recursively expanded.
- The score and rule catalogue remain MVP quality.
- Demo login is not production authentication.
- Metadata generation currently uses character-based practical ranges; measured
  SERP pixel-width previews are deferred to the UI phase.
- Unsupported numeric claims are checked deterministically. Other factual claims
  are constrained to the user brief through the model contract but cannot be
  comprehensively verified because this agent does not crawl URLs or use external data.
