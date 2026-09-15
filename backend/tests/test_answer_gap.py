from answer_gap.analysis import analyze_answer_gaps
from diagnosis.evidence import snapshot
from diagnosis.models import DiagnosisInput
from diagnosis.reporting import assemble_report
from diagnosis.storage import MemoryDiagnosisRepository
from question_discovery.analysis import discover_questions
from seo_audit.crawler import CrawlResult
from seo_audit.models import HeadingRecord, PageRecord


URL = "https://www.sterlingholidays.com/resorts-hotels/lake-palace-alleppey"


def capture_data():
    page = PageRecord(
        audit_id="gap", requested_url=URL, final_url=URL, status_code=200,
        title="Sterling Lake Palace Alleppey", h1=["Sterling Lake Palace Alleppey"],
        h2=["What dining options are available?", "Does the resort have a pool?"],
        headings=[
            HeadingRecord(level="h2", text="What dining options are available?"),
            HeadingRecord(level="h2", text="Does the resort have a pool?"),
        ],
        main_text=(
            "What dining options are available? The resort restaurant serves regional and international dishes for breakfast and dinner. "
            "Does the resort have a pool?"
        ),
        schema_names=["Sterling Lake Palace Alleppey"],
    )
    data = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    data["identity"] = {"property_name": "Sterling Lake Palace Alleppey", "branded_query": "Sterling Lake Palace Alleppey", "destination": "Alleppey"}
    return data


def test_answer_gap_scores_only_observed_questions_and_retains_passage_evidence():
    capture = capture_data()
    discovery = discover_questions(capture, URL)
    detail = analyze_answer_gaps(capture, discovery, URL)["detail"]
    assert detail["question_count"] == detail["answered_count"] + detail["partial_count"] + detail["missing_count"] + detail["unable_to_verify_count"]
    assert detail["discovery_provenance"]["inferred_questions_excluded"] > 0
    dining = next(item for item in detail["assessments"] if "dining" in item["question"].lower())
    assert dining["status"] == "answered"
    assert dining["passage"]["excerpt"]
    pool = next(item for item in detail["assessments"] if "pool" in item["question"].lower())
    assert pool["status"] == "missing"
    assert any(item["question_id"] == pool["question_id"] for item in detail["prioritized_gaps"])


def test_answer_gap_is_independent_but_connected_runs_add_discovery_dependency():
    individual = DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["answer_gap"])
    assert individual.selected_agents == ["answer_gap"]
    connected = DiagnosisInput(page_url=URL, selected_agents=["answer_gap"])
    assert connected.selected_agents == ["question_discovery", "answer_gap"]


def test_answer_gap_uses_standard_report_contract():
    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["answer_gap"]))
    capture = capture_data()
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["answer_gap"].status = "complete"
    run.tasks["answer_gap"].result = analyze_answer_gaps(capture, discover_questions(capture, URL), URL)
    report = assemble_report(run)
    agent = report["agent_reports"]["answer_gap"]
    assert agent["answer_coverage"]
    assert agent["score_kind"] == "readiness"
    assert agent["measurements"][0]["label"] == "Observed questions assessed"
    assert report["findings"]
    assert all(item["primary_agent"] == "answer_gap" for item in report["findings"])


def test_unrelated_transport_passage_is_not_treated_as_an_airport_shuttle_answer():
    page = PageRecord(
        audit_id="gap-relevance", requested_url=URL, final_url=URL, status_code=200,
        title="Sterling Lake Palace Alleppey",
        main_text="Guests can relax in the airport lounge before departure. The resort offers a lakeside restaurant and family rooms.",
    )
    capture = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    capture["identity"] = {"property_name": "Sterling Lake Palace Alleppey", "branded_query": "Sterling Lake Palace Alleppey"}
    from serp_competitor.models import QuestionEvidence
    research = type("Research", (), {"questions": [QuestionEvidence(question="Does the resort provide an airport shuttle?")]})()
    discovery = discover_questions(capture, URL, research)
    assessment = analyze_answer_gaps(capture, discovery, URL)["detail"]["assessments"][0]
    assert assessment["status"] == "missing"
    assert assessment["passage"] is None
