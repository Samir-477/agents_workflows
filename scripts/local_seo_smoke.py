"""Explicit live smoke test. Creates one clearly labelled sample run in Supabase.

Run from the repository root: python scripts/local_seo_smoke.py
Pass --maps to additionally make one keyless OpenStreetMap lookup (Nominatim + Overpass).
Never prints keys, database URLs, or provider exception bodies.
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from agent_runtime.provider_settings import ProviderCredentialRepository
from local_seo.generation import LocalGenerator
from local_seo.maps import MapsLookupError, lookup_candidates
from local_seo.models import LocalRequest
from local_seo.pipeline import generate_run
from local_seo.storage import LocalRepository
from seo_audit.config import Settings


async def test_maps():
    try:
        matches = await lookup_candidates("Woolworths", "Sydney")
        print("osm_ids_only_lookup: ok; candidate_count:", len(matches), flush=True)
        return 0
    except MapsLookupError as exc:
        print("maps_http_status:", exc.status_code, "reason_codes:", exc.reasons, flush=True)
        return 2
    except Exception as exc:
        print("maps_lookup_failure_type:", type(exc).__name__, flush=True)
        return 2


async def main(maps, maps_only=False):
    settings = Settings.from_env()
    if maps_only:
        return await test_maps()
    credentials = ProviderCredentialRepository(settings.database_url)
    repository = LocalRepository(settings.database_url)
    repository.initialize()
    generator = LocalGenerator(settings, credentials.resolve_api_key, credentials.resolve_model)
    request = LocalRequest(prompt="SMOKE TEST — fictional business, not for publishing. Business name: Sample Plumbing. Services: plumbing. Service area: Austin. Kind: service_area, no public office. Phone: 5550100. Hours: 24/7. Local proof: supplied example of a completed kitchen pipe repair in Austin. Do not invent reviews, fees or response times.")
    run = repository.create(request)
    print("sample_run_id:", run.id, flush=True)
    repository.mutate(run.id, status="running")
    try:
        def progress(stage, percent):
            print("stage:", stage, flush=True)
            repository.mutate(run.id, stage=stage, progress=percent)
        result = await generate_run(request, generator, progress)
        repository.mutate(run.id, status="complete", stage="complete", progress=100, result=result)
        saved = repository.get(run.id)
        print("persisted_status:", saved.status, "pages:", len(saved.result.pages), "faqs:", len(saved.result.pages[0].content.faqs), flush=True)
        print("sample_title:", saved.result.pages[0].content.title, flush=True)
    except Exception as exc:
        repository.mutate(run.id, status="failed", stage="failed", error="Live smoke test failed; inspect provider configuration or extracted facts.")
        print("generation_failure_type:", type(exc).__name__, flush=True)
        return 1
    if maps:
        return await test_maps()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--maps", action="store_true")
    parser.add_argument("--maps-only", action="store_true")
    args = parser.parse_args()
    try:
        sys.exit(asyncio.run(main(args.maps, args.maps_only)))
    except Exception as exc:
        print("setup_failure_type:", type(exc).__name__)
        sys.exit(1)
