import asyncio
import time
from io import BytesIO
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from diagnosis import engine
from diagnosis.api import create_router
from diagnosis.models import DiagnosisInput, AGENTS
from diagnosis.storage import MemoryDiagnosisRepository
from diagnosis.reporting import assemble_report
from diagnosis.evidence import derive_research_query, derive_resort_identity, snapshot, SnapshotCrawler
from diagnosis.pdf import build_pdf
from seo_audit.crawler import CrawlResult, SiteCrawler
from seo_audit.models import PageRecord
from seo_audit.config import Settings


URL = "https://example.com/resorts/lake"


def setup_run():
    repo = MemoryDiagnosisRepository()
    run = repo.create(DiagnosisInput(page_url=URL))
    return repo, run


def capture_data():
    page = PageRecord(audit_id="test", requested_url=URL, final_url=URL, status_code=200,
                      title="Example Resort - TEST FIXTURE", main_text="A resort page for test verification. " * 50,
                      json_ld_errors=["Block 2: invalid control character"], schema_types=["LodgingBusiness"])
    return snapshot(CrawlResult(pages=[page], origin="https://example.com", warnings=["One-page test sample"], robots_txt="User-agent: *\nAllow: /"))


def test_research_query_is_derived_from_page_evidence_then_url():
    data = capture_data()
    data["pages"][0]["h1"] = ["Sterling Lake Palace Alleppey"]
    assert derive_research_query(data, URL) == "Sterling Lake Palace Alleppey"
    data["pages"][0]["h1"] = []
    data["pages"][0]["title"] = None
    assert derive_research_query(data, URL) == "Lake"
    assert derive_research_query({"pages": []}, "https://example.com/resorts/regalia-agra") == "Regalia Agra"


def test_resort_identity_rejects_marketing_h1_and_uses_schema_or_branded_slug():
    data = {"pages": [{
        "final_url": "https://www.sterlingholidays.com/resorts-hotels/lake-palace-alleppey",
        "title": "Best Family Resorts/Hotels in Alleppey - Sterling Holidays",
        "h1": ["Cruise through heaven in Kerala's lush backwaters"],
        "schema_names": ["Sterling Lake Palace Alleppey"],
        "main_text": "Sterling Lake Palace Alleppey",
    }]}
    identity = derive_resort_identity(data, data["pages"][0]["final_url"])
    assert identity["property_name"] == "Sterling Lake Palace Alleppey"
    assert identity["branded_query"] == "Sterling Lake Palace Alleppey"
    assert identity["generic_query"] == "resorts in Alleppey"
    assert identity["rejected_candidates"][0]["value"].startswith("Cruise through")


def test_resort_identity_adds_url_destination_when_schema_name_omits_it():
    data = {"pages": [{
        "final_url": "https://www.sterlingholidays.com/resorts-hotels/lake-palace-alleppey",
        "title": "Best Family Resorts/Hotels in Alleppey - Sterling Holidays",
        "h1": ["Cruise through heaven in Kerala's lush backwaters"],
        "schema_names": ["Sterling Lake Palace"],
        "main_text": "Sterling Lake Palace in Alleppey",
    }]}
    identity = derive_resort_identity(data, data["pages"][0]["final_url"])
    assert identity["property_name"] == "Sterling Lake Palace"
    assert identity["destination"] == "Alleppey"
    assert identity["branded_query"] == "Sterling Lake Palace Alleppey"


def test_resort_identity_rejects_a_different_property_in_lodging_schema():
    url = "https://www.sterlingholidays.com/resorts-hotels/regalia-agra"
    data = {"pages": [{"final_url": url, "title": "Sterling Regalia Agra – Best Hotels & Resorts in Agra",
                       "h1": ["Sterling Regalia Agra – Stay Close to the Taj"],
                       "schema_names": ["Sterling Rampath Ayodhya"], "main_text": "Sterling Regalia Agra"}]}
    identity = derive_resort_identity(data, url)
    assert identity["branded_query"] == "Sterling Regalia Agra"
    assert identity["rejected_candidates"][0]["value"] == "Sterling Rampath Ayodhya"
    assert "schema name conflicts" in identity["rejected_candidates"][0]["reason"].casefold()


