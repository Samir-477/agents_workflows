# Frontend

Next.js App Router frontend for signing in, browsing Stellar agents, submitting audits, following progress, and reading prioritized reports.

```powershell
Copy-Item .env.example .env.local
cmd /c npm install
cmd /c npm run dev
```

`NEXT_PUBLIC_API_URL` must point to the FastAPI backend.

## Routes

- `/login` — dummy login using `admin@gmail.com` and `admin123`
- `/agents` — searchable agent catalogue with active and coming-soon agents
- `/agents/seo-audit` — SEO Audit Agent explanation and audit form
- `/agents/seo-audit/runs/<audit-id>` — live progress and completed report
- `/agents/history` — paginated saved audits, report/PDF actions, and deletion

The demo session uses an HTTP-only cookie and `src/proxy.ts` protects the agent routes. It is intentionally not a replacement for production authentication.

For the Vercel Services deployment, leave `NEXT_PUBLIC_API_URL` unset; the
frontend calls the same deployment's `/api/backend` service path in production.
For the separate-project setup, set the project Root Directory to `frontend`
and configure `NEXT_PUBLIC_API_URL` for Preview and Production.
