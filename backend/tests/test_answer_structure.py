from answer_structure.analysis import analyze_answer_structure
from diagnosis.models import DiagnosisInput


URL = "https://www.sterlingholidays.com/resorts-hotels/lake-palace-alleppey"


def _discovery():
    return {"detail": {"questions": [
        {"id": "Q-01", "lineage_id": "AQ-pool", "question": "Does the resort have a pool?"},
        {"id": "Q-02", "lineage_id": "AQ-pets", "question": "Is the resort pet-friendly?"},
    ]}}


def _gaps():
    return {"detail": {"assessments": [
        {"question_id": "Q-01", "lineage_id": "AQ-pool", "question": "Does the resort have a pool?", "status": "answered", "dimensions": {"directness": 92, "extractability": 85}, "passage": {"excerpt": "The resort has an outdoor swimming pool for registered guests.", "source_url": URL}},
        {"question_id": "Q-02", "lineage_id": "AQ-pets", "question": "Is the resort pet-friendly?", "status": "missing", "dimensions": {"directness": 0, "extractability": 0}, "passage": None},
    ], "discovery_provenance": {}}}


def test_structure_scores_retained_answers_and_excludes_missing_answers():
    capture = {"pages": [{"final_url": URL, "content_sections": [{"heading": "Pool", "text": "The resort has an outdoor swimming pool for registered guests."}]}]}
    result = analyze_answer_structure(capture, _discovery(), _gaps(), URL)["detail"]
    assert result["assessed_answer_count"] == 1
    assert result["structure_entries"][0]["question_id"] == "Q-01"
    assert result["structure_entries"][0]["heading"] == "Pool"
    assert result["answer_structure_score"] >= 85
    assert result["structure_entries"][0]["locator_method"] == "exact_normalized"
    assert result["scoring_weights"] == {"direct_opening": 25, "self_containment": 25, "heading_context": 20, "format_suitability": 15, "concision": 15}


def test_structure_uses_each_dimension_once_in_weighted_score():
    capture = {"pages": [{"final_url": URL, "content_sections": [{"heading": "Pool", "text": "The resort has an outdoor swimming pool for registered guests."}]}]}
    entry = analyze_answer_structure(capture, _discovery(), _gaps(), URL)["detail"]["structure_entries"][0]
    expected = round(sum(entry["dimensions"][key] * weight for key, weight in {"direct_opening": 25, "self_containment": 25, "heading_context": 20, "format_suitability": 15, "concision": 15}.items()) / 100)
    assert entry["structure_score"] == expected


def test_structure_withholds_score_when_passage_cannot_be_located():
    capture = {"pages": [{"final_url": URL, "content_sections": [{"heading": "Dining", "text": "Breakfast is served each morning."}]}]}
    result = analyze_answer_structure(capture, _discovery(), _gaps(), URL)["detail"]
    entry = result["structure_entries"][0]
    assert entry["structure_status"] == "unable_to_locate"
    assert entry["structure_score"] is None
    assert result["answer_structure_score"] is None
    assert result["unable_to_locate_count"] == 1
    assert result["structure_improvements"] == []
    assert [item["question_id"] for item in result["unlocated_entries"]] == ["Q-01"]


def test_structure_applies_question_specific_format_expectations():
    discovery = {"detail": {"questions": [{"id": "Q-03", "lineage_id": "AQ-amenities", "question": "What amenities does the resort offer?"}]}}
    gaps = {"detail": {"assessments": [{"question_id": "Q-03", "lineage_id": "AQ-amenities", "question": "What amenities does the resort offer?", "status": "answered", "dimensions": {"directness": 90, "extractability": 90}, "passage": {"excerpt": "The resort offers a pool, restaurant, spa and activity centre.", "source_url": URL}}]}}
    capture = {"pages": [{"final_url": URL, "content_sections": [{"heading": "Amenities", "text": "The resort offers a pool, restaurant, spa and activity centre.", "element_type": "paragraph"}]}]}
    entry = analyze_answer_structure(capture, discovery, gaps, URL)["detail"]["structure_entries"][0]
    assert entry["question_type"] == "list"
    assert entry["dimensions"]["format_suitability"] == 60
    assert "format" in entry["recommended_action"].lower() or "list" in entry["recommended_action"].lower()


def test_structure_is_independent_and_connected_runs_include_evidence_dependencies():
    individual = DiagnosisInput(page_url=URL, run_mode="individual", selected_agents=["answer_structure"])
    assert individual.selected_agents == ["answer_structure"]
    connected = DiagnosisInput(page_url=URL, selected_agents=["answer_structure"])
    assert connected.selected_agents == ["question_discovery", "answer_gap", "answer_structure"]