def test_report_turns_conflicting_lodging_identity_into_direct_management_proof():
    url = "https://www.sterlingholidays.com/resorts-hotels/regalia-agra"
    repo = MemoryDiagnosisRepository()
    run = repo.create(DiagnosisInput(page_url=url))
    page = PageRecord(audit_id="schema-name", requested_url=url, final_url=url, status_code=200,
                      title="Sterling Regalia Agra – Best Hotels & Resorts in Agra",
                      h1=["Sterling Regalia Agra – Stay Close to the Taj"],
                      schema_names=["Sterling Rampath Ayodhya"], main_text="Sterling Regalia Agra " * 50)
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    for key in AGENTS:
        run.tasks[key].status = "complete"
    report = assemble_report(run)
    match = [item for item in report["findings"] if item["title"] == "Structured resort identity names a different property"]
    assert len(match) == 1
    assert match[0]["primary_agent"] == "seo_audit"
    assert match[0]["supporting_agents"] == ["schema_markup"]
    proof = report["evidence"][match[0]["evidence_ids"][0]]
    assert "Sterling Regalia Agra" in proof["excerpt"]
    assert "Sterling Rampath Ayodhya" in proof["excerpt"]


def test_claims_are_exclusive_and_expired_lease_is_fenced():
    repo, run = setup_run()
    first = engine.claim(repo, run.id)
    assert first[0] == "capture"
    assert engine.claim(repo, run.id) is None
    repo.mutate(run.id, lambda r: setattr(r.tasks["capture"], "lease_until", time.time()-1))
    second = engine.claim(repo, run.id)
    assert second[1] != first[1]
    engine.checkpoint(repo, run.id, "capture", first[1], "stale-child")
    assert repo.get(run.id).tasks["capture"].run_id is None
    engine.checkpoint(repo, run.id, "capture", second[1], "new-child")
    assert repo.get(run.id).tasks["capture"].run_id == "new-child"


@pytest.mark.asyncio
async def test_all_agents_are_attempted_failure_isolated_and_report_saved(monkeypatch):
    repo, run = setup_run()
    calls = []
    async def execute(deps, repository, current, key, token):
        calls.append(key)
        if key == "capture": return capture_data()
        if key == "metadata": raise TimeoutError("provider secret must not reach user")
        if key == "report": return assemble_report(current)
        return {"status": "complete", "detail": {}}
    monkeypatch.setattr(engine, "execute", execute)
    for _ in range(12):
        await engine.process_one(None, repo, run.id)
    result = repo.get(run.id)
    assert set(AGENTS) <= set(calls)
    assert result.status == "partial"
    assert len(result.report["cases"]) == 10
    assert "secret" not in result.tasks["metadata"].error


@pytest.mark.asyncio
async def test_cancel_fences_inflight_completion(monkeypatch):
    repo, run = setup_run()
    async def execute(*args):
        engine.cancel(repo, run.id)
        return capture_data()
    monkeypatch.setattr(engine, "execute", execute)
    await engine.process_one(None, repo, run.id)
    result = repo.get(run.id)
    assert result.status == "cancelled"
    assert not result.tasks["capture"].result


def test_retry_preserves_success_and_invalidates_dependents():
    repo, run = setup_run()
    def complete(r):
        r.status = "partial"
        for t in r.tasks.values(): t.status = "complete"
        r.tasks["serp_competitor"].status = "failed"
        r.tasks["metadata"].run_id = "keep-me"
    repo.mutate(run.id, complete)
    result = engine.retry(repo, run.id)
    assert result.tasks["metadata"].run_id == "keep-me"
    assert result.tasks["capture"].status == "complete"
    assert result.tasks["content_brief"].status == "queued"
    assert result.tasks["content_optimizer"].status == "queued"
    assert result.tasks["report"].status == "queued"


