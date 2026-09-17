from __future__ import annotations

from collections import defaultdict
from typing import Any


STAGE_WEIGHT = {"Book": 15, "Evaluate": 12, "Manage": 10, "Plan": 7, "Discover": 4}


def _detail(value: dict[str, Any] | None) -> dict[str, Any]:
    return (value or {}).get("detail", value or {})


def _lineage(item: dict[str, Any], questions: dict[str, dict[str, Any]]) -> str:
    question = questions.get(item.get("question_id", ""), {})
    return item.get("lineage_id") or question.get("lineage_id") or item.get("question_id", "unknown")


def build_aeo_opportunities(
    discovery: dict[str, Any], gap_result: dict[str, Any], structure_result: dict[str, Any],
    faq_result: dict[str, Any], intent_result: dict[str, Any], page_url: str,
    optimization_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one dependency-aware work item per stable observed-question lineage."""
    discovery_detail, gap_detail = _detail(discovery), _detail(gap_result)
    structure_detail, faq_detail, intent_detail = _detail(structure_result), _detail(faq_result), _detail(intent_result)
    optimization_detail = _detail(optimization_result)
    question_rows = discovery_detail.get("questions", [])
    questions = {item["id"]: item for item in question_rows}
    by_lineage: dict[str, dict[str, Any]] = {}
    for item in question_rows:
        lineage = item.get("lineage_id", item["id"])
        current = by_lineage.setdefault(lineage, {**item, "lineage_id": lineage, "question_ids": []})
        current["question_ids"].append(item["id"])
        if item.get("evidence_status") == "observed":
            current.update({**item, "lineage_id": lineage, "question_ids": current["question_ids"]})

    facets: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for item in gap_detail.get("prioritized_gaps", []): facets[_lineage(item, questions)]["answer_gap"].append(item)
    for item in structure_detail.get("structure_improvements", []): facets[_lineage(item, questions)]["answer_structure"].append(item)
    for item in faq_detail.get("faq_entries", []):
        if item.get("status") in {"not_covered", "needs_review"} and item.get("question_id"):
            facets[_lineage(item, questions)]["faq_intelligence"].append(item)
    for item in intent_detail.get("classified_questions", []): facets[_lineage(item, questions)]["question_intent"].append(item)
    for item in optimization_detail.get("optimized_answers", []): facets[_lineage(item, questions)]["answer_optimization"].append(item)

    global_confidence = int(discovery_detail.get("discovery_confidence_score") or 0)
    opportunities: list[dict[str, Any]] = []
    research: list[dict[str, Any]] = []
    for lineage, question in by_lineage.items():
        group = facets.get(lineage, {})
        gaps, structures, faqs = group.get("answer_gap", []), group.get("answer_structure", []), group.get("faq_intelligence", [])
        intents, optimized = group.get("question_intent", []), group.get("answer_optimization", [])
        if question.get("evidence_status") != "observed":
            research.append({
                "lineage_id": lineage, "question": question["question"], "queue": "research",
                "reason": "Planning hypothesis only; validate demand before approving implementation.",
                "source_types": question.get("source_types", []), "priority_score": question.get("priority_score", 0),
            })
            continue
        if not (gaps or structures or faqs):
            continue

        gap = max(gaps, key=lambda item: item.get("priority_score", 0), default=None)
        structure = min(structures, key=lambda item: item.get("structure_score") if item.get("structure_score") is not None else -1, default=None)
        faq = faqs[0] if faqs else None
        intent = intents[0] if intents else {}
        draft = optimized[0] if optimized else None
        stage = intent.get("journey_stage") or question.get("journey_stage") or "Discover"

        issue_facets: list[str] = []
        if gap: issue_facets.append("missing_answer" if gap.get("status") == "missing" else "partial_answer")
        if structure: issue_facets.append("unlocated_answer" if structure.get("structure_status") == "unable_to_locate" else "weak_answer_structure")
        if faq: issue_facets.append("faq_coverage_gap" if faq.get("status") == "not_covered" else "faq_editorial_review")
        if draft and draft.get("status") == "drafted": issue_facets.append("reviewable_draft_available")

        blocked = bool(gap and gap.get("status") == "missing" and not (gap.get("passage") or {}).get("excerpt"))
        dependencies: list[str] = []
        actions: list[str] = []
        if blocked:
            dependencies.append("Approved property facts")
            actions.append("Confirm the answer with Resort Operations before drafting page copy.")
        if gap:
            actions.append(gap.get("recommended_action") or "Create a direct answer from approved property facts.")
        if structure:
            actions.append(structure.get("recommended_action") or "Restructure the retained answer for direct extraction.")
        if faq:
            actions.append("Place the verified question and answer in the visible FAQ experience when it helps guests complete this journey stage.")
        if draft and draft.get("status") == "drafted":
            actions.insert(0, "Review the retained Answer Optimization draft against the cited passage.")

        evidence_points = 25 if global_confidence >= 70 else 18 if global_confidence >= 40 else 10
        deficiency = 25 if gap and gap.get("status") == "missing" else 18 if gap else 0
        obstruction = 15 if structure and structure.get("structure_status") in {"weak", "unable_to_locate"} else 10 if structure or faq else 0
        blocker_urgency = 10 if blocked else 6 if dependencies else 4
        effort = "high" if blocked and len(issue_facets) >= 3 else "medium" if blocked or len(issue_facets) >= 2 else "low"
        effort_fit = {"low": 10, "medium": 7, "high": 4}[effort]
        factors = {"evidence_confidence": evidence_points, "answer_deficiency": deficiency,
                   "journey_relevance": STAGE_WEIGHT.get(stage, 4), "structural_obstruction": obstruction,
                   "dependency_urgency": blocker_urgency, "effort_fit": effort_fit}
        score = min(100, sum(factors.values()))
        priority = "high" if score >= 75 else "medium" if score >= 55 else "low"
        queue = "blocked" if blocked else "now" if priority == "high" and effort != "high" else "next" if priority == "medium" or effort == "high" else "later"
        primary_action = actions[0]
        completion = (gap or {}).get("completion_check") or "A reviewer can extract one direct answer under a descriptive heading and trace every fact to the captured page."
        source_agents = [name for name in ("answer_gap", "answer_structure", "faq_intelligence", "question_intent", "answer_optimization") if group.get(name)]
        reasons = [f"Observed question from {', '.join(question.get('source_types', [])) or 'retained evidence'}", f"{stage} journey stage", *[item.replace('_', ' ') for item in issue_facets]]
        opportunities.append({
            "question_id": question["question_ids"][0], "question_ids": question["question_ids"], "lineage_id": lineage,
            "question": question["question"], "evidence_status": "observed", "assessment_confidence": global_confidence,
            "issue": ", ".join(issue_facets).replace("_", " ").title(), "issue_facets": issue_facets,
            "recommended_action": primary_action, "primary_action": primary_action, "supporting_actions": actions[1:],
            "completion_check": completion, "journey_stage": stage, "priority_score": score, "priority": priority,
            "priority_factors": factors, "queue": queue, "effort": effort,
            "owner": "Resort Operations and Content Strategy" if blocked else "Content Strategy and Web Engineering",
            "blockers": dependencies, "dependencies": dependencies, "source_agents": source_agents,
            "reason": "; ".join(reasons) + ".", "source_url": (structure or {}).get("source_url") or ((gap or {}).get("passage") or {}).get("source_url") or page_url,
            "source_excerpt": (structure or {}).get("source_excerpt") or ((gap or {}).get("passage") or {}).get("excerpt"),
        })

    queue_order = {"now": 0, "next": 1, "later": 2, "blocked": 3}
    opportunities.sort(key=lambda item: (queue_order[item["queue"]], -item["priority_score"], item["lineage_id"]))
    research.sort(key=lambda item: (-item["priority_score"], item["lineage_id"]))
    roadmap = {key: [item["lineage_id"] for item in opportunities if item["queue"] == key] for key in ("now", "next", "later", "blocked")}
    roadmap["research"] = [item["lineage_id"] for item in research]

    observed = [item for item in by_lineage.values() if item.get("evidence_status") == "observed"]
    observed_lineages = {item["lineage_id"] for item in observed}
    assessed_lineages = {_lineage(item, questions) for item in gap_detail.get("assessments", [])}
    unresolved_lineages = {item["lineage_id"] for item in opportunities}
    ready_count = len((observed_lineages & assessed_lineages) - unresolved_lineages)
    readiness = round(100 * ready_count / len(observed_lineages)) if observed_lineages and global_confidence >= 40 else None
    return {"status": "complete", "detail": {
        "aeo_opportunity_score": readiness, "assessment_confidence_score": global_confidence if observed_lineages else None,
        "opportunity_count": len(opportunities), "implementation_count": sum(item["queue"] != "blocked" for item in opportunities),
        "blocked_count": sum(item["queue"] == "blocked" for item in opportunities), "research_count": len(research),
        "high_priority_count": sum(item["priority"] == "high" for item in opportunities),
        "observed_question_count": len(observed_lineages), "assessed_question_count": len(observed_lineages & assessed_lineages),
        "ready_question_count": ready_count, "verified_faq_gap_count": sum(bool(group.get("faq_intelligence")) for group in facets.values()),
        "opportunities": opportunities, "research_opportunities": research, "roadmap": roadmap,
        "source_summary": {"answer_gap_count": sum(bool(group.get("answer_gap")) for group in facets.values()),
                           "structure_improvement_count": sum(bool(group.get("answer_structure")) for group in facets.values()),
                           "faq_gap_count": sum(bool(group.get("faq_intelligence")) for group in facets.values()),
                           "intent_classified_count": sum(bool(group.get("question_intent")) for group in facets.values()),
                           "optimized_answer_count": sum(bool(group.get("answer_optimization")) for group in facets.values())},
        "limitations": [
            "Delivery priority combines disclosed evidence, deficiency, journey, obstruction, dependency and effort factors; it is not measured traffic, revenue or conversion impact.",
            "Work is deduplicated by stable question lineage; correlated source agents enrich one opportunity and do not inflate its score.",
            "Inferred questions remain in a separate research queue and never become implementation work without observed demand evidence.",
        ], "source_url": page_url,
    }}
