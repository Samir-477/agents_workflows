from faq_intelligence.analysis import FAQ_CATEGORIES, _classify, audit_faq_coverage
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
        audit_id="faq", requested_url=URL, final_url=URL, status_code=200,
        title="Sterling Lake Palace Alleppey", h1=["Sterling Lake Palace Alleppey"],
        h2=["What dining options are available?"],
        main_text=(
            "What dining options are available? The resort restaurant serves regional and international dishes "
            "for breakfast and dinner. Does the resort have a pool? "
        ),
        schema_names=["Sterling Lake Palace Alleppey"],
    )
    data = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    data["identity"] = {"property_name": "Sterling Lake Palace Alleppey", "branded_query": "Sterling Lake Palace Alleppey", "destination": "Alleppey"}
    return data


def optimized_result(drafted_ids):
    return {"detail": {"optimized_answers": [
        {"question_id": qid, "draft_answer": "A grounded direct answer.", "status": "drafted", "source_url": URL}
        for qid in drafted_ids
    ]}}


def test_classifier_does_not_collide_on_substrings_found_in_real_page_text():
    """A live run against sterlingholidays.com once misclassified 'Does the
    resort cater to destination weddings and corporate retreats?' as Booking
    Policy (via 'rate' inside 'corporate') and 'What are the hidden spots
    accessible from the resort?' as Accessibility (via 'accessib' inside
    'accessible'). Both were real, found by testing against real text."""
    assert _classify("Does the resort cater to destination weddings and corporate retreats?") != "Booking Policy"
    assert _classify("What are the hidden spots accessible from the resort?") != "Accessibility"
    assert _classify("Are spacious rooms available at this resort?") != "Amenities"
    assert _classify("What is the room rate for a weekend stay?") == "Booking Policy"
    assert _classify("What accessibility information is available?") == "Accessibility"
    assert _classify("Is this resort pet-friendly?") == "Pets"


def test_every_category_gets_an_audited_entry():
    capture = capture_data()
    discovery = discover_questions(capture, URL)
    gaps = analyze_answer_gaps(capture, discovery, URL)
    detail = audit_faq_coverage(discovery, gaps, None, URL)["detail"]
    assert {item["category"] for item in detail["faq_entries"]} == set(FAQ_CATEGORIES)
    assert detail["category_count"] == len(FAQ_CATEGORIES)
    assert detail["ready_count"] + detail["needs_review_count"] + detail["not_covered_count"] + detail["no_question_count"] == len(FAQ_CATEGORIES)


def test_a_real_dining_answer_marks_dining_covered():
    capture = capture_data()
    discovery = discover_questions(capture, URL)
    gaps = analyze_answer_gaps(capture, discovery, URL)
    detail = audit_faq_coverage(discovery, gaps, None, URL)["detail"]
    dining = next(item for item in detail["faq_entries"] if item["category"] == "Dining")
    assert dining["status"] == "covered"
    assert dining["evidence_source"] == "answer_gap"
    assert dining["answer"]


def test_a_category_with_no_observed_question_is_distinguished_from_a_verified_gap():
    capture = capture_data()
    # No pet-related content or question is present anywhere in this fixture.
    discovery = discover_questions(capture, URL)
    gaps = analyze_answer_gaps(capture, discovery, URL)
    detail = audit_faq_coverage(discovery, gaps, None, URL)["detail"]
    pets = next(item for item in detail["faq_entries"] if item["category"] == "Pets")
    # Only the inferred template question exists here, never an observed one.
    assert pets["status"] == "not_assessed"
    assert pets["question_id"] is None
    assert pets["evidence_source"] is None
    assert "no observed guest question" in pets["reason"].lower()


def test_a_verified_missing_answer_is_a_stronger_signal_than_no_demand():
    capture = capture_data()
    research = QuestionEvidence(question="Does the resort have a swimming pool?")
    discovery = discover_questions(capture, URL, __import__("types").SimpleNamespace(questions=[research]))
    gaps = analyze_answer_gaps(capture, discovery, URL)
    detail = audit_faq_coverage(discovery, gaps, None, URL)["detail"]
    amenities = next(item for item in detail["faq_entries"] if item["category"] == "Amenities")
    assert amenities["status"] == "not_covered"
    assert amenities["question_id"] is not None
    assert amenities["evidence_source"] == "answer_gap"


def test_an_answer_optimization_draft_is_preferred_over_the_raw_passage():
    capture = capture_data()
    discovery = discover_questions(capture, URL)
    gaps = analyze_answer_gaps(capture, discovery, URL)
    dining_question = next(q for q in discovery["detail"]["questions"] if q["topic"] == "Dining" or "dining" in q["question"].lower())
    optimization = optimized_result([dining_question["id"]])
    detail = audit_faq_coverage(discovery, gaps, optimization, URL)["detail"]
    dining = next(item for item in detail["faq_entries"] if item["category"] == "Dining")
    assert dining["evidence_source"] == "answer_optimization"
    assert dining["answer"] == "A grounded direct answer."
    assert detail["used_answer_optimization"] is True


def test_faq_coverage_score_is_always_a_real_number():
    capture = capture_data()
    discovery = discover_questions(capture, URL)
    gaps = analyze_answer_gaps(capture, discovery, URL)
    detail = audit_faq_coverage(discovery, gaps, None, URL)["detail"]
    # This fixture has assessed categories. Unassessed baseline categories are
    # excluded from the denominator.
    assert isinstance(detail["faq_coverage_score"], int)
    assert 0 <= detail["faq_coverage_score"] <= 100