def test_legacy_upgrade_resets_capture_and_every_agent():
    repo, run = setup_run()
    def completed(r):
        r.status = "complete"
        r.report = {"version": 3}
        for task in r.tasks.values():
            task.status = "complete"
            task.run_id = "legacy-child"
            task.result = {"legacy": True}
    repo.mutate(run.id, completed)
    result = engine.rerun_all(repo, run.id)
    assert result.status == "queued"
    assert result.report is None
    assert all(task.status == "queued" and task.run_id is None and not task.result for task in result.tasks.values())


@pytest.mark.asyncio
async def test_snapshot_reuses_primary_without_refetch(monkeypatch):
    data = capture_data()
    crawler = SnapshotCrawler(data, Settings())
    async def forbidden(*args): raise AssertionError("Unexpected live request")
    monkeypatch.setattr(crawler.live, "crawl", forbidden)
    one = await crawler.crawl("child-1", URL, 1)
    two = await crawler.crawl("child-2", URL, 20)
    assert one.pages[0].audit_id == "child-1"
    assert two.pages[0].audit_id == "child-2"
    assert data["pages"][0]["audit_id"] == "test"


def report_fixture():
    repo, run = setup_run()
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture_data()
    for key in AGENTS: run.tasks[key].status = "complete"
    run.tasks["seo_audit"].result = {"detail": {"findings": [
        {"rule_id": "invalid_json_ld", "title": "Malformed structured information", "evidence": "Block 2: invalid control character", "why_it_matters": "Search systems cannot read the affected information.", "recommendation": "Correct and validate the block.", "severity": "important", "affected_urls": [URL]},
        {"rule_id": "error_status", "title": "Unrelated property fault", "evidence": "404", "why_it_matters": "Wrong page", "recommendation": "Fix", "severity": "critical", "affected_urls": ["https://example.com/another-resort"]},
    ]}}
    run.tasks["metadata"].result = {"detail": {"pages": [{"titles": [{"recommended": True, "text": "Suggested title - REVIEW DRAFT"}], "descriptions": []}]}}
    return assemble_report(run)


def test_report_deduplicates_schema_and_excludes_unrelated_resort():
    report = report_fixture()
    assert report["version"] == 5
    schema_findings = [item for item in report["findings"] if item["title"] == "Malformed structured information"]
    assert len(schema_findings) == 1
    assert schema_findings[0]["supporting_agents"] == ["schema_markup"]
    assert "Unrelated property fault" not in str(report)
    assert len(report["cases"]) == 10
    assert "Suggested title" not in str(report["findings"])
    for f in report["findings"]:
        assert all(e in report["evidence"] for e in f["evidence_ids"])
    proof = next(iter(report["evidence"].values()))
    assert proof["title"]
    assert proof["observed_value"]
    assert proof["location"]
    assert proof["verification"]
    assert proof["fix_example"]
    assert proof["fix_label"]
    assert proof["presentation_kind"] == "json_parse_error"
    assert report["cases"][0]["management"]["evidence_explanations"][0]["plain_language"] != proof["observed_value"]


def test_supporting_agents_get_specific_assessment_outcomes():
    report = report_fixture()
    cases = {case["agent"]: case for case in report["cases"]}
    for key in ("internal_linking", "keyword_cluster", "content_brief", "local_seo"):
        management = cases[key]["management"]
        assert management["section_kind"] == "assessment"
        assert "No verified website fault was established" not in management["issue_identified"]
        assert management["recommended_actions"]
        assert all("Retain this result as a baseline" not in item for item in management["recommended_actions"])
        assert management["issue_identified"] not in management["other_findings"]


