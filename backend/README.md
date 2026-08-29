# Backend

FastAPI, LangGraph, the crawler, deterministic SEO/AEO rules, Groq-assisted
reporting, and persistence live here. SQLite is the local fallback; Vercel uses
Supabase Postgres through `DATABASE_URL`.

```powershell
python -m pip install -e ".[dev]"
seo-audit-api
```

The frontend calls `/audits/{id}/process`, allowing FastAPI to run each bounded
audit inside one request locally or one Vercel invocation in production.
`seo-audit-worker` remains available only for command-line queue testing.

Copy `.env.example` to `.env` for a new local setup. Keep real keys only in `.env`.
