import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from local_seo.api import create_local_router
from local_seo.maps import MapsLookupError, lookup_candidates
from local_seo.models import CopyDraft, LocalRequest, Location, Profile
from local_seo.pipeline import finalize, ground_profile
from local_seo.storage import MemoryLocalRepository


def profile():
    return Profile(business_name="Sample Plumbing", phone="5550100", hours="24/7", services=["plumbing"], locations=[Location(area="Austin", kind="service_area"), Location(area="Dallas", kind="planned")])


def copy(area="Austin"):
    return CopyDraft(title=f"Plumbing in {area}", meta_description=f"Discuss your plumbing requirements in {area} with Sample Plumbing.", headline=f"Plumbing in {area}", introduction=f"Discuss your plumbing needs in {area} and let us help you plan the next steps for your property.", sections=[{"heading": "Service details", "body": "[CONFIRM: service scope for this area]"}] * 2, faqs=[{"question": f"Can you answer question {i}?", "answer": "[CONFIRM: business policy]"} for i in range(5)], call_to_action="Contact us to discuss your needs.")


def test_no_fake_branches_and_planned_actions():
    result = finalize(profile(), [copy(), copy("Dallas")], [])
    assert result.pages[0].json_ld["@type"] == "Service"
    assert "address" not in result.pages[0].json_ld
    assert result.pages[1].json_ld == {}
    assert result.pages[1].call_url is None
    assert result.pages[1].directions_url is None
    assert result.status == "needs_review"
    assert result.warnings  # City-swap comparison.
    assert result.pages[0].title_characters == len(copy().title)
    assert result.pages[0].review_tasks


def test_branch_overrides_and_schema():
    p = profile()
    p.locations[0] = Location(area="Austin", kind="physical", address="10 Main Street", phone="5550200", hours="Mon 9-5")
    page = finalize(p, [copy(), copy("Dallas")], []).pages[0]
    assert page.business_details["phone"] == "5550200"
    assert page.business_details["hours"] == "Mon 9-5"
    assert page.json_ld["address"] == "10 Main Street"
    assert page.directions_url.startswith("https://www.google.com/maps/")


def test_physical_accommodation_uses_lodging_business_schema():
    lodging = Profile(
        business_name="Lake View Resort",
        phone="5550300",
        services=["accommodation", "spa"],
        locations=[Location(area="Kodaikanal", kind="physical", address="44 Lake Road")],
    )
    page = finalize(lodging, [copy("Kodaikanal")], []).pages[0]
    assert page.json_ld["@type"] == "LodgingBusiness"


def test_grounding_and_batch_limits():
    with pytest.raises(ValueError):
        ground_profile(profile(), "plumbing in Austin and Dallas")
    p = profile()
    p.exceeds_page_limit = True
    with pytest.raises(ValueError, match="three"):
        ground_profile(p, "Sample Plumbing 5550100 24/7 plumbing Austin Dallas")
    with pytest.raises(ValidationError):
        LocalRequest(prompt="Plumbing in Austin, available by appointment", existing_urls=["javascript:alert(1)"])


class FakeGenerator:
    async def parse(self, request):
        return profile()

    async def draft(self, p, location):
        return copy(location.area)


def client(generator=None):
    repository = MemoryLocalRepository()
    app = FastAPI()
    app.include_router(create_local_router(repository, generator or FakeGenerator()))
    return TestClient(app), repository


def test_run_lifecycle():
    api, repo = client()
    base = "/api/agents/local-seo/generations"
    response = api.post(base, json={"prompt": "Sample Plumbing 5550100 24/7 plumbing Austin Dallas"})
    assert response.status_code == 202
    run_id = response.json()["id"]
    assert api.get(f"{base}/{run_id}/result").status_code == 409
    assert api.post(f"{base}/{run_id}/process").json()["status"] == "complete"
    assert api.get(f"{base}/{run_id}/result").json()["status"] == "needs_review"
    updated_copy = copy().model_copy(update={"title": "Austin plumbing — edited draft"})
    edited = api.put(f"{base}/{run_id}/pages/0", json=updated_copy.model_dump())
    assert edited.status_code == 200
    assert edited.json()["result"]["pages"][0]["title_characters"] == len(updated_copy.title)
    assert api.get(f"{base}/{run_id}").json()["result"]["pages"][0]["content"]["title"] == updated_copy.title
    assert api.put(f"{base}/{run_id}/pages/99", json=updated_copy.model_dump()).status_code == 404
    assert api.get(base, params={"query": "Sample"}).json()["total"] == 1
    assert api.post(f"{base}/{run_id}/retry").json()["status"] == "queued"
    assert repo.mutate(run_id, expected={"queued"}, status="running")
    assert repo.mutate(run_id, expected={"queued"}, status="running") is None
    assert api.delete(f"{base}/{run_id}").status_code == 409
    repo.mutate(run_id, status="failed")
    assert api.delete(f"{base}/{run_id}").status_code == 204
    assert api.get(f"{base}/{run_id}").status_code == 404


