from __future__ import annotations

import argparse
import asyncio
import logging

from seo_audit.config import Settings
from seo_audit.models import AuditStage, AuditStatus
from seo_audit.storage import AuditRepository
from seo_audit.workflow import build_audit_graph


LOGGER = logging.getLogger("seo_audit.worker")


async def process_one(repository: AuditRepository, graph) -> bool:
    audit = repository.claim_next_audit()
    if audit is None:
        return False
    LOGGER.info("Processing audit %s for %s", audit.id, audit.requested_url)
    try:
        await graph.ainvoke({"audit_id": audit.id})
    except Exception as exc:
        LOGGER.exception("Unhandled audit failure for %s", audit.id)
        repository.update_audit(
            audit.id,
            status=AuditStatus.FAILED,
            stage=AuditStage.FAILED,
            progress=100,
            error=f"Unhandled workflow error: {exc}",
        )
    return True


async def run_worker(*, once: bool = False) -> None:
    settings = Settings.from_env()
    repository = AuditRepository(settings.database_url)
    repository.initialize()
    graph = build_audit_graph(settings, repository)
    while True:
        processed = await process_one(repository, graph)
        if once:
            return
        if not processed:
            await asyncio.sleep(settings.worker_poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SEO/AEO audit worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one queued audit and exit",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run_worker(once=args.once))


if __name__ == "__main__":
    main()
