from __future__ import annotations

import re
import hashlib
from collections import Counter
from typing import Any
from urllib.parse import quote_plus


QUESTION_WORDS = ("who", "what", "when", "where", "why", "how", "which", "is", "are", "can", "does", "do")
STOP = {"a", "an", "and", "are", "at", "be", "can", "do", "does", "for", "how", "in", "is", "of", "on", "or", "the", "to", "what", "where", "which", "with"}
CANONICAL_TERMS = {
    "accommodation": "room", "accommodations": "room", "rooms": "room",
    "facilities": "amenity", "amenities": "amenity",
    "restaurants": "dining", "restaurant": "dining", "food": "dining",
    "kids": "children", "child": "children",
    "rates": "price", "cost": "price", "pricing": "price",
}


def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip(" -|\u2013\u2014")


def _normalize(question: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", question.casefold()))


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) > 2 and token not in STOP}


def _meaning_tokens(value: str, identity_tokens: set[str]) -> set[str]:
    """Return subject tokens suitable for conservative semantic deduplication."""
    tokens = _tokens(value) - identity_tokens
    return {CANONICAL_TERMS.get(token, token) for token in tokens if token not in {"available", "offer", "offers", "guest", "guests", "resort"}}


def _same_question(left: dict[str, Any], right: dict[str, Any], identity_tokens: set[str]) -> bool:
    left_tokens = _meaning_tokens(left["question"], identity_tokens)
    right_tokens = _meaning_tokens(right["question"], identity_tokens)
    if not left_tokens or not right_tokens:
        return _normalize(left["question"]) == _normalize(right["question"])
    overlap = len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
    return overlap >= 0.72 or (left_tokens == right_tokens)


def _intent(question: str) -> tuple[str, str, str]:
    text = question.casefold()
    if any(term in text for term in ("price", "cost", "rate", "deal", "offer", "book", "cancel")):
        return "transaction", "Book", "Commercial"
    if any(term in text for term in ("compare", "better", "best", "review", "worth", "family", "couple", "children")):
        return "evaluation", "Compare", "Commercial"
    if any(term in text for term in ("where", "reach", "distance", "near", "airport", "station", "check-in", "check out")):
        return "planning", "Plan", "Practical"
    if any(term in text for term in ("food", "restaurant", "dining", "breakfast")):
        return "property details", "Evaluate", "Dining"
    if any(term in text for term in ("room", "accommodation")):
        return "property details", "Evaluate", "Rooms"
    if any(term in text for term in ("amenit", "pool", "wifi", "pet", "accessib")):
        return "property details", "Evaluate", "Amenities"
    return "discovery", "Discover", "General"


def _coverage(question: str, page_text: str, headings: list[str], identity_tokens: set[str]) -> tuple[str, str]:
    # Property-name overlap says nothing about whether the page answers the
    # question. Score the subject terms (pool, cancellation, dining, etc.).
    wanted = _tokens(question) - identity_tokens
    if not wanted:
        return "unknown", "The question contains too little subject detail for a reliable text match."
    heading_tokens = [_tokens(item) for item in headings]
    if any(len(wanted & tokens) >= max(1, min(3, len(wanted) - 1)) for tokens in heading_tokens):
        return "explicit", "A captured heading directly signals this topic."
    present = wanted & _tokens(page_text)
    ratio = len(present) / len(wanted)
    if ratio >= 0.65:
        return "implicit", "The topic terms appear in captured copy, but no direct question heading was observed."
    return "absent", "The captured page sample did not contain enough matching topic terms to establish an answer."


def _templates(identity: dict[str, Any], language: str = "en") -> list[tuple[str, str]]:
    if language.casefold() != "en":
        return []
    name = identity.get("branded_query") or identity.get("property_name") or "this resort"
    destination = identity.get("destination")
    values = [
        (f"Where is {name} located?", "location"),
        (f"What room and accommodation options does {name} offer?", "rooms"),
        (f"What amenities are available at {name}?", "amenities"),
        (f"Is {name} suitable for families with children?", "audience fit"),
        (f"What dining options are available at {name}?", "dining"),
        (f"What are the check-in and check-out times at {name}?", "arrival"),
        (f"How do guests reach {name}?", "transport"),
        (f"What is the cancellation policy for {name}?", "booking policy"),
        (f"What accessibility information is available for {name}?", "accessibility"),
        (f"Is {name} pet-friendly?", "pets"),
    ]
    if destination:
        values.append((f"What can guests do near {name} in {destination}?", "nearby experiences"))
    return values