def test_edit_revalidation_retains_source_grounding_and_listing_warnings():
    class GroundedGenerator(FakeGenerator):
        async def parse(self, request):
            value = profile()
            value.differentiators = ["licensed"]
            return value

        async def draft(self, p, location):
            draft = copy(location.area)
            draft.introduction = (
                f"Sample Plumbing provides licensed plumbing support in {location.area} "
                "and helps property owners plan the next steps."
            )
            return draft

    api, repo = client(GroundedGenerator())
    base = "/api/agents/local-seo/generations"
    prompt = "Sample Plumbing 5550100 24/7 licensed plumbing Austin Dallas"
    run_id = api.post(base, json={"prompt": prompt}).json()["id"]
    run = api.post(f"{base}/{run_id}/process").json()
    repo.mutate(
        run_id,
        warnings=[*run["result"]["warnings"], "Listing lookup unavailable; draft retained."],
        result=repo.get(run_id).result.model_copy(update={
            "warnings": [*repo.get(run_id).result.warnings, "Listing lookup unavailable; draft retained."]
        }),
    )
    edited_copy = CopyDraft.model_validate(run["result"]["pages"][0]["content"])
    edited = api.put(f"{base}/{run_id}/pages/0", json=edited_copy.model_dump())
    result = edited.json()["result"]
    assert not any("Unsupported claim wording" in item for item in result["warnings"])
    assert "Listing lookup unavailable; draft retained." in result["warnings"]


def test_provider_errors_are_redacted():
    class Broken(FakeGenerator):
        async def parse(self, request):
            raise RuntimeError("secret-api-key")
    api, _ = client(Broken())
    base = "/api/agents/local-seo/generations"
    run_id = api.post(base, json={"prompt": "plumbing in Austin, our service area"}).json()["id"]
    response = api.post(f"{base}/{run_id}/process")
    assert response.json()["status"] == "failed"
    assert "secret-api-key" not in response.text


def _osm_transport(overpass_response):
    def handle(request):
        if "nominatim" in request.url.host:
            assert "stellar-local-seo" in request.headers["user-agent"]
            return httpx.Response(200, json=[{"boundingbox": ["-33.90", "-33.80", "151.10", "151.30"]}])
        assert "overpass" in request.url.host
        return overpass_response
    return httpx.MockTransport(handle)


async def test_maps_ids_only_and_ambiguous_candidates():
    elements = {"elements": [
        {"type": "node", "id": 11, "tags": {"name": "Sample Plumbing", "shop": "trade"}},
        {"type": "way", "id": 22, "center": {"lat": -33.86, "lon": 151.2}, "tags": {"name": "Sample Plumbing Supplies", "shop": "hardware"}},
        {"type": "node", "id": 33, "tags": {"name": "Unrelated Cafe", "amenity": "cafe"}},
        {"type": "node", "id": 44, "tags": {"name": "Sample Plumbing Depot"}},  # No POI tag -> dropped.
    ]}
    async with httpx.AsyncClient(transport=_osm_transport(httpx.Response(200, json=elements))) as session:
        candidates = await lookup_candidates("Sample Plumbing", "Sydney", client=session)
    assert [c["place_id"] for c in candidates] == ["node/11", "way/22"]
    assert all(c["maps_url"].startswith("https://www.openstreetmap.org/") for c in candidates)
    assert all("Unrelated" not in c["name"] for c in candidates)


async def test_maps_failure_redacts_upstream_message():
    async with httpx.AsyncClient(transport=_osm_transport(httpx.Response(429, text="rate limited: secret-token"))) as session:
        with pytest.raises(MapsLookupError) as error:
            await lookup_candidates("Sample Plumbing", "Sydney", client=session)
    assert "secret-token" not in str(error.value)
    assert "429" in str(error.value) and "OVERPASS_UNAVAILABLE" in str(error.value)


async def test_maps_skips_overly_broad_area():
    def handle(request):
        assert "nominatim" in request.url.host  # Overpass must not be reached.
        return httpx.Response(200, json=[{"boundingbox": ["10.0", "45.0", "-5.0", "40.0"]}])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as session:
        assert await lookup_candidates("Sample Plumbing", "Texas", client=session) == []


def test_local_runs_in_shared_history():
    from agent_runtime.history import AgentRunHistoryService
    from unittest.mock import Mock
    repo = MemoryLocalRepository()
    repo.create(LocalRequest(prompt="Sample Plumbing serving Austin from one base"))
    service = AgentRunHistoryService(*[Mock() for _ in range(7)], local_repository=repo)
    history = service.list_runs(limit=10, offset=0, query="Sample", agent="local-seo")
    assert history.total == 1
    assert history.items[0].agent_slug == "local-seo"


async def test_optional_maps_failure_does_not_fail_draft(monkeypatch):
    from local_seo.pipeline import generate_run
    class PhysicalGenerator(FakeGenerator):
        async def parse(self, request):
            return Profile(business_name="Sample Plumbing", services=["plumbing"], locations=[Location(area="Austin", kind="physical")])
    async def fail(*args, **kwargs):
        raise MapsLookupError(403, ["PERMISSION_DENIED"])
    monkeypatch.setattr("local_seo.pipeline.lookup_candidates", fail)
    result = await generate_run(LocalRequest(prompt="Sample Plumbing offers plumbing at our physical Austin office", lookup_maps=True), PhysicalGenerator(), lambda *args: None)
    assert len(result.pages) == 1
    assert any("403" in warning for warning in result.warnings)