def test_report_rejects_agent_results_built_from_a_stale_slogan_identity():
    page_url = "https://www.sterlingholidays.com/resorts-hotels/lake-palace-alleppey"
    repo = MemoryDiagnosisRepository()
    run = repo.create(DiagnosisInput(page_url=page_url))
    page = PageRecord(audit_id="identity", requested_url=page_url, final_url=page_url, status_code=200,
                      title="Best Family Resorts/Hotels in Alleppey - Sterling Holidays",
                      h1=["Cruise through heaven in Kerala's lush backwaters"],
                      schema_names=["Sterling Lake Palace Alleppey"], main_text="Property page " * 100)
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    for key in AGENTS:
        run.tasks[key].status = "complete"
    run.tasks["serp_competitor"].result = {"detail": {"target_keyword": "Cruise through heaven in Kerala's lush backwaters", "organic_results": [{"position": 1, "title": "Unrelated", "url": "https://example.org"}]}}
    report = assemble_report(run)
    serp_case = next(case for case in report["cases"] if case["agent"] == "serp_competitor")
    assert report["identity"]["property_name"] == "Sterling Lake Palace Alleppey"
    assert serp_case["output_quality"] == "rejected"
    assert not serp_case["finding_ids"]
    assert "Cruise through heaven" not in str(report["findings"])


def test_low_quality_content_brief_is_excluded_from_management_outputs():
    repo, run = setup_run()
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture_data()
    for key in AGENTS:
        run.tasks[key].status = "complete"
    run.tasks["content_brief"].result = {"detail": {"target_keyword": "Lake", "quality_score": 40,
        "ready_for_handoff": False, "brief": {"suggested_title": "Bad fallback", "outline": [{"heading": "How to apply Lake"}]}}}
    report = assemble_report(run)
    case = next(case for case in report["cases"] if case["agent"] == "content_brief")
    assert case["output_quality"] == "rejected"
    assert case["proposed_outputs"] == []
    assert "Bad fallback" not in str(case["management"])


def test_report_excludes_internal_link_suggestions_without_contextual_target_match():
    page_url = "https://www.sterlingholidays.com/resorts-hotels/lake-palace-alleppey"
    repo = MemoryDiagnosisRepository()
    run = repo.create(DiagnosisInput(page_url=page_url))
    page = PageRecord(audit_id="links", requested_url=page_url, final_url=page_url, status_code=200,
                      title="Sterling Lake Palace", schema_names=["Sterling Lake Palace"],
                      main_text="Sterling Lake Palace in Alleppey " * 50)
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    for key in AGENTS:
        run.tasks[key].status = "complete"
    base = {"source_url": page_url, "placement_heading": "Backwater stay",
            "placement_snippet": "Explore Lake Vembanad and Alleppey's backwaters.",
            "anchor_options": ["Explore this destination"]}
    run.tasks["internal_linking"].result = {"detail": {"pages": [{}], "recommendations": [
        {**base, "target_url": "https://www.sterlingholidays.com/resorts-hotels/kodaikanal-lake"},
        {**base, "target_url": "https://www.sterlingholidays.com/destination/alleppey"},
    ]}}
    report = assemble_report(run)
    findings = [item for item in report["findings"] if item["primary_agent"] == "internal_linking"]
    assert len(findings) == 1
    assert "/destination/alleppey" in findings[0]["observation"]
    assert "kodaikanal" not in findings[0]["observation"]


