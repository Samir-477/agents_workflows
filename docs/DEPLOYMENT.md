# One Vercel deployment + Supabase

## Deployment model

Deploy the repository as one Vercel project with Root Directory `.`.

```text
src/                         Next.js frontend
api/index.py                 Vercel Python/FastAPI entrypoint
backend/src/seo_audit/       backend implementation imported by the entrypoint
```

Vercel's documented Next.js + Python layout builds the frontend from the root
`package.json` and packages `api/index.py` as a Python function. Requests to
`/` reach Next.js, while `/api/*` reaches FastAPI on the same domain.

## Vercel project settings

```text
Root Directory: .
Framework Preset: Next.js
Build Command: npm run build (default)
Output Directory: .next (default)
Install Command: npm install / npm ci (default)
```

Do not select `frontend`, `backend`, or `api` as the Root Directory. There is
only one Vercel project.

## Environment variables

Add these to the one Vercel project:

```text
DATABASE_URL=postgresql://...supabase-transaction-pooler...:6543/postgres
SEO_AUDIT_LLM_PROVIDER=groq
SEO_AUDIT_LLM_MODEL=openai/gpt-oss-20b
GROQ_API_KEY=your-secret-key
SEO_AUDIT_DEFAULT_CRAWL_LIMIT=20
SEO_AUDIT_MAX_CRAWL_LIMIT=100
SEO_AUDIT_ALLOW_PRIVATE_NETWORKS=false
```

Do not add `NEXT_PUBLIC_API_URL` or `SEO_AUDIT_CORS_ORIGINS` in this deployment.
The browser uses the same origin, so neither a backend hostname nor CORS is
required.

Use Supabase's transaction-pooler connection string for `DATABASE_URL`, not the
browser-facing project URL. Encode reserved password characters; for example,
`#` becomes `%23`.

Run `supabase/migrations/202608290001_initial_audit_schema.sql` in Supabase's
SQL editor before the first production audit.

## Verify

After deployment, open:

```text
https://your-project.vercel.app/api/health
https://your-project.vercel.app/api/docs
```

The health endpoint should return `{"status":"ok"}`. Then open the same domain
and run a 20-page audit from the frontend.

## Adding agents later

Add frontend UI under `src/` and backend code under `backend/src/<agent_name>/`.
Expose each agent under a sibling `/api/agents/<agent-name>` namespace. The one
Vercel project continues to deploy all agents.
