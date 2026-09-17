from aeo_opportunity.analysis import build_aeo_opportunities
from diagnosis.models import DiagnosisInput


URL = "https://www.sterlingholidays.com/resorts-hotels/lake-palace-alleppey"


def test_opportunity_deduplicates_gap_and_structure_by_question_lineage():
    discovery = {"detail": {"observed_question_count": 1, "discovery_confidence_score": 80, "questions": [{"id": "Q-01", "lineage_id": "AQ-pool", "question": "Does the resort have a pool?", "evidence_status": "observed", "journey_stage": "Evaluate", "source_types": ["page_heading"]}]}}
    gap = {"detail": {"assessments": [{"question_id": "Q-01", "lineage_id": "AQ-pool"}], "prioritized_gaps": [{"question_id": "Q-01", "lineage_id": "AQ-pool", "question": "Does the resort have a pool?", "status": "partial", "recommended_action": "Complete the pool answer.", "completion_check": "The answer is complete.", "passage": {"excerpt": "Outdoor pool.", "source_url": URL}}]}}
    structure = {"detail": {"structure_improvements": [{"question_id": "Q-01", "lineage_id": "AQ-pool", "question": "Does the resort have a pool?", "structure_status": "weak", "structure_score": 42, "recommended_action": "Restructure the answer.", "source_excerpt": "Outdoor pool.", "source_url": URL}]}}
    faq = {"detail": {"faq_entries": [{"status": "not_covered", "question_id": "Q-01"}]}}
    intent = {"detail": {"classified_questions": [{"question_id": "Q-01", "journey_stage": "Evaluate"}]}}
    result = build_aeo_opportunities(discovery, gap, structure, faq, intent, URL)["detail"]
    assert result["opportunity_count"] == 1
    assert result["opportunities"][0]["lineage_id"] == "AQ-pool"
    assert set(result["opportunities"][0]["source_agents"]) == {"answer_gap", "answer_structure", "faq_intelligence", "question_intent"}
    assert result["roadmap"]["now"] == ["AQ-pool"]
    assert result["aeo_opportunity_score"] == 0


def test_opportunity_collapses_variant_ids_into_one_lineage():
    discovery = {"detail": {"discovery_confidence_score": 80, "questions": [
        {"id": "Q-01", "lineage_id": "AQ-pool", "question": "Does the resort have a pool?", "evidence_status": "observed", "source_types": ["page_heading"]},
        {"id": "Q-02", "lineage_id": "AQ-pool", "question": "Is there a swimming pool?", "evidence_status": "observed", "source_types": ["google_related_question"]},
    ]}}
    gap = {"detail": {"assessments": [{"question_id": "Q-01"}], "prioritized_gaps": [{"question_id": "Q-01", "status": "partial", "recommended_action": "Complete the answer.", "passage": {"excerpt": "Outdoor pool."}}]}}
    result = build_aeo_opportunities(discovery, gap, {"detail": {}}, {"detail": {}}, {"detail": {}}, URL)["detail"]
    assert result["opportunity_count"] == 1
    assert result["opportunities"][0]["question_ids"] == ["Q-01", "Q-02"]


def test_opportunity_blocks_missing_answer_until_property_facts_are_approved():
    discovery = {"detail": {"discovery_confidence_score": 75, "questions": [{"id": "Q-01", "lineage_id": "AQ-pets", "question": "Are pets allowed?", "evidence_status": "observed", "source_types": ["google_related_question"]}]}}
    gap = {"detail": {"assessments": [{"question_id": "Q-01"}], "prioritized_gaps": [{"question_id": "Q-01", "status": "missing", "recommended_action": "Add the verified pet policy.", "passage": None}]}}
    result = build_aeo_opportunities(discovery, gap, {"detail": {}}, {"detail": {}}, {"detail": {}}, URL)["detail"]
    item = result["opportunities"][0]
    assert item["queue"] == "blocked"
    assert item["dependencies"] == ["Approved property facts"]
    assert item["primary_action"].startswith("Confirm the answer")


def test_inferred_questions_stay_out_of_implementation_queue():
    discovery = {"detail": {"discovery_confidence_score": 80, "questions": [{"id": "Q-01", "lineage_id": "AQ-wedding", "question": "Can the resort host weddings?", "evidence_status": "inferred", "source_types": ["planning_framework"], "priority_score": 70}]}}
    gap = {"detail": {"assessments": [], "prioritized_gaps": [{"question_id": "Q-01", "status": "missing", "passage": None}]}}
    result = build_aeo_opportunities(discovery, gap, {"detail": {}}, {"detail": {}}, {"detail": {}}, URL)["detail"]
    assert result["opportunities"] == []
    assert result["roadmap"]["research"] == ["AQ-wedding"]
    assert result["research_opportunities"][0]["queue"] == "research"
    assert result["aeo_opportunity_score"] is None


def test_opportunity_uses_reviewable_draft_without_creating_duplicate_work():
    discovery = {"detail": {"discovery_confidence_score": 80, "questions": [{"id": "Q-01", "lineage_id": "AQ-pool", "question": "Does the resort have a pool?", "evidence_status": "observed"}]}}
    gap = {"detail": {"assessments": [{"question_id": "Q-01"}], "prioritized_gaps": [{"question_id": "Q-01", "status": "partial", "recommended_action": "Complete it.", "passage": {"excerpt": "Outdoor pool."}}]}}
    optimization = {"detail": {"optimized_answers": [{"question_id": "Q-01", "status": "drafted"}]}}
    result = build_aeo_opportunities(discovery, gap, {"detail": {}}, {"detail": {}}, {"detail": {}}, URL, optimization)["detail"]
    assert result["opportunity_count"] == 1
    assert "reviewable_draft_available" in result["opportunities"][0]["issue_facets"]
    assert result["opportunities"][0]["primary_action"].startswith("Review the retained")


def test_opportunity_is_independent_and_connected_run_expands_full_evidence_chain():
    individual = DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["aeo_opportunity"])
    assert individual.selected_agents == ["aeo_opportunity"]
    connected = DiagnosisInput(page_url=URL, selected_agents=["aeo_opportunity"])
    assert connected.selected_agents == ["question_discovery", "answer_gap", "faq_intelligence", "question_intent", "answer_structure", "aeo_opportunity"]
