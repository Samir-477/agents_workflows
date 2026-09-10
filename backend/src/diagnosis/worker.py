"""Optional durable worker: python -m diagnosis.worker (same environment as API)."""
import asyncio
import argparse
from agent_runtime.api import create_app
from diagnosis.engine import process_one


async def work(once=False):
    app = create_app()
    async with app.router.lifespan_context(app):
        repo = app.state.diagnosis_repository
        deps = app.state.diagnosis_dependencies
        while True:
            ids = repo.pending()
            # Bound worker-wide concurrency; model stages within a diagnosis serialize.
            for id in ids:
                await process_one(deps, repo, id)
                if once:
                    return
            if once:
                return
            await asyncio.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    asyncio.run(work(parser.parse_args().once))