def test_report_keeps_weak_optimizer_topics_as_observations():
    repo, run = setup_run()
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture_data()
    for key in AGENTS:
        run.tasks[key].status = "complete"
    run.tasks["content_optimizer"].result = {"detail": {"assessments": [{"key": "topic_coverage", "label": "Topic coverage", "summary": "One exact phrase was absent."}], "actions": [{
        "issue": "Review potential topic: lake hotel", "category": "Coverage",
        "observed_text": "Not found as an exact phrase", "impact_rationale": "Possible idea",
        "proposed_action": "Review it", "priority": "medium", "confidence": "medium",
        "affected_section": "Body", "evidence_ids": ["serp:topic:1"],
    }], "evidence": [{"id": "serp:topic:1", "label": "SERP pattern", "observed": "Two titles", "source_type": "serp"}]}}
    report = assemble_report(run)
    assert "Review potential topic" not in str(report["findings"])
    optimizer = next(case for case in report["cases"] if case["agent"] == "content_optimizer")
    assert any("Idea to investigate" in item for item in optimizer["observations"])


def test_pdf_contains_all_ten_sections_and_evidence():
    from pypdf import PdfReader
    report = report_fixture()
    pdf = build_pdf(report)
    reader = PdfReader(BytesIO(pdf))
    text = "\n".join(p.extract_text() for p in reader.pages)
    assert 4 <= len(reader.pages) <= 10
    assert "Ten-agent coverage" in text
    assert "Content Optimizer" in text
    assert "invalid control character" in text
    assert "REVIEW DRAFT" not in text
    assert "�" not in text
    assert "Unrelated property fault" not in text
    assert text.count("ACTION CASE") == len(report["findings"])
    assert "How we confirm completion" in text


def test_pdf_preserves_unicode_property_copy():
    from pypdf import PdfReader
    report = report_fixture()
    report["title"] = "Sterling Lake Palace – Kerala’s backwaters"
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(build_pdf(report))).pages)
    assert "Kerala’s backwaters" in text
    assert "�" not in text


def test_pdf_labels_optional_model_narrative_for_review():
    from pypdf import PdfReader
    report = report_fixture()
    report["narrative"] = {"source": "model", "status": "editorial_review_required", "text": "Review the supported resort-page concerns in priority order.", "evidence_ids": [next(iter(report["evidence"]))]}
    text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(build_pdf(report))).pages)
    assert "Model-written introduction - editorial review required" in text
    assert "Referenced evidence:" in text


def test_api_history_and_download_use_same_saved_report():
    repo, run = setup_run()
    report = report_fixture()
    repo.mutate(run.id, lambda r: setattr(r, "report", report))
    app = FastAPI()
    app.include_router(create_router(repo, None))
    with TestClient(app) as client:
        assert client.get("/api/diagnoses").status_code == 401
        client.cookies.set("stellar_demo_session", "stellar-admin")
        assert client.get("/api/diagnoses").json()[0]["id"] == run.id
        response = client.get(f"/api/diagnoses/{run.id}")
        assert response.json()["report"] == report
        assert "token" not in response.json()["tasks"]["capture"]
        assert client.get(f"/api/diagnoses/{run.id}/report.pdf").headers["content-type"] == "application/pdf"
        assert client.get("/api/diagnoses/missing").status_code == 404


def test_api_refreshes_an_existing_report_from_saved_agent_results():
    repo, run = setup_run()
    def completed(current):
        current.tasks["capture"].status = "complete"
        current.tasks["capture"].result = capture_data()
        for key in AGENTS:
            current.tasks[key].status = "complete"
        current.report = {"version": 1}
    repo.mutate(run.id, completed)
    app = FastAPI()
    app.include_router(create_router(repo, None))
    with TestClient(app) as client:
        client.cookies.set("stellar_demo_session", "stellar-admin")
        response = client.post(f"/api/diagnoses/{run.id}/refresh-report")
        assert response.status_code == 200
        assert response.json()["report"]["version"] == 5


def test_api_starts_combined_diagnosis_from_url_only():
    repo = MemoryDiagnosisRepository()
    app = FastAPI()
    app.include_router(create_router(repo, None))
    with TestClient(app) as client:
        client.cookies.set("stellar_demo_session", "stellar-admin")
        response = client.post("/api/diagnoses", json={"page_url": URL})
        assert response.status_code == 202
        assert "target_keyword" not in response.json()["request"]
        assert "owner_subject" not in response.json()
        assert repo.get(response.json()["id"]).owner_subject == "local-demo-admin"
        assert set(AGENTS) <= set(response.json()["tasks"])


