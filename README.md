# SEO/AEO Audit Agent

An evidence-backed website audit application with a Next.js frontend and a FastAPI/LangGraph backend.

## Project structure

```text
seo_agent_idea/
  frontend/          Next.js web interface
  backend/           FastAPI application and local worker
  supabase/          PostgreSQL migrations for durable audit history
  docs/              Architecture, implementation, and deployment notes
  PROJECT_CONTEXT.md Durable product and architecture brief
```

## Run locally

Install and start the backend API:

```powershell
cd backend
python -m pip install -e ".[dev]"
seo-audit-api
```

In a second terminal, start the frontend:

```powershell
cd frontend
Copy-Item .env.example .env.local
cmd /c npm run dev
```

Open `http://localhost:3000`. FastAPI documentation is available at `http://127.0.0.1:8000/docs`.

The frontend starts each bounded audit through the API. `seo-audit-worker`
remains available for command-line/local queue testing, but it is not required
for the web app and is not part of the Vercel deployment.

Demo login:

```text
Email: admin@gmail.com
Password: admin123
```

The login is deliberately a demo gate, not production authentication.

## Configuration

- For the Vercel Services deployment, add backend secrets to the repository-root
  Vercel project. Vercel exposes the backend service at `/api/backend`.
- For local development, backend settings belong in `backend/.env` and frontend
  configuration belongs in `frontend/.env.local`.
- Set `NEXT_PUBLIC_API_URL` only when the frontend and backend are deployed as
  separate Vercel projects; leave it empty for the root Services deployment.
- Production frontend origins must be added to `SEO_AUDIT_CORS_ORIGINS` on the backend.

Local development uses SQLite and optional Markdown files. Production uses
Supabase Postgres; PDFs are generated on demand from the persisted report JSON.

See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md), [deployment notes](docs/DEPLOYMENT.md), and [implementation status](docs/IMPLEMENTATION_STATUS.md).