def discover_questions(capture: dict[str, Any], page_url: str, research: Any | None = None, language: str = "en") -> dict[str, Any]:
    """Build a question inventory while preserving observed versus inferred provenance."""
    identity = capture.get("identity") or {}
    pages = capture.get("pages", [])
    primary = pages[0] if pages else {}
    page_text = "\n".join(str(page.get("main_text") or "") for page in pages)
    headings = [
        _clean(heading.get("text") if isinstance(heading, dict) else heading)
        for page in pages for heading in page.get("headings", [])
    ]
    headings.extend(_clean(item) for page in pages for item in [*page.get("h1", []), *page.get("h2", [])])

    candidates: list[dict[str, Any]] = []
    search_url = "https://www.google.com/search?q=" + quote_plus(identity.get("branded_query") or identity.get("property_name") or page_url)
    research_questions = list(getattr(research, "questions", []) or []) if research else []
    related_searches = list(getattr(research, "related_searches", []) or []) if research else []
    observed_at = getattr(research, "observed_at", None) if research else None
    research_queries = list(getattr(research, "queries", []) or []) if research else []
    question_queries = dict(getattr(research, "question_queries", {}) or {}) if research else {}
    if research_questions:
        for item in research_questions:
            cleaned = _clean(item.question)
            candidates.append({"question": cleaned, "source_type": "people_also_ask", "source_url": item.source_url or search_url, "source_queries": question_queries.get(_normalize(cleaned), []), "evidence_status": "observed", "confidence": "high"})
    for related in related_searches:
        value = _clean(related)
        if value and (value.endswith("?") or value.casefold().startswith(QUESTION_WORDS)):
            candidates.append({"question": value if value.endswith("?") else value + "?", "source_type": "related_search", "source_url": search_url, "evidence_status": "observed", "confidence": "medium"})
    for heading in headings:
        lowered = heading.casefold()
        if heading.endswith("?") or lowered.startswith(QUESTION_WORDS):
            candidates.append({"question": heading if heading.endswith("?") else heading + "?", "source_type": "page_heading", "source_url": primary.get("final_url") or page_url, "evidence_status": "observed", "confidence": "high"})
    for question, topic in _templates(identity, language):
        candidates.append({"question": question, "source_type": "resort_question_framework", "source_url": page_url, "evidence_status": "inferred", "confidence": "medium", "topic": topic})

    merged: list[dict[str, Any]] = []
    identity_tokens = _tokens(" ".join(filter(None, [identity.get("branded_query"), identity.get("property_name"), identity.get("destination")])))
    for candidate in candidates:
        question = _clean(candidate["question"])
        if not question:
            continue
        current = next((item for item in merged if _same_question(item, {"question": question}, identity_tokens)), None)
        if current:
            current["source_types"] = list(dict.fromkeys([*current["source_types"], candidate["source_type"]]))
            current["source_urls"] = list(dict.fromkeys([*current["source_urls"], candidate["source_url"]]))
            current["source_queries"] = list(dict.fromkeys([*current.get("source_queries", []), *candidate.get("source_queries", [])]))
            if question != current["question"] and question not in current["variants"]:
                current["variants"].append(question)
            if candidate["evidence_status"] == "observed":
                current["evidence_status"], current["confidence"] = "observed", "high"
                # Prefer the wording that was actually observed over a framework template.
                if current.get("representative_source") == "resort_question_framework":
                    current["question"] = question
                    current["representative_source"] = candidate["source_type"]
            continue
        intent, journey, default_topic = _intent(question)
        coverage, basis = _coverage(question, page_text, headings, identity_tokens)
        observed = candidate["evidence_status"] == "observed"
        # An inferred candidate is a research hypothesis. Page absence cannot
        # make it a stronger implementation opportunity before demand is observed.
        score = (38 if observed else 18) + ({"absent": 20, "implicit": 12, "explicit": 5, "unknown": 8}[coverage] if observed else 0)
        score += {"transaction": 12, "evaluation": 10, "planning": 8, "property details": 7, "discovery": 5}[intent]
        merged.append({
            "question": question,
            # Template topics are lowercase and intent-derived topics are
            # capitalized; without one casing the same topic produced two
            # separate clusters with the same displayed label.
            "topic": (candidate.get("topic") or default_topic).strip().title(), "intent": intent, "journey_stage": journey,
            "page_coverage": coverage, "coverage_basis": basis,
            "coverage_role": "triage_hint" if observed else "hypothesis_preview",
            "evidence_status": candidate["evidence_status"], "confidence": candidate["confidence"],
            "source_types": [candidate["source_type"]], "source_urls": [candidate["source_url"]],
            "source_queries": candidate.get("source_queries", []),
            "representative_source": candidate["source_type"], "variants": [],
            "priority_score": min(100, score),
            "handoffs": {
                "seo": f"Validate '{question}' as a search theme before assigning a page role.",
                "aeo": "Assess answer completeness and add a direct answer only when approved property facts support it.",
                "geo": "Use this as a prompt seed for a separately measured AI-visibility test; do not treat it as observed AI demand.",
            },
        })
    questions = sorted(merged, key=lambda item: (item["evidence_status"] != "observed", -item["priority_score"], item["question"]))
    # Keep a human-readable rank ID while lineage_id remains stable when a
    # later run inserts or reorders questions.
    for position, item in enumerate(questions, 1):
        item["id"] = f"Q-{position:02d}"
        item["lineage_id"] = "AQ-" + hashlib.sha256(_normalize(item["question"]).encode()).hexdigest()[:10]
    observed_questions = [item for item in questions if item["evidence_status"] == "observed"]
    observed_assessed = [item for item in observed_questions if item["page_coverage"] != "unknown"]
    observed_earned = sum({"explicit": 100, "implicit": 55, "absent": 0}[item["page_coverage"]] for item in observed_assessed)
    coverage_score = round(observed_earned / len(observed_assessed)) if observed_assessed else None
    inferred_assessed = [item for item in questions if item["evidence_status"] == "inferred" and item["page_coverage"] != "unknown"]
    inferred_earned = sum({"explicit": 100, "implicit": 55, "absent": 0}[item["page_coverage"]] for item in inferred_assessed)
    hypothesis_preview = round(inferred_earned / len(inferred_assessed)) if inferred_assessed else None
    observed_count = sum(item["evidence_status"] == "observed" for item in questions)
    observed_source_types = sorted({source for item in observed_questions for source in item["source_types"]})
    # Additional rows from one search feature add breadth, not certainty.
    # Cap deterministic confidence below 90 until an independently measured
    # first-party source (for example Search Console or support logs) exists.
    confidence_score = min(88, 20 + min(observed_count, 6) * 6 + len(observed_source_types) * 12 + min(len(research_queries), 4) * 4)
    evidence_status = "verified" if len(observed_source_types) >= 2 and observed_count >= 3 else "partial" if observed_count else "insufficient"
    clusters = Counter(item["topic"] for item in questions)  # topics are already normalized above
    return {
        "status": "complete",
        "detail": {
            "target_keyword": identity.get("branded_query") or identity.get("property_name"),
            "question_coverage_score": coverage_score,
            "observed_coverage_score": coverage_score,
            "hypothesis_coverage_preview": hypothesis_preview,
            "discovery_confidence_score": confidence_score,
            "evidence_quality": {"status": evidence_status, "score": confidence_score, "observed_source_types": observed_source_types, "observed_question_count": observed_count},
            "source_ledger": [
                {"source_type": "page_heading", "status": "captured", "query": page_url, "observed_count": sum("page_heading" in item["source_types"] for item in observed_questions), "observed_at": None},
                {"source_type": "people_also_ask", "status": "captured" if research_questions else "unavailable", "query": " | ".join(research_queries) or identity.get("branded_query") or identity.get("property_name") or page_url, "observed_count": len(research_questions), "observed_at": observed_at},
                {"source_type": "related_search", "status": "captured" if related_searches else "unavailable", "query": identity.get("branded_query") or identity.get("property_name") or page_url, "observed_count": sum("related_search" in item["source_types"] for item in observed_questions), "observed_at": observed_at},
                {"source_type": "resort_question_framework", "status": "planning_only", "query": None, "observed_count": 0, "observed_at": None},
            ],
            "questions": questions,
            "clusters": [{"label": label.title(), "question_count": count} for label, count in clusters.most_common()],
            "observed_question_count": observed_count,
            "inferred_question_count": len(questions) - observed_count,
            "explicit_answer_count": sum(item["page_coverage"] == "explicit" for item in observed_questions),
            "unanswered_count": sum(item["page_coverage"] == "absent" for item in observed_questions),
            "answer_gap_candidate_ids": [item["id"] for item in observed_questions if item["page_coverage"] in {"absent", "implicit", "unknown"}],
            "recommended_agent_handoffs": ([{
                "target_agent": "answer_gap", "target_label": "Answer Gap Agent", "question_ids": [item["id"] for item in observed_questions],
                "title": "Validate observed questions for answer completeness",
                "reason": "Question Discovery identifies demand and a coverage hint; Answer Gap must verify factual completeness before content changes are recommended.",
            }] if observed_questions else []),
            "limitations": [
                "Observed questions come from captured page headings and the available Google question sample; inferred questions are planning hypotheses, not measured demand.",
                "Coverage is a text-evidence check. The Answer Gap Agent should separately assess factual completeness and answer quality.",
            "AI prompt demand and live assistant visibility were not measured; GEO handoffs are prompt seeds only.",
            *( ["The fixed resort-question framework is currently English-only, so it was omitted for this language rather than mistranslated."] if language.casefold() != "en" else [] ),
            ],
        },
    }