def test_api_hides_a_diagnosis_owned_by_another_subject(monkeypatch):
    repo, run = setup_run()
    repo.mutate(run.id, lambda current: setattr(current, "owner_subject", "owner-a"))
    from diagnosis import api as diagnosis_api
    monkeypatch.setattr(diagnosis_api, "session_subject", lambda value: "owner-b" if value else None)
    app = FastAPI()
    app.include_router(create_router(repo, None))
    with TestClient(app) as client:
        client.cookies.set("stellar_demo_session", "signed-for-test")
        assert client.get(f"/api/diagnoses/{run.id}").status_code == 404
        assert client.get("/api/diagnoses").json() == []
        assert client.get(f"/api/diagnoses/{run.id}/report.pdf").status_code == 404


@pytest.mark.asyncio
async def test_model_failure_preserves_validated_report(monkeypatch):
    from diagnosis.reporting import narrate
    from diagnosis import provider
    class Fake:
        async def ainvoke(self, messages):
            return SimpleNamespace(content='{"overview":"Guaranteed 100 lost bookings", "evidence_ids":["invented"]}')
    monkeypatch.setattr(provider, "management_editor_model", lambda s, **kwargs: (Fake(), "fake:model"))
    report = report_fixture()
    result = await narrate(report, Settings())
    assert result["narrative"]["source"] == "validated finding template"
    assert result["findings"]


@pytest.mark.asyncio
async def test_management_editor_can_only_rewrite_referenced_cases(monkeypatch):
    from diagnosis.reporting import narrate, _editor_pack
    from diagnosis import provider
    report = report_fixture()
    pack = _editor_pack(report)
    cases = []
    for source in pack["cases"]:
        finding_ids = [item["id"] for item in source["findings"]]
        cases.append({
            "agent": source["agent"],
            "issue_identified": source["findings"][0]["observation"] if finding_ids else "No verified website fault was established by this agent.",
            "finding_ids": finding_ids,
            "evidence_explanations": [{"evidence_id": item["id"], "plain_language": item["observed_value"] or "Observed proof", "example": ""} for item in source["evidence"]],
            "why_management_should_care": source["findings"][0]["business_relevance"] if finding_ids else "The available checks did not produce a defensible management finding.",
            "other_findings": [],
            "recommended_actions": [source["allowed_actions"][0]],
            "limitation": source["limitations"][0] if source["limitations"] else "The result is limited to the captured evidence.",
        })
    calls = []
    class Fake:
        async def ainvoke(self, messages):
            calls.append(messages)
            json = __import__("json")
            requested = {item["agent"] for item in json.loads(messages[1][1])["cases"]}
            return SimpleNamespace(content=json.dumps({"overview": "Review the supported concerns and verify each recommendation before making changes.", "cases": [item for item in cases if item["agent"] in requested]}))
    monkeypatch.setattr(provider, "management_editor_model", lambda s, **kwargs: (Fake(), "fake:model"))
    result = await narrate(report, Settings())
    if result["management_editor"]["status"] != "complete":
        raise AssertionError(repr(result["management_editor"]))
    assert result["cases"][0]["management"]["source"] == "model_validated"
    assert len(calls) == 1


def test_optimizer_does_not_pass_malformed_schema():
    from content_optimizer.analysis import ContentInput, analyze_content
    from content_optimizer.models import ContentOptimizerRequest, ContentOptimizerRun
    run = ContentOptimizerRun(request=ContentOptimizerRequest(content_url=URL, target_keyword="lake resort", audience="Travellers"))
    result = analyze_content(run, ContentInput(mode="url", text="lake resort "*100, schema_types=["LodgingBusiness"], json_ld_errors=["invalid control character"]))
    assert next(a for a in result.assessments if a.key == "schema").status == "review"


