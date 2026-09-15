import asyncio
import pytest
from types import SimpleNamespace

from answer_optimization.analysis import _validate_draft, optimize_answers
from diagnosis.evidence import snapshot
from diagnosis.models import DiagnosisInput
from diagnosis.reporting import assemble_report
from diagnosis.storage import MemoryDiagnosisRepository
from question_discovery.analysis import discover_questions
from answer_gap.analysis import analyze_answer_gaps
from seo_audit.crawler import CrawlResult
from seo_audit.models import PageRecord
from serp_competitor.models import QuestionEvidence


URL = "https://www.sterlingholidays.com/resorts-hotels/lake-palace-alleppey"


def gap_result(gaps):
    return {"detail": {"prioritized_gaps": gaps, "discovery_provenance": {"observed_question_ids": [g["question_id"] for g in gaps]}}}


PARKING_PASSAGE = (
    "The resort offers ample gated parking for every guest arriving by car, motorbike or taxi, "
    "and the parking area stays open around the clock for guest convenience."
)
GROUNDED_DRAFT = (
    "This resort offers ample gated parking for every guest arriving by car, motorbike or taxi. "
    "The gated parking area stays open around the clock for every guest, and this parking offers "
    "convenience for every guest arriving at the resort."
)
HALLUCINATED_DRAFT = (
    "This resort has a rooftop infinity pool and complimentary valet parking with ample gated "
    "space for every guest arriving by car, motorbike or taxi around the clock."
)


def partial_gap(question_id="Q-01", excerpt=PARKING_PASSAGE):
    return {
        "question_id": question_id, "question": "Does the resort have parking for guests?",
        "topic": "transport", "intent": "planning", "priority": "medium", "priority_score": 61,
        "status": "partial", "reason": "A related passage was captured, but it does not provide a sufficiently direct and complete answer.",
        "answer_quality_score": 50, "passage": {"excerpt": excerpt, "source_url": URL, "location": "Selected resort page"},
    }


def missing_gap(question_id="Q-02"):
    return {
        "question_id": question_id, "question": "What is the cancellation policy for the resort?",
        "topic": "booking policy", "intent": "transaction", "priority": "high", "priority_score": 70,
        "status": "missing", "reason": "No captured passage matched the subject of the observed question closely enough to assess as an answer.",
        "answer_quality_score": 0, "passage": None,
    }


class FakeOptimizer:
    """Stands in for the LLM boundary. Records every batch it was asked to draft."""

    def __init__(self, drafts: dict[str, str] | None = None, raise_error: bool = False):
        self.drafts = drafts or {}
        self.raise_error = raise_error
        self.batches: list[list[dict]] = []

    async def draft_batch(self, items):
        self.batches.append(list(items))
        if self.raise_error:
            raise RuntimeError("provider unavailable")
        return {item["question_id"]: self.drafts[item["question_id"]] for item in items if item["question_id"] in self.drafts}


@pytest.mark.asyncio
async def test_a_grounded_draft_is_accepted():
    gap = partial_gap()
    passage = gap["passage"]["excerpt"]
    generator = FakeOptimizer(drafts={gap["question_id"]: GROUNDED_DRAFT})
    detail = (await optimize_answers(gap_result([gap]), URL, generator))["detail"]
    item = detail["optimized_answers"][0]
    assert item["status"] == "drafted"
    assert item["draft_answer"] == GROUNDED_DRAFT
    # Deterministic checks reject obvious grounding failures; editorial review
    # remains the final factual verification step.
    assert item["grounding_verified"] is False
    assert detail["drafted_count"] == 1
    assert detail["optimization_coverage_score"] == 100
    # The passage itself was never mutated or discarded.
    assert item["source_excerpt"] == passage


@pytest.mark.asyncio
async def test_an_ungrounded_draft_falls_back_to_the_retained_passage():
    gap = partial_gap()
    # A plausible-sounding but fabricated amenity absent from the passage.
    generator = FakeOptimizer(drafts={gap["question_id"]: HALLUCINATED_DRAFT})
    detail = (await optimize_answers(gap_result([gap]), URL, generator))["detail"]
    item = detail["optimized_answers"][0]
    assert item["status"] == "fallback_extractive"
    assert "infinity pool" not in (item["draft_answer"] or "")
    assert "valet" not in (item["draft_answer"] or "")
    assert item["draft_answer"] == gap["passage"]["excerpt"]
    assert detail["drafted_count"] == 0
    assert detail["fallback_count"] == 1
    # A gap that failed drafting does not count against optimization coverage
    # the way a missing-passage gap would; it is still a partial gap attempt.
    assert detail["optimization_coverage_score"] == 0


