# Stellar backend implementation

This folder contains the Python backend domain code and tests. It is not a
second Vercel project.

- `src/seo_audit/` contains the active agent.
- `tests/` contains backend verification.
- `app.py` allows the backend to run independently during local debugging.
- Root `../api/index.py` imports this package for the combined Vercel deployment.

Future backend agents should receive their own package under `src/` and expose
a distinct route namespace through the shared FastAPI application.

Run backend tests from this folder:

```powershell
python -m pytest
```
