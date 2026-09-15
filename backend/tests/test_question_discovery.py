from types import SimpleNamespace

from diagnosis.evidence import snapshot
from diagnosis.models import DiagnosisInput
from diagnosis.reporting import assemble_report
from diagnosis.storage import MemoryDiagnosisRepository
from question_discovery.analysis import discover_questions
from seo_audit.crawler import CrawlResult
from seo_audit.models import HeadingRecord, PageRecord
from serp_competitor.models import QuestionEvidence


URL = "https://www.sterlingholidays.com/resorts-hotels/lake-palace-alleppey"


def captured_resort():
    page = PageRecord(
        audit_id="questions", requested_url=URL, final_url=URL, status_code=200,
        title="Sterling Lake Palace Alleppey",
        h1=["Sterling Lake Palace Alleppey"],
        h2=["What dining options are available?"],
        headings=[HeadingRecord(level="h2", text="What dining options are available?")],
        main_text="Sterling Lake Palace is in Alleppey. The resort includes a restaurant and rooms overlooking the backwaters.",
        schema_names=["Sterling Lake Palace Alleppey"],
    )
    data = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    data["identity"] = {
        "property_name": "Sterling Lake Palace Alleppey", "branded_query": "Sterling Lake Palace Alleppey",
        "destination": "Alleppey",
    }
    return data


def test_question_discovery_preserves_provenance_and_cross_engine_handoffs():
    research = SimpleNamespace(questions=[QuestionEvidence(question="Is Sterling Lake Palace good for families?")])
    detail = discover_questions(captured_resort(), URL, research)["detail"]
    observed = [item for item in detail["questions"] if item["evidence_status"] == "observed"]
    inferred = [item for item in detail["questions"] if item["evidence_status"] == "inferred"]
    assert observed and inferred
    assert detail["observed_question_count"] == len(observed)
    assert all(set(item["handoffs"]) == {"seo", "aeo", "geo"} for item in detail["questions"])
    assert next(item for item in observed if "dining" in item["question"].lower())["page_coverage"] == "explicit"
    assert 0 <= detail["question_coverage_score"] <= 100
    assert detail["evidence_quality"]["status"] in {"partial", "verified"}
    assert detail["source_ledger"]
    assert detail["unanswered_count"] == sum(item["page_coverage"] == "absent" for item in observed)


def test_question_discovery_report_uses_standard_contract_in_individual_mode():
    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["question_discovery"]))
    assert list(run.tasks) == ["capture", "question_discovery"]
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = captured_resort()
    run.tasks["question_discovery"].status = "complete"
    run.tasks["question_discovery"].result = discover_questions(captured_resort(), URL)
    report = assemble_report(run)
    agent = report["agent_reports"]["question_discovery"]
    assert report["session_intelligence"]["engine_scores"][0]["engine"] == "AEO"
    assert agent["question_landscape"]
    assert agent["question_clusters"]
    assert agent["measurements"]
    assert agent["method"]
    assert agent["score_basis"].startswith("Discovery confidence")
    assert agent["evidence_ids"]
    assert report["session_intelligence"]["priorities"] == []
    assert report["session_intelligence"]["recommended_agent_handoffs"]
    assert agent["score_kind"] == "evidence_confidence"
    assert agent["benchmarks"] == []
    assert agent["action_plan"] == []


def test_observed_unanswered_question_routes_to_answer_gap_without_inventing_a_fix():
    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["question_discovery"]))
    capture = captured_resort()
    research = SimpleNamespace(questions=[QuestionEvidence(question="Does Sterling Lake Palace have a swimming pool?")])
    run.tasks["capture"].status = "complete"
    run.tasks["capture"].result = capture
    run.tasks["question_discovery"].status = "complete"
    run.tasks["question_discovery"].result = discover_questions(capture, URL, research)

    report = assemble_report(run)
    priorities = report["session_intelligence"]["priorities"]
    assert priorities == []
    assert report["findings"] == []
    handoff = report["session_intelligence"]["recommended_agent_handoffs"][0]
    assert handoff["target_agent"] == "answer_gap"
    assert handoff["question_ids"]


def test_question_ids_follow_the_presented_priority_order():
    research = SimpleNamespace(questions=[QuestionEvidence(question="Is Sterling Lake Palace good for families?")])
    questions = discover_questions(captured_resort(), URL, research)["detail"]["questions"]
    # Identifiers are assigned after ranking, so a reader of the report or PDF
    # sees Q-01 first rather than the order candidates happened to be merged in.
    assert [item["id"] for item in questions] == [f"Q-{position:02d}" for position in range(1, len(questions) + 1)]
    assert [item["priority_score"] for item in questions] == sorted((item["priority_score"] for item in questions), reverse=True)


def test_question_clusters_do_not_repeat_the_same_topic_label():
    research = SimpleNamespace(questions=[QuestionEvidence(question="What amenities does Sterling Lake Palace have?")])
    detail = discover_questions(captured_resort(), URL, research)["detail"]
    labels = [cluster["label"] for cluster in detail["clusters"]]
    # Template topics are lowercase and intent-derived topics are capitalized;
    # counting both produced two clusters rendering the identical label.
    assert len(labels) == len(set(labels)), labels
    assert sum(cluster["question_count"] for cluster in detail["clusters"]) == len(detail["questions"])


def test_branded_and_unbranded_question_variants_are_merged():
    research = SimpleNamespace(questions=[QuestionEvidence(question="What dining options are available at Sterling Lake Palace Alleppey?")])
    detail = discover_questions(captured_resort(), URL, research)["detail"]
    dining = [item for item in detail["questions"] if item["topic"] == "Dining"]
    assert len(dining) == 1
    assert dining[0]["evidence_status"] == "observed"
    assert dining[0]["variants"]


def test_inferred_questions_never_change_observed_coverage_metrics():
    detail = discover_questions(captured_resort(), URL)["detail"]
    observed = [item for item in detail["questions"] if item["evidence_status"] == "observed"]
    assert detail["unanswered_count"] == sum(item["page_coverage"] == "absent" for item in observed)
    assert detail["explicit_answer_count"] == sum(item["page_coverage"] == "explicit" for item in observed)


def test_lineage_ids_are_stable_when_presentation_order_changes():
    first = discover_questions(captured_resort(), URL)["detail"]["questions"]
    second = discover_questions(captured_resort(), URL)["detail"]["questions"]
    assert {item["question"]: item["lineage_id"] for item in first} == {item["question"]: item["lineage_id"] for item in second}
    assert all(item["lineage_id"].startswith("AQ-") for item in first)


def test_non_english_run_does_not_inject_english_framework_questions():
    detail = discover_questions(captured_resort(), URL, language="fr")["detail"]
    assert all(item["evidence_status"] == "observed" for item in detail["questions"])
    assert any("English" in item for item in detail["limitations"])
