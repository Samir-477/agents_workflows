from question_intent.analysis import INTENT_STAGES, _classify_intent, _classify_question, classify_intent
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


def capture_data():
    page = PageRecord(
        audit_id="intent", requested_url=URL, final_url=URL, status_code=200,
        title="Sterling Lake Palace Alleppey", main_text="Sterling Lake Palace is a heritage property in Alleppey.",
    )
    data = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    data["identity"] = {"property_name": "Sterling Lake Palace Alleppey", "branded_query": "Sterling Lake Palace Alleppey"}
    return data


def test_classifier_separates_comparison_from_suitability():
    """question_discovery's own coarse bucket lumps 'is it good for families'
    in with a real competitor comparison. This taxonomy must not."""
    assert _classify_question("Is Sterling better than Club Mahindra?") == ("Evaluate", "Commercial investigation", "Comparison")
    assert _classify_question("Is Sterling good for families with young children?") == ("Evaluate", "Commercial investigation", "Suitability")


def test_classifier_separates_local_logistics_from_arrival_timing():
    """question_discovery's own coarse bucket lumps 'how far is the airport'
    in with 'what time is check-in' under the same 'planning' label. This
    taxonomy's 'Local' stage is destination logistics only."""
    assert _classify_question("How far is the airport from the resort?")[0] == "Plan"
    assert _classify_question("What time is check-in and check-out?")[0] in {"Plan", "Manage"}


def test_classifier_matches_common_inflections_not_just_the_bare_stem():
    """A first pass used whole-word matching for every Transactional keyword,
    which silently missed 'cancellation' (from 'cancel') and 'pricing' (from
    'price', which drops its final e before -ing) — both far more common in
    real questions than the bare stem itself."""
    assert _classify_intent("What is the cancellation policy for the resort?") == "Transactional"
    assert _classify_intent("What is the pricing for a suite upgrade?") == "Transactional"
    assert _classify_intent("Can you compare this resort to nearby alternatives?") == "Commercial investigation"
    # And the inflected match must not over-reach into an unrelated word.
    assert _classify_intent("Does the room have a luggage compartment?") != "Comparison"


def test_classifier_does_not_collide_on_substrings_found_in_real_page_text():
    # The same "rate" inside "corporate" collision FAQ Intelligence's
    # classifier hit on real captured text applies to this taxonomy too.
    assert _classify_intent("Does the resort cater to destination weddings and corporate retreats?") != "Transactional"
    assert _classify_intent("What is the nightly rate for a lake-view room?") == "Transactional"


def test_every_question_gets_classified_into_a_fixed_stage():
    capture = capture_data()
    research = QuestionEvidence(question="What is the cancellation policy?")
    discovery = discover_questions(capture, URL, __import__("types").SimpleNamespace(questions=[research]))
    detail = classify_intent(discovery, None, URL)["detail"]
    assert {row["intent"] for row in detail["distribution"]} == set(INTENT_STAGES)
    assert sum(row["count"] for row in detail["distribution"]) == detail["observed_question_count"]
    assert sum(row["hypothesis_count"] for row in detail["distribution"]) == detail["hypothesis_question_count"]
    assert detail["used_answer_gap"] is False


def test_answer_gap_is_optional_but_enriches_reprioritization():
    capture = capture_data()
    research = QuestionEvidence(question="What is the cancellation policy for the resort?")
    discovery = discover_questions(capture, URL, __import__("types").SimpleNamespace(questions=[research]))
    without_gap = classify_intent(discovery, None, URL)["detail"]
    assert without_gap["reprioritized_gaps"] == []
    assert without_gap["used_answer_gap"] is False
    assert any("Answer Gap was unavailable" in item for item in without_gap["limitations"])

    gaps = analyze_answer_gaps(capture, discovery, URL)
    with_gap = classify_intent(discovery, gaps, URL)["detail"]
    assert with_gap["used_answer_gap"] is True
    assert with_gap["reprioritized_gaps"]
    assert with_gap["reprioritized_gaps"][0]["intent"] == "Transactional"
    assert with_gap["reprioritized_gaps"][0]["journey_stage"] == "Manage"


