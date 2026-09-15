from __future__ import annotations

import re
from typing import Any


STOP = {
    "a", "an", "and", "are", "at", "be", "can", "do", "does", "for", "how",
    "available", "have", "in", "is", "it", "of", "on", "options", "or", "resort", "the", "this", "to", "what", "where",
    "which", "who", "with", "your", "provide", "provided", "provides",
}
VAGUE = {"discover", "experience", "explore", "enjoy", "perfect", "unique", "unforgettable", "world-class"}
FACT_TERMS = {
    "address", "airport", "available", "breakfast", "check-in", "check-out", "distance",
    "hours", "includes", "located", "menu", "policy", "price", "restaurant", "room",
    "station", "timing", "wifi",
}
ALIASES = {
    "dining": "restaurant", "food": "restaurant", "meals": "restaurant",
    "accommodation": "room", "rooms": "room", "amenities": "amenity",
    "facilities": "amenity", "children": "family", "kids": "family",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _tokens(value: str) -> set[str]:
    return {ALIASES.get(token, token) for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) > 2 and token not in STOP}


def _sentences(value: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", value)
    return list(dict.fromkeys(_clean(chunk) for chunk in chunks if 5 <= len(_clean(chunk)) <= 700))


def _passages(page: dict[str, Any]) -> list[tuple[str, str]]:
    """Prefer section-sized evidence, then fall back to sentence windows.

    A single sentence routinely loses the heading, list items, or following
    sentence that makes an answer complete. Two-sentence windows retain that
    context while remaining small enough to review in the report.
    """
    passages: list[tuple[str, str]] = []
    for section in page.get("content_sections", []):
        heading = _clean(section.get("heading") if isinstance(section, dict) else "")
        text = _clean(section.get("text") if isinstance(section, dict) else "")
        if text:
            passages.append((_clean(f"{heading}. {text}") if heading else text, f"Section: {heading}" if heading else "Captured content section"))
    sentences = _sentences(page.get("main_text") or "")
    for index, sentence in enumerate(sentences):
        passages.append((sentence, "Captured sentence"))
        if index + 1 < len(sentences):
            passages.append((_clean(f"{sentence} {sentences[index + 1]}"), "Adjacent captured sentences"))
    return list(dict.fromkeys(passages))


def _identity_tokens(capture: dict[str, Any]) -> set[str]:
    identity = capture.get("identity") or {}
    return _tokens(" ".join(filter(None, [identity.get("property_name"), identity.get("branded_query"), identity.get("destination")])))


def _retrieve(question: str, capture: dict[str, Any]) -> tuple[dict[str, Any] | None, float]:
    wanted = _tokens(question) - _identity_tokens(capture)
    if not wanted:
        return None, 0.0
    best: dict[str, Any] | None = None
    best_score = 0.0
    for page in capture.get("pages", []):
        for sentence, location in _passages(page):
            tokens = _tokens(sentence) - _identity_tokens(capture)
            overlap = len(wanted & tokens) / len(wanted)
            # A question heading by itself is a locator, not an answer.
            is_question = sentence.rstrip().endswith("?")
            if is_question:
                continue
            matched = len(wanted & tokens)
            # Length must not rescue a passage that merely shares one generic
            # term (for example "airport lounge" for "free airport shuttle").
            minimum_matches = 1 if len(wanted) == 1 else 2
            if matched < minimum_matches and overlap < 0.60:
                continue
            substance = min(1.0, max(0, len(tokens) - 2) / 12)
            score = overlap * 0.90 + substance * 0.10
            if score > best_score:
                best_score = score
                best = {
                    "excerpt": sentence,
                    "source_url": page.get("final_url") or page.get("requested_url"),
                    "location": location,
                    "matched_terms": sorted(wanted & tokens),
                    "question_terms": sorted(wanted),
                    "lexical_coverage": round(overlap, 3),
                }
    return best, max(0.0, best_score)


def _assess(question: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    passage, relevance = _retrieve(question["question"], capture)
    if not any(page.get("main_text") for page in capture.get("pages", [])):
        status, reason = "unable_to_verify", "No usable page text was captured."
        directness = completeness = extractability = support = 0
    elif not passage or relevance < 0.48:
        status, reason = "missing", "No captured passage matched the subject of the observed question closely enough to assess as an answer."
        directness = completeness = extractability = support = 0
    else:
        excerpt = passage["excerpt"]
        words = re.findall(r"[a-z0-9]+", excerpt.casefold())
        qtokens = _tokens(question["question"]) - _identity_tokens(capture)
        etokens = _tokens(excerpt) - _identity_tokens(capture)
        coverage = len(qtokens & etokens) / max(1, len(qtokens))
        vague_ratio = len(etokens & VAGUE) / max(1, len(etokens))
        directness = round(min(100, relevance * 115))
        completeness = round(min(100, coverage * 70 + min(30, len(words) * 1.5)))
        extractability = 85 if 8 <= len(words) <= 80 else 60 if len(words) <= 140 else 35
        has_number = bool(re.search(r"\b\d+(?:[.:]\d+)?\b", excerpt))
        support = min(100, 20 + 15 * len(etokens & FACT_TERMS) + (15 if has_number else 0))
        if len(words) < 7 or vague_ratio > 0.28 or completeness < 65 or coverage < 0.60:
            status = "partial"
            reason = "A related passage was captured, but it does not provide a sufficiently direct and complete answer."
        else:
            status = "answered"
            reason = "A concise, relevant passage addresses the observed question in the captured content."
    quality = round((directness + completeness + extractability + support) / 4)
    return {
        "question_id": question["id"], "lineage_id": question.get("lineage_id", question["id"]), "question": question["question"],
        "topic": question.get("topic"), "intent": question.get("intent"),
        "question_source_types": question.get("source_types", []),
        "evidence_status": question.get("evidence_status"), "status": status,
        "reason": reason, "answer_quality_score": quality,
        "dimensions": {
            "directness": directness, "completeness": completeness,
            "extractability": extractability, "factual_support": support,
        },
        "passage": passage,
    }


def analyze_answer_gaps(capture: dict[str, Any], discovery: dict[str, Any], page_url: str) -> dict[str, Any]:
    """Validate answers for observed questions without turning inferred demand into findings."""
    discovery_detail = discovery.get("detail", discovery)
    questions = discovery_detail.get("questions", [])
    observed = [item for item in questions if item.get("evidence_status") == "observed"]
    assessments = [_assess(item, capture) for item in observed]
    assessable = [item for item in assessments if item["status"] != "unable_to_verify"]
    coverage_values = {"answered": 100, "partial": 50, "missing": 0}
    readiness = round(sum(coverage_values[item["status"]] for item in assessable) / len(assessable)) if assessable else None
    source_types = {s for item in observed for s in item.get("source_types", [])}
    # Confidence reflects source diversity and reviewable passages. More rows
    # from one source do not by themselves create near-certain evidence.
    passage_ratio = sum(bool(item.get("passage")) for item in assessments) / len(assessments) if assessments else 0
    confidence = min(90, round(20 + len(source_types) * 18 + passage_ratio * 30)) if assessments else 0
    gaps = [item for item in assessments if item["status"] in {"partial", "missing"}]
    priorities = []
    for item in gaps:
        source = next((question for question in observed if question["id"] == item["question_id"]), {})
        status_weight = 55 if item["status"] == "missing" else 35
        priority_score = min(100, status_weight + round(source.get("priority_score", 0) * 0.35))
        priorities.append({
            **item, "priority_score": priority_score,
            "priority": "high" if priority_score >= 75 else "medium" if priority_score >= 55 else "low",
            "recommended_action": (
                "Add a direct, fact-checked answer for this observed question in the most relevant page section."
                if item["status"] == "missing" else
                "Expand the retained passage so it answers the observed question directly and completely using approved property facts."
            ),
            "completion_check": "A reviewer can locate one concise passage that answers the question, verify every property fact, and extract it without surrounding promotional copy.",
        })
    priorities.sort(key=lambda item: (-item["priority_score"], item["question_id"]))
    return {
        "status": "complete",
        "detail": {
            "answer_readiness_score": readiness,
            "assessment_confidence_score": confidence,
            "question_count": len(observed),
            "answered_count": sum(item["status"] == "answered" for item in assessments),
            "partial_count": sum(item["status"] == "partial" for item in assessments),
            "missing_count": sum(item["status"] == "missing" for item in assessments),
            "unable_to_verify_count": sum(item["status"] == "unable_to_verify" for item in assessments),
            "assessments": assessments,
            "prioritized_gaps": priorities,
            "discovery_provenance": {
                "observed_question_ids": [item["id"] for item in observed],
                "inferred_questions_excluded": sum(item.get("evidence_status") == "inferred" for item in questions),
                "discovery_confidence_score": discovery_detail.get("discovery_confidence_score"),
                "source_ledger": discovery_detail.get("source_ledger", []),
            },
            "recommended_agent_handoffs": ([{
                "target_agent": "answer_optimization", "target_label": "Answer Optimization Agent",
                "question_ids": [item["question_id"] for item in priorities],
                "title": "Prepare evidence-bound answer improvements",
                "reason": "Answer Gap verified these observed questions as missing or incomplete; drafting must use approved property facts and preserve their evidence links.",
            }] if priorities else []),
            "limitations": [
                "Only observed questions were scored; inferred discovery hypotheses remain excluded until separately approved or demand-validated.",
                "Assessment uses captured server HTML and deterministic passage matching; rendered, interactive or image-only answers may require manual verification.",
                "An answered classification measures the captured passage, not live search prominence or inclusion in an AI-generated answer.",
                "This agent identifies missing information and does not generate replacement copy.",
            ],
            "source_url": page_url,
        },
    }