@pytest.mark.asyncio
async def test_a_missing_gap_never_reaches_the_model_and_gets_a_checklist():
    gap = missing_gap()
    generator = FakeOptimizer()
    detail = (await optimize_answers(gap_result([gap]), URL, generator))["detail"]
    item = detail["optimized_answers"][0]
    assert item["status"] == "needs_facts"
    assert item["draft_answer"] is None
    assert item["checklist_action"]
    assert "cancellation policy" in item["checklist_action"].lower() or "policy" in item["checklist_action"].lower()
    # Nothing was ever sent to the model for a question with no retained passage.
    assert generator.batches == []
    # A gap with no draftable passage is excluded from the coverage score,
    # not scored as a failure.
    assert detail["optimization_coverage_score"] is None


@pytest.mark.asyncio
async def test_a_provider_failure_falls_back_without_raising():
    gap = partial_gap()
    generator = FakeOptimizer(raise_error=True)
    result = await optimize_answers(gap_result([gap]), URL, generator)
    item = result["detail"]["optimized_answers"][0]
    assert item["status"] == "fallback_extractive"
    assert item["fallback_reason"] == "provider_unavailable"
    assert "RuntimeError" in item["reason"]


@pytest.mark.asyncio
async def test_a_provider_outage_does_not_read_as_zero_content_coverage():
    """A live run once scored 0/100 'Critical' purely because the configured
    model ID had been deprecated — every gap fell back safely, but the score
    read as if the resort's content itself had zero coverage. A provider
    outage must be excluded from the score, not counted as a content failure."""
    gaps = [partial_gap(f"Q-{i:02d}") for i in range(1, 4)]
    generator = FakeOptimizer(raise_error=True)
    detail = (await optimize_answers(gap_result(gaps), URL, generator))["detail"]
    assert all(item["fallback_reason"] == "provider_unavailable" for item in detail["optimized_answers"])
    assert detail["drafting_unavailable_count"] == 3
    assert detail["optimization_coverage_score"] is None
    assert any("drafting provider was unavailable" in item for item in detail["limitations"])


@pytest.mark.asyncio
async def test_batches_stay_small_and_only_include_partial_gaps():
    gaps = [partial_gap(f"Q-{i:02d}", "The resort has a heated pool open from seven in the morning until nine at night.") for i in range(1, 5)] + [missing_gap("Q-99")]
    generator = FakeOptimizer()
    await optimize_answers(gap_result(gaps), URL, generator)
    assert all(len(batch) <= 3 for batch in generator.batches)
    sent_ids = {item["question_id"] for batch in generator.batches for item in batch}
    assert sent_ids == {f"Q-{i:02d}" for i in range(1, 5)}
    assert "Q-99" not in sent_ids


def test_zero_verified_gaps_produces_no_optimizable_items():
    detail = asyncio.run(optimize_answers(gap_result([]), URL, FakeOptimizer()))["detail"]
    assert detail["optimized_answers"] == []
    assert detail["optimization_coverage_score"] is None
    assert detail["gap_count"] == 0


@pytest.mark.parametrize("passage,draft", [
    (
        "The resort does not allow pets in guest rooms, and guests must contact the property team before arrival to discuss every special animal request and requirement safely.",
        "The resort does allow pets in guest rooms, and guests must contact the property team before arrival to discuss every special animal request and requirement safely safely.",
    ),
    (
        "Breakfast is not included in the room rate and guests must pay for breakfast separately at the restaurant every morning during their stay at the resort.",
        "Breakfast is included in the room rate and guests must pay for breakfast separately at the restaurant every morning during their stay at the resort at the resort.",
    ),
])
def test_validation_rejects_negation_reversals(passage, draft):
    accepted, reason = _validate_draft(draft, passage)
    assert accepted is False
    assert "polarity" in reason


def test_answer_optimization_is_independent_but_connected_runs_add_both_dependencies():
    individual = DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["answer_optimization"])
    assert individual.selected_agents == ["answer_optimization"]
    connected = DiagnosisInput(page_url=URL, selected_agents=["answer_optimization"])
    assert connected.selected_agents == ["question_discovery", "answer_gap", "answer_optimization"]