@pytest.mark.asyncio
async def test_real_agent_workflows_share_evidence_and_persist_child_results(monkeypatch):
    """Real workflow/storage/validation contracts; only network/model boundaries are fake."""
    from agent_runtime.api import create_app
    from memory_repository import MemoryAuditRepository
    from memory_metadata_repository import MemoryMetadataGenerationRepository
    from test_metadata_generator import FakeGenerator as MetadataFake
    from test_schema_generator import FakeInterpreter
    from test_content_brief import FakeGenerator as BriefFake
    from test_keyword_cluster import FakeClusterGenerator
    from test_local_seo import FakeGenerator as LocalFake
    from test_internal_linking import FakeRefiner
    from test_serp_competitor import FakeSerper, FakeCrawler
    from seo_audit.url_safety import ValidatedTarget
    import seo_audit.workflow
    import ai_visibility.workflow
    import internal_linking.workflow
    import serp_competitor.workflow

    async def valid(url, **kwargs):
        return ValidatedTarget(url=url, origin="https://example.com")
    monkeypatch.setattr(seo_audit.workflow, "validate_public_target", valid)
    # Default function arguments capture their original callable; use local address allowance
    # for the SEO graph, and patch build boundary to explicitly inject our test validator.
    original_graph = engine.legacy.build_audit_graph
    monkeypatch.setattr(engine.legacy, "build_audit_graph", lambda *a, **kw: original_graph(*a, **kw, target_validator=valid))
    monkeypatch.setattr(ai_visibility.workflow, "validate_public_target", valid)
    monkeypatch.setattr(internal_linking.workflow, "validate_public_target", valid)
    monkeypatch.setattr(serp_competitor.workflow, "SerperClient", lambda key: FakeSerper())
    async def competitor(self, audit_id, start_url, limit):
        return await FakeCrawler().crawl(audit_id, start_url, limit)
    monkeypatch.setattr(SiteCrawler, "crawl", competitor)
    def adapter(fake):
        class Adapter:
            api_key_resolver = None
            model_resolver = None
            def __init__(self, *args): self.inner = fake()
            def __getattr__(self, name): return getattr(self.inner, name)
        return Adapter()
    app = create_app(Settings(), audit_repository=MemoryAuditRepository(), metadata_repository=MemoryMetadataGenerationRepository(),
                     metadata_generator=adapter(MetadataFake), schema_interpreter=adapter(FakeInterpreter),
                     content_brief_generator=adapter(BriefFake), keyword_cluster_generator=adapter(FakeClusterGenerator),
                     local_generator=adapter(LocalFake), internal_link_refiner=adapter(FakeRefiner))
    repo = app.state.diagnosis_repository
    run = repo.create(DiagnosisInput(page_url=URL))
    data = capture_data()
    data["pages"][0]["main_text"] += " Sample Plumbing 5550100 24/7 plumbing Austin Dallas"
    def captured(r):
        r.tasks["capture"].status = "complete"
        r.tasks["capture"].result = data
    repo.mutate(run.id, captured)
    for _ in range(11):
        await engine.process_one(app.state.diagnosis_dependencies, repo, run.id)
    result = repo.get(run.id)
    assert all(t.status in engine.TERMINAL for t in result.tasks.values())
    assert result.report is not None
    assert len(result.report["cases"]) == 10
    assert all(result.tasks[key].status == "complete" for key in AGENTS)
    assert result.tasks["local_seo"].result["detail"]["mode"] == "url_assessment"
    for key in set(AGENTS) - {"local_seo", "metadata", "keyword_cluster"}:
        assert result.tasks[key].status == "complete", (key, result.tasks[key].error)
        assert result.tasks[key].run_id
        assert result.tasks[key].result["detail"]
