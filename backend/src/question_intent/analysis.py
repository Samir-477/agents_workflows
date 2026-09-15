from __future__ import annotations

import re
from typing import Any


JOURNEY_STAGES = ["Discover", "Evaluate", "Plan", "Book", "Manage"]
# Backward-compatible export name; values now represent actual journey stages.
INTENT_STAGES = JOURNEY_STAGES
STAGE_WEIGHT = {"Book": 40, "Evaluate": 30, "Plan": 18, "Manage": 14, "Discover": 8}
HIGH_VALUE_STAGES = {"Book", "Evaluate", "Manage"}

CONTENT_STRATEGY = {
    "Book": ("answer_optimization", "Answer Optimization Agent", "Resolve a verified booking question with a concise, fact-checked answer close to the booking path."),
    "Evaluate": ("content_brief", "Content Brief Agent", "Support evaluation with a fuller evidence-backed section rather than an unsupported comparison claim."),
    "Plan": ("local_seo", "Local SEO Agent", "Confirm property and destination logistics before publishing planning guidance."),
    "Manage": ("answer_optimization", "Answer Optimization Agent", "Make approved policy and stay-management information direct and easy to locate."),
    "Discover": ("content_brief", "Content Brief Agent", "Use validated early-stage questions to plan a useful explanatory section."),
}


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _classify_question(question: str) -> tuple[str, str, str]:
    """Return journey stage, query intent and topic as separate dimensions."""
    text = question.casefold()
    if _has(text, r"\b(cancel|refund|modify|change booking|check[- ]?out|late checkout)"):
        return "Manage", "Transactional", "Policies and stay management"
    if _has(text, r"\b(book|booking|price|pricing|cost|rates?|deal|offer|discount|availability|available dates?)\b"):
        return "Book", "Transactional", "Booking and price"
    if _has(text, r"\b(compare|comparison|versus|vs\.?|better|best|worth|reviews?|alternative|competitor)"):
        return "Evaluate", "Commercial investigation", "Comparison"
    if _has(text, r"\b(famil\w*|children|kids|couple|honeymoon|suitable|accessibility|wheelchair)"):
        return "Evaluate", "Commercial investigation", "Suitability"
    if _has(text, r"\b(distance|nearby|airport|station|reach|transport|shuttle|parking|located|location|address|weather|season|itinerary|things to do|attraction|check[- ]?in)"):
        return "Plan", "Informational", "Trip planning"
    return "Discover", "Informational", "Property discovery"


def _classify_intent(question: str) -> str:
    """Compatibility helper for callers that need the query intent only."""
    return _classify_question(question)[1]


def classify_intent(discovery: dict[str, Any], gap_result: dict[str, Any] | None, page_url: str) -> dict[str, Any]:
    discovery_detail = discovery.get("detail", discovery)
    questions = discovery_detail.get("questions", [])
    gap_detail = (gap_result or {}).get("detail", {}) if gap_result else {}
    assessments_by_id = {item["question_id"]: item for item in gap_detail.get("assessments", [])}
    classified = []
    for question in questions:
        stage, intent, topic = _classify_question(question["question"])
        assessment = assessments_by_id.get(question["id"])
        classified.append({
            "question_id": question["id"], "lineage_id": question.get("lineage_id", question["id"]),
            "question": question["question"], "evidence_status": question["evidence_status"],
            "journey_stage": stage, "intent": intent, "topic": topic,
            "priority_score": question.get("priority_score", 0), "gap_status": assessment.get("status") if assessment else None,
        })

    observed = [item for item in classified if item["evidence_status"] == "observed"]
    distribution = []
    for stage in JOURNEY_STAGES:
        measured = [item for item in observed if item["journey_stage"] == stage]
        hypotheses = [item for item in classified if item["evidence_status"] != "observed" and item["journey_stage"] == stage]
        distribution.append({"intent": stage, "count": len(measured), "observed_count": len(measured),
                             "hypothesis_count": len(hypotheses), "share": round(100 * len(measured) / len(observed)) if observed else 0})

    reprioritized_gaps = []
    if gap_result is not None:
        for item in observed:
            if item["gap_status"] not in {"partial", "missing"}:
                continue
            status_weight = 50 if item["gap_status"] == "missing" else 30
            weighted_score = min(100, status_weight + STAGE_WEIGHT[item["journey_stage"]] + round(item["priority_score"] * 0.12))
            reprioritized_gaps.append({**item, "weighted_priority_score": weighted_score,
                "priority": "high" if weighted_score >= 75 else "medium" if weighted_score >= 55 else "low",
                "reason": f"Answer Gap marked this observed {item['journey_stage'].lower()}-stage question {item['gap_status']}; the stage changes delivery order, not the evidence verdict."})
        reprioritized_gaps.sort(key=lambda item: (-item["weighted_priority_score"], item["question_id"]))

    high_value = [item for item in observed if item["journey_stage"] in HIGH_VALUE_STAGES and item["gap_status"] in {"answered", "partial", "missing"}]
    values = {"answered": 100, "partial": 50, "missing": 0}
    readiness = round(sum(values[item["gap_status"]] for item in high_value) / len(high_value)) if high_value else None
    strategy = [{"intent": stage, "recommended_agent": CONTENT_STRATEGY[stage][0], "recommended_agent_label": CONTENT_STRATEGY[stage][1],
                 "reason": CONTENT_STRATEGY[stage][2], "question_count": next(row["count"] for row in distribution if row["intent"] == stage)}
                for stage in JOURNEY_STAGES if next(row["count"] for row in distribution if row["intent"] == stage)]
    limitations = [
        "The journey distribution uses observed questions only; inferred framework questions are shown separately and do not represent measured demand.",
        "Journey stage, query intent and topic are separate fields. Classification remains a deterministic heuristic and requires review for ambiguous questions.",
        "Priority is a delivery aid based on stage and Answer Gap evidence. It is not measured conversion or revenue impact.",
    ]
    if gap_result is None:
        limitations.append("Answer Gap was unavailable, so classification is retained but no gap was reprioritized.")
    return {"status": "complete", "detail": {
        "high_value_readiness_score": readiness, "question_count": len(classified), "observed_question_count": len(observed),
        "hypothesis_question_count": len(classified) - len(observed),
        "high_value_question_count": sum(item["journey_stage"] in HIGH_VALUE_STAGES for item in observed),
        "reprioritized_gap_count": len(reprioritized_gaps), "distribution": distribution, "classified_questions": classified,
        "reprioritized_gaps": reprioritized_gaps, "content_strategy": strategy, "used_answer_gap": gap_result is not None,
        "upstream_provenance": gap_detail.get("discovery_provenance", {}),
        "limitations": limitations, "source_url": page_url,
    }}
