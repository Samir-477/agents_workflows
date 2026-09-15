from __future__ import annotations

import re
from typing import Any

# The fixed audit taxonomy. Reuses question_discovery's own template
# vocabulary rather than inventing a parallel one, plus "Pets" — named
# explicitly in the product brief's own FAQ example but not yet a discovery
# template. "Nearby Experiences" is deliberately excluded: question_discovery
# only generates that template when a destination was resolved, so treating
# it as a fixed, always-required category would read as incomplete for a
# resort whose destination could not be identified, which is a discovery
# limitation, not an FAQ gap.
FAQ_CATEGORIES = [
    "Location", "Rooms", "Amenities", "Pets", "Dining",
    "Arrival", "Transport", "Booking Policy", "Accessibility", "Audience Fit",
]

# Ordered so a question that touches more than one topic ("pet-friendly
# rooms") resolves to its most specific category before a broader one.
def _word(term: str) -> str:
    """A whole-word regex. A bare substring check is what let 'rate' match
    inside 'corporate' and 'spa' match inside 'spacious' on a real captured
    page — both found by testing against real Sterling copy, not invented."""
    return r"\b" + re.escape(term) + r"\b"


def _prefix(term: str) -> str:
    """A start-anchored stem for words this taxonomy wants every inflection
    of (amenity/amenities, family/families, accessibility/accessibilities),
    without also matching an unrelated word that merely starts the same way."""
    return r"\b" + re.escape(term)


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Pets": (_word("pet"), _word("pets"), _word("dog"), _word("dogs"), _word("cat"), _word("cats")),
    # A bare "accessib" matches "accessible" (reachable) as readily as
    # "accessibility" (disability access) — the longer stem excludes the
    # former since "accessible" is shorter than "accessibil" itself.
    "Accessibility": (_prefix("accessibil"), _word("wheelchair"), _prefix("disab"), "mobility impair"),
    "Dining": (_prefix("dining"), _prefix("restaurant"), _prefix("breakfast"), _prefix("cuisine"), _prefix("meal")),
    "Arrival": ("check-in", "check in", "check-out", "check out", _prefix("arrival"), _prefix("timing")),
    "Transport": (_prefix("reach"), _prefix("distance"), _prefix("airport"), _prefix("station"), _prefix("transport"), _prefix("shuttle"), _prefix("pickup"), _prefix("parking")),
    "Booking Policy": (_prefix("cancel"), _prefix("refund"), _prefix("booking"), _prefix("book"), _prefix("price"), _word("rate"), _prefix("payment"), _prefix("deposit")),
    "Audience Fit": (_prefix("famil"), _prefix("child"), _prefix("kids"), _prefix("couple"), _prefix("honeymoon"), _prefix("suitable")),
    "Rooms": (_prefix("room"), _prefix("accommodation"), _prefix("suite"), _prefix("cottage"), _prefix("villa")),
    "Amenities": (_prefix("amenit"), _prefix("pool"), _word("spa"), _prefix("gym"), _prefix("facilit"), _prefix("wifi"), _prefix("activit")),
    "Location": (_prefix("located"), _prefix("location"), _prefix("address"), "where is"),
}

_STATUS_RANK = {"covered": 3, "needs_editorial_review": 2, "not_covered": 1, "not_assessed": 0}


def _classify(question: str) -> str | None:
    text = question.casefold()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(re.search(term, text) for term in keywords):
            return category
    return None


def _candidate_from_optimized(question: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any] | None:
    if optimized.get("status") == "drafted":
        return {
            # A generated draft is reviewable, never publication-approved.
            "status": "needs_editorial_review", "answer": optimized["draft_answer"],
            "source_url": optimized.get("source_url"), "evidence_source": "answer_optimization",
            "question": question["question"], "question_id": question["id"], "lineage_id": question.get("lineage_id", question["id"]),
        }
    if optimized.get("status") == "fallback_extractive":
        return {
            "status": "needs_editorial_review", "answer": optimized["draft_answer"],
            "source_url": optimized.get("source_url"), "evidence_source": "answer_optimization",
            "question": question["question"], "question_id": question["id"], "lineage_id": question.get("lineage_id", question["id"]),
        }
    return None


def _candidate_from_assessment(question: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any] | None:
    passage = assessment.get("passage") or {}
    if assessment.get("status") == "answered":
        return {
            "status": "covered", "answer": passage.get("excerpt"),
            "source_url": passage.get("source_url"), "evidence_source": "answer_gap",
            "question": question["question"], "question_id": question["id"], "lineage_id": question.get("lineage_id", question["id"]),
        }
    if assessment.get("status") == "partial":
        return {
            "status": "needs_editorial_review", "answer": passage.get("excerpt"),
            "source_url": passage.get("source_url"), "evidence_source": "answer_gap",
            "question": question["question"], "question_id": question["id"], "lineage_id": question.get("lineage_id", question["id"]),
        }
    if assessment.get("status") == "missing":
        return {
            "status": "not_covered", "answer": None, "source_url": None,
            "evidence_source": "answer_gap", "question": question["question"], "question_id": question["id"], "lineage_id": question.get("lineage_id", question["id"]),
        }
    return None