def test_faq_intelligence_is_independent_but_connected_runs_add_both_dependencies():
    individual = DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["faq_intelligence"])
    assert individual.selected_agents == ["faq_intelligence"]
    connected = DiagnosisInput(page_url=URL, selected_agents=["faq_intelligence"])
    assert connected.selected_agents == ["question_discovery", "answer_gap", "faq_intelligence"]


def test_faq_intelligence_uses_standard_report_contract():
    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["faq_intelligence"]))
    capture = capture_data()
    discovery = discover_questions(capture, URL)
    gaps = analyze_answer_gaps(capture, discovery, URL)
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["faq_intelligence"].status = "complete"
    run.tasks["faq_intelligence"].result = audit_faq_coverage(discovery, gaps, None, URL)
    report = assemble_report(run)
    agent = report["agent_reports"]["faq_intelligence"]
    assert agent["faq_entries"]
    assert agent["score_kind"] == "readiness"
    assert agent["measurements"][0]["label"] == "Categories covered"
    # Unassessed baseline categories remain visible in the matrix but do not
    # become implementation findings without an observed question.
    assert all(item["primary_agent"] == "faq_intelligence" for item in report["findings"])
    # This agent audits; it never offers its own replacement copy.
    assert agent["fixes"] == []


def test_no_observed_demand_reads_as_evidence_limited_not_critical():
    """A live run against sterlingholidays.com scored 0/100 'Critical' when
    every one of its six real observed questions happened to be about niche
    topics (weddings, local culture) outside the ten-category taxonomy —
    zero verified gaps, just zero observed demand. That must not read as a
    confirmed content fault the same way a real verified gap does."""
    page = PageRecord(audit_id="faq2", requested_url=URL, final_url=URL, status_code=200, title="Sterling Lake Palace Alleppey", main_text="Sterling Lake Palace is a heritage property in Alleppey.")
    capture = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    capture["identity"] = {"property_name": "Sterling Lake Palace Alleppey", "branded_query": "Sterling Lake Palace Alleppey"}
    # An observed question entirely outside the taxonomy, and no template
    # matches anything either since the page text gives no other signal.
    research = QuestionEvidence(question="Does the resort host destination weddings?")
    discovery = discover_questions(capture, URL, __import__("types").SimpleNamespace(questions=[research]))
    gaps = analyze_answer_gaps(capture, discovery, URL)
    detail = audit_faq_coverage(discovery, gaps, None, URL)["detail"]
    assert detail["not_covered_count"] == 0
    assert detail["no_question_count"] > 0

    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["faq_intelligence"]))
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["faq_intelligence"].status = "complete"
    run.tasks["faq_intelligence"].result = {"status": "complete", "detail": detail}
    report = assemble_report(run)
    agent = report["agent_reports"]["faq_intelligence"]
    assert agent["score_status"]["label"] == "Evidence limited"
    assert agent["score_status"]["label"] != "Critical"


def test_a_genuine_verified_gap_still_reads_as_critical():
    """The 'Evidence limited' override must not mask a real confirmed gap."""
    capture = capture_data()
    research = QuestionEvidence(question="Does the resort have a swimming pool?")
    discovery = discover_questions(capture, URL, __import__("types").SimpleNamespace(questions=[research]))
    gaps = analyze_answer_gaps(capture, discovery, URL)
    detail = audit_faq_coverage(discovery, gaps, None, URL)["detail"]
    assert detail["not_covered_count"] > 0

    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["faq_intelligence"]))
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["faq_intelligence"].status = "complete"
    run.tasks["faq_intelligence"].result = {"status": "complete", "detail": detail}
    report = assemble_report(run)
    agent = report["agent_reports"]["faq_intelligence"]
    assert agent["score_status"]["label"] != "Evidence limited"


def test_faq_intelligence_never_offers_a_finding_for_a_ready_category():
    capture = capture_data()
    discovery = discover_questions(capture, URL)
    gaps = analyze_answer_gaps(capture, discovery, URL)
    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["faq_intelligence"]))
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["faq_intelligence"].status = "complete"
    run.tasks["faq_intelligence"].result = audit_faq_coverage(discovery, gaps, None, URL)
    report = assemble_report(run)
    finding_titles = " ".join(item["title"] for item in report["findings"])
    assert "Dining FAQ is not covered" not in finding_titles
    assert "Dining FAQ needs editorial review" not in finding_titles


def test_one_missing_question_keeps_an_otherwise_answered_category_open():
    discovery = {"detail": {"questions": [
        {"id": "Q-01", "lineage_id": "AQ-pool", "question": "Does the resort have a pool?", "evidence_status": "observed"},
        {"id": "Q-02", "lineage_id": "AQ-heated", "question": "Is the resort pool heated?", "evidence_status": "observed"},
    ]}}
    gaps = {"detail": {"assessments": [
        {"question_id": "Q-01", "status": "answered", "passage": {"excerpt": "The resort has an outdoor pool.", "source_url": URL}},
        {"question_id": "Q-02", "status": "missing", "passage": None},
    ]}}
    amenities = next(item for item in audit_faq_coverage(discovery, gaps, None, URL)["detail"]["faq_entries"] if item["category"] == "Amenities")
    assert amenities["status"] == "not_covered"
    assert amenities["observed_question_count"] == 2
    assert "Is the resort pool heated?" in amenities["unresolved_questions"]
