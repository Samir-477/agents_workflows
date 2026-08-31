# Stellar backend implementation

This folder contains the Python backend domain code and tests. It is not a
second Vercel project.

- `src/seo_audit/` contains the SEO/AEO Audit Agent.
- `src/meta_generator/` contains the prompt-first metadata generator.
- `src/agent_runtime/` composes agent routers and shared persistence helpers.
- `tests/` contains backend verification.
- `app.py` allows the backend to run independently during local debugging.
- Root `../api/index.py` imports this package for the combined Vercel deployment.

Future backend agents should receive their own package under `src/`, expose a
distinct route namespace, and add an `AgentRegistration` in the shared FastAPI
composition root.

Run backend tests from this folder:

```powershell
python -m pytest
```
