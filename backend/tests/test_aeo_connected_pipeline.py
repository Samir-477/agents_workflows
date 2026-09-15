import asyncio

import pytest

from aeo_shared.contracts import validate_aeo_result
from answer_gap.analysis import analyze_answer_gaps
from answer_optimization.analysis import optimize_answers
from diagnosis.evidence import snapshot
from diagnosis.models import DiagnosisInput
from diagnosis.reporting import assemble_report
from diagnosis.storage import MemoryDiagnosisRepository
from faq_intelligence.analysis import audit_faq_coverage
from question_discovery.analysis import discover_questions
from question_intent.analysis import classify_intent
from seo_audit.crawler import CrawlResult
from seo_audit.models import PageRecord
from serp_competitor.models import QuestionEvidence


URL = "https://www.sterlingholidays.com/resorts-hotels/lake-palace-alleppey"


def _capture():
    page = PageRecord(
        audit_id="connected-aeo", requested_url=URL, final_url=URL,
        status_code=200, title="Sterling Lake Palace Alleppey",
        main_text="Sterling Lake Palace is a heritage resort in Alleppey.",
    )
    result = snapshot(CrawlResult(pages=[page], origin="https://www.sterlingholidays.com"))
    result["identity"] = {"property_name": "Sterling Lake Palace Alleppey", "branded_query": "Sterling Lake Palace Alleppey"}
    return result


def test_connected_agents_collapse_one_question_into_one_evidence_linked_action():
    capture = _capture()
    research = type("Research", (), {"questions": [QuestionEvidence(question="Does the resort have a swimming pool?")]})()
    discovery = discover_questions(capture, URL, research)
    gaps = analyze_answer_gaps(capture, discovery, URL)
    optimization = asyncio.run(optimize_answers(gaps, URL, None))
    faq = audit_faq_coverage(discovery, gaps, optimization, URL)
    intent = classify_intent(discovery, gaps, URL)

    repository = MemoryDiagnosisRepository()
    run = repository.create(DiagnosisInput(page_url=URL, selected_agents=[
        "question_discovery", "answer_gap", "answer_optimization", "faq_intelligence", "question_intent",
    ]))
    run.tasks["capture"].status, run.tasks["capture"].result = "complete", capture
    for name, result in {
        "question_discovery": discovery, "answer_gap": gaps,
        "answer_optimization": optimization, "faq_intelligence": faq,
        "question_intent": intent,
    }.items():
        run.tasks[name].status, run.tasks[name].result = "complete", result

    report = assemble_report(run)
    findings = [item for item in report["findings"] if item.get("lineage_id")]
    assert len(findings) == 1
    finding = findings[0]
    assert set(finding["supporting_agents"]) == {"answer_optimization", "faq_intelligence", "question_intent"}
    assert len(finding["evidence_ids"]) == 4
    assert all(evidence_id in report["evidence"] for evidence_id in finding["evidence_ids"])


def test_aeo_runtime_contract_rejects_incomplete_results():
    with pytest.raises(ValueError, match="omitted required fields"):
        validate_aeo_result("answer_gap", {"status": "complete", "detail": {"limitations": []}})