def test_answer_optimization_uses_standard_report_contract():
    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["answer_optimization"]))
    page = PageRecord(audit_id="opt", requested_url=URL, final_url=URL, status_code=200, title="Sterling Lake Palace Alleppey", main_text="Sterling Lake Palace is in Alleppey.")
    capture = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    capture["identity"] = {"property_name": "Sterling Lake Palace Alleppey", "branded_query": "Sterling Lake Palace Alleppey", "destination": "Alleppey"}
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    gap = partial_gap()
    result = asyncio.run(optimize_answers(gap_result([gap]), URL, FakeOptimizer(drafts={gap["question_id"]: GROUNDED_DRAFT})))
    run.tasks["answer_optimization"].status = "complete"
    run.tasks["answer_optimization"].result = result
    report = assemble_report(run)
    agent = report["agent_reports"]["answer_optimization"]
    assert agent["optimized_answers"]
    assert agent["score_kind"] == "readiness"
    assert agent["optimization_coverage_score"] == 100
    assert agent["measurements"][0]["label"] == "Verified gaps received"
    # The grounded draft becomes a reviewable "Fix it" replacement.
    assert agent["fixes"]
    assert agent["fixes"][0]["replacement"] == GROUNDED_DRAFT
    assert report["findings"]
    assert all(item["primary_agent"] == "answer_optimization" for item in report["findings"])


def test_zero_verified_gaps_does_not_force_a_punitive_score():
    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["answer_optimization"]))
    page = PageRecord(audit_id="opt", requested_url=URL, final_url=URL, status_code=200, title="Sterling Lake Palace Alleppey", main_text="Sterling Lake Palace is in Alleppey.")
    capture = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    capture["identity"] = {"property_name": "Sterling Lake Palace Alleppey", "branded_query": "Sterling Lake Palace Alleppey"}
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["answer_optimization"].status = "complete"
    run.tasks["answer_optimization"].result = asyncio.run(optimize_answers(gap_result([]), URL, FakeOptimizer()))
    report = assemble_report(run)
    agent = report["agent_reports"]["answer_optimization"]
    # Nothing to draft is a "no retained finding reduced this area" state,
    # not proof every answer failed; it must not read as a 0/100 score.
    assert agent["score"] > 0
    assert agent["score_status"]["label"] == "Evidence limited"
    assert agent["limitations"]


def test_provider_outage_does_not_read_as_a_critical_report_score():
    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["answer_optimization"]))
    page = PageRecord(audit_id="opt", requested_url=URL, final_url=URL, status_code=200, title="Sterling Lake Palace Alleppey", main_text="Sterling Lake Palace is in Alleppey.")
    capture = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    capture["identity"] = {"property_name": "Sterling Lake Palace Alleppey"}
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["answer_optimization"].status = "complete"
    run.tasks["answer_optimization"].result = asyncio.run(optimize_answers(gap_result([partial_gap()]), URL, FakeOptimizer(raise_error=True)))
    report = assemble_report(run)
    agent = report["agent_reports"]["answer_optimization"]
    assert agent["score_status"]["label"] != "Critical"
    assert agent["score_status"]["label"] == "Evidence limited"


def test_answer_gap_zero_observed_questions_does_not_force_a_punitive_score():
    """Locks the same fix for Answer Gap: no assessable question is not a 0."""
    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["answer_gap"]))
    page = PageRecord(audit_id="gap", requested_url=URL, final_url=URL, status_code=200, title="Sterling Lake Palace Alleppey", main_text="Generic text with no question-style heading at all.")
    capture = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    capture["identity"] = {"property_name": "Sterling Lake Palace Alleppey"}
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["answer_gap"].status = "complete"
    run.tasks["answer_gap"].result = analyze_answer_gaps(capture, discover_questions(capture, URL), URL)
    report = assemble_report(run)
    agent = report["agent_reports"]["answer_gap"]
    assert agent["score"] > 0
    assert agent["score_status"]["label"] == "Evidence limited"


def test_end_to_end_pipeline_from_discovery_through_optimization():
    """Full chain sanity check: discover -> gap -> optimize stays contract-shaped."""
    page = PageRecord(
        audit_id="pipeline", requested_url=URL, final_url=URL, status_code=200,
        title="Sterling Lake Palace Alleppey", h2=["Does the resort have a pool?"],
        main_text="Does the resort have a pool? The resort restaurant serves regional dishes for breakfast and dinner.",
    )
    capture = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    capture["identity"] = {"property_name": "Sterling Lake Palace Alleppey", "branded_query": "Sterling Lake Palace Alleppey", "destination": "Alleppey"}
    discovery = discover_questions(capture, URL)
    gaps = analyze_answer_gaps(capture, discovery, URL)
    result = asyncio.run(optimize_answers(gaps, URL, FakeOptimizer()))
    assert result["status"] == "complete"
    assert result["detail"]["gap_count"] == len(gaps["detail"]["prioritized_gaps"])
    ids_in = {g["question_id"] for g in gaps["detail"]["prioritized_gaps"]}
    ids_out = {item["question_id"] for item in result["detail"]["optimized_answers"]}
    assert ids_in == ids_out