def _audit_category(category: str, questions: list[dict[str, Any]], assessments_by_id: dict[str, dict], optimized_by_id: dict[str, dict]) -> dict[str, Any]:
    observed = [item for item in questions if item.get("evidence_status") == "observed"]
    candidates = []
    for question in observed:
        optimized = optimized_by_id.get(question["id"])
        assessment = assessments_by_id.get(question["id"])
        # An Answer Optimization draft is preferred when it exists: it is a
        # word-checked, grounded rewrite, not just the raw retained passage.
        candidate = (_candidate_from_optimized(question, optimized) if optimized else None) or (_candidate_from_assessment(question, assessment) if assessment else None)
        if candidate:
            candidates.append(candidate)
    if candidates:
        # A category is only as complete as its least-covered observed
        # question. Selecting the best row concealed genuine gaps whenever a
        # second question in the same category was answered.
        best = min(candidates, key=lambda item: _STATUS_RANK[item["status"]])
        reason = {
            "covered": "Every observed question assessed in this category has a retained answer passage.",
            "needs_editorial_review": "Related content was captured, but it is not yet a complete, direct answer.",
            "not_covered": "An observed guest question in this category was checked against the captured page and no answer was found.",
        }[best["status"]]
    else:
        # No observed question ever reached this category — only an inferred
        # planning hypothesis exists, if that. This is a weaker signal than a
        # verified gap: it means demand was never confirmed, not that a known
        # question goes unanswered.
        inferred = next((item for item in questions if item.get("evidence_status") == "inferred"), None)
        best = {
            "status": "not_assessed", "answer": None, "source_url": None, "evidence_source": None,
            "question": inferred["question"] if inferred else f"What should guests know about {category.lower()}?",
            "question_id": None, "lineage_id": None,
        }
        reason = "No observed guest question surfaced in this category; only an unverified planning hypothesis exists."
    content_gap_action = None
    if best["status"] in {"needs_editorial_review", "not_covered"}:
        content_gap_action = (
            f"Confirm the {category.lower()} facts with the property team, then add one direct sentence "
            f"answering ‘{best['question']}’ using the confirmed facts."
        )
    unresolved = [item["question"] for item in candidates if item["status"] != "covered"]
    return {
        "category": category, "reason": reason, "content_gap_action": content_gap_action,
        "observed_question_count": len(observed), "unresolved_questions": unresolved, **best,
    }


def audit_faq_coverage(discovery: dict[str, Any], gap_result: dict[str, Any], optimization_result: dict[str, Any] | None, page_url: str) -> dict[str, Any]:
    """Roll observed-question evidence up into a fixed FAQ-category coverage matrix.

    Question Discovery, Answer Gap and Answer Optimization each work at the
    level of one question. This agent answers a different question: across
    the standard set of things every resort guest asks about, which
    categories does this page actually cover? A category is never marked
    covered from an inferred (unobserved) question alone, and no answer text
    is ever written here — every entry traces to a passage or draft another
    agent already retained and validated.
    """
    discovery_detail = discovery.get("detail", discovery)
    questions = discovery_detail.get("questions", [])
    gap_detail = (gap_result or {}).get("detail", gap_result or {})
    assessments_by_id = {item["question_id"]: item for item in gap_detail.get("assessments", [])}
    optimization_detail = (optimization_result or {}).get("detail", {}) if optimization_result else {}
    optimized_by_id = {item["question_id"]: item for item in optimization_detail.get("optimized_answers", [])}

    by_category: dict[str, list[dict[str, Any]]] = {category: [] for category in FAQ_CATEGORIES}
    for question in questions:
        category = _classify(question["question"])
        if category in by_category:
            by_category[category].append(question)

    entries = [_audit_category(category, by_category[category], assessments_by_id, optimized_by_id) for category in FAQ_CATEGORIES]
    ready_count = sum(item["status"] == "covered" for item in entries)
    review_count = sum(item["status"] == "needs_editorial_review" for item in entries)
    not_covered_count = sum(item["status"] == "not_covered" and item["question_id"] is not None for item in entries)
    no_question_count = sum(item["status"] == "not_assessed" for item in entries)
    assessed_categories = [item for item in entries if item["status"] != "not_assessed"]
    faq_coverage_score = round(100 * ready_count / len(assessed_categories)) if assessed_categories else None

    limitations = [
        "A category is marked covered only from an observed question with a retained, checked passage or a "
        "validated draft; an inferred planning hypothesis alone never counts as coverage.",
        "This audit does not write new FAQ copy. A category needing content receives a fact-gathering action, "
        "the same as an Answer Gap or Answer Optimization content gap.",
        "The ten categories are a fixed hospitality baseline, not a measurement of this specific resort's actual "
        "customer questions; a category with no observed demand may genuinely not matter for this property.",
    ]
    if not optimization_result:
        limitations.append(
            "This run did not include a completed Answer Optimization result. Category answers reflect only "
            "Answer Gap's retained passages, not a word-checked direct-answer draft."
        )

    return {
        "status": "complete",
        "detail": {
            "faq_coverage_score": faq_coverage_score,
            "assessed_category_count": len(assessed_categories),
            "category_count": len(FAQ_CATEGORIES),
            "ready_count": ready_count,
            "needs_review_count": review_count,
            "not_covered_count": not_covered_count,
            "no_question_count": no_question_count,
            "faq_entries": entries,
            "used_answer_optimization": bool(optimization_result),
            "upstream_provenance": gap_detail.get("discovery_provenance", {}),
            "limitations": limitations,
            "source_url": page_url,
        },
    }
