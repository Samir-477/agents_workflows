# Stellar Agents

Stellar is a multi-agent web application built with Next.js and FastAPI. It is
structured for one direct Vercel deployment while keeping the backend's domain
logic isolated from the frontend source.

## Structure

```text
stellar-agents/
  src/                       Next.js frontend
  api/index.py               small Vercel FastAPI entrypoint
  backend/
    src/agent_runtime/        shared app composition and agent registration
    src/meta_generator/       prompt parsing, generation, validation, and storage
    src/seo_audit/           crawler, rules, workflow, storage, and reports
    tests/                   backend tests
    app.py                   optional standalone local entrypoint
  supabase/                  production database migrations
  docs/                      architecture and deployment notes
  package.json               Next.js dependencies
  requirements.txt           Python dependency entrypoint for Vercel
  vercel.json                Python function duration and bundle settings
```

The root `api/index.py` is only Vercel's routing adapter. The actual backend
implementation remains under `backend/src/`.

## Run locally

Install dependencies from the repository root:

```powershell
cmd /c npm ci
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Start FastAPI:

```powershell
python -m uvicorn api.index:app --reload --port 8000
```

Start Next.js in another terminal:

```powershell
cmd /c npm run dev
```

Open `http://localhost:3000`. FastAPI docs are available at
`http://127.0.0.1:8000/api/docs`.

## Deploy

Import this repository into Vercel once and keep Root Directory set to `.`.
Vercel builds the root Next.js application and packages `api/index.py` as the
Python API. Both are served from one deployment domain.

Production audit requests use `/api/agents/seo-audit`. Metadata-generator
requests use `/api/agents/meta-title-description`. Both are served from the same
FastAPI/Vercel deployment, so do not set `NEXT_PUBLIC_API_URL` in Vercel.

Model-powered agents use `AGENT_LLM_PROVIDER` and `AGENT_LLM_MODEL`, with the
provider-specific `GROQ_API_KEY` or `OPENAI_API_KEY`. The older
`SEO_AUDIT_LLM_*` variable names remain supported for compatibility.

See [deployment notes](docs/DEPLOYMENT.md) and
[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).