def test_early_stage_gaps_remain_in_the_queue_with_lower_weight():
    """Every verified gap stays traceable; stage changes its order rather
    than silently removing useful work from the connected plan."""
    capture = capture_data()
    research = QuestionEvidence(question="What are the hidden non-touristy spots near the resort?")
    discovery = discover_questions(capture, URL, __import__("types").SimpleNamespace(questions=[research]))
    gaps = analyze_answer_gaps(capture, discovery, URL)
    detail = classify_intent(discovery, gaps, URL)["detail"]
    assert len(detail["reprioritized_gaps"]) == 1
    assert detail["reprioritized_gaps"][0]["journey_stage"] == "Discover"
    assert detail["reprioritized_gaps"][0]["weighted_priority_score"] < 75


def test_high_value_readiness_score_is_none_safe_not_punitive():
    """No observed transactional or comparison question this run must not
    read as 0% readiness — the same conflation caught twice already this
    session for Answer Gap and FAQ Intelligence."""
    capture = capture_data()
    research = QuestionEvidence(question="What is Alleppey known for historically?")
    discovery = discover_questions(capture, URL, __import__("types").SimpleNamespace(questions=[research]))
    gaps = analyze_answer_gaps(capture, discovery, URL)
    detail = classify_intent(discovery, gaps, URL)["detail"]
    assert detail["high_value_readiness_score"] is None

    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["question_intent"]))
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["question_intent"].status = "complete"
    run.tasks["question_intent"].result = {"status": "complete", "detail": detail}
    report = assemble_report(run)
    agent = report["agent_reports"]["question_intent"]
    assert agent["score"] > 0
    assert agent["score_status"]["label"] == "Evidence limited"
    assert agent["score_status"]["label"] != "Critical"


def test_a_genuine_high_value_gap_still_reads_as_critical():
    capture = capture_data()
    research = QuestionEvidence(question="What is the cancellation policy for the resort?")
    discovery = discover_questions(capture, URL, __import__("types").SimpleNamespace(questions=[research]))
    gaps = analyze_answer_gaps(capture, discovery, URL)
    detail = classify_intent(discovery, gaps, URL)["detail"]
    assert detail["high_value_readiness_score"] is not None

    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["question_intent"]))
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["question_intent"].status = "complete"
    run.tasks["question_intent"].result = {"status": "complete", "detail": detail}
    report = assemble_report(run)
    agent = report["agent_reports"]["question_intent"]
    assert agent["score_status"]["label"] != "Evidence limited"


def test_question_intent_is_independent_and_connected_runs_include_evidence_dependencies():
    individual = DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["question_intent"])
    assert individual.selected_agents == ["question_intent"]
    connected = DiagnosisInput(page_url=URL, selected_agents=["question_intent"])
    assert connected.selected_agents == ["question_discovery", "answer_gap", "question_intent"]


def test_available_amenities_is_not_misclassified_as_booking_intent():
    assert _classify_question("What amenities are available at the resort?") == (
        "Discover", "Informational", "Property discovery"
    )


def test_question_intent_uses_standard_report_contract():
    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["question_intent"]))
    capture = capture_data()
    research = QuestionEvidence(question="What is the cancellation policy for the resort?")
    discovery = discover_questions(capture, URL, __import__("types").SimpleNamespace(questions=[research]))
    gaps = analyze_answer_gaps(capture, discovery, URL)
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["question_intent"].status = "complete"
    run.tasks["question_intent"].result = classify_intent(discovery, gaps, URL)
    report = assemble_report(run)
    agent = report["agent_reports"]["question_intent"]
    assert agent["intent_distribution"]
    assert agent["content_strategy"]
    assert agent["score_kind"] == "readiness"
    assert agent["measurements"][0]["label"] == "Questions classified"
    assert report["findings"]
    assert all(item["primary_agent"] == "question_intent" for item in report["findings"])
    # This agent reprioritizes; it never offers its own replacement copy.
    assert agent["fixes"] == []
