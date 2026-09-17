from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


STOP = {"a", "an", "and", "are", "at", "be", "can", "do", "does", "for", "has", "have", "how", "in", "is", "it", "of", "on", "or", "resort", "the", "this", "to", "what", "where", "which", "who", "with"}
WEIGHTS = {"direct_opening": 25, "self_containment": 25, "heading_context": 20, "format_suitability": 15, "concision": 15}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normal(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", _clean(value).casefold()))


def _tokens(value: Any) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", _clean(value).casefold()) if len(token) > 2 and token not in STOP}


def _question_type(question: str) -> str:
    text = question.casefold()
    if re.match(r"^(is|are|can|does|do|has|have|will|would)\b", text):
        return "yes_no"
    if re.search(r"\b(price|cost|rate|time|distance|how far|how much|how long|when)\b", text):
        return "value"
    if re.search(r"\b(policy|cancel|refund|check[- ]?in|check[- ]?out|rule|allowed)\b", text):
        return "policy"
    if re.match(r"^how (?:do|does|can|to)\b", text):
        return "steps"
    if re.search(r"\b(compare|versus|vs\.?|difference|better)\b", text):
        return "comparison"
    if re.search(r"\b(amenit|facilit|option|include|offer|activities|things to do)\b", text):
        return "list"
    if re.match(r"^(what is|what are|who is|define)\b", text):
        return "definition"
    if re.search(r"\b(where|located|location|address|reach)\b", text):
        return "location"
    return "explanation"


def _locate(capture: dict[str, Any], excerpt: str) -> dict[str, Any] | None:
    needle = _normal(excerpt)
    if not needle:
        return None
    needle_tokens = _tokens(excerpt)
    best: tuple[float, dict[str, Any]] | None = None
    for page in capture.get("pages", []):
        for index, raw in enumerate(page.get("content_sections", [])):
            section = raw if isinstance(raw, dict) else raw.model_dump()
            text, heading = _clean(section.get("text")), _clean(section.get("heading"))
            candidates = [text, _clean(f"{heading}. {text}") if heading else text]
            normalized = [_normal(item) for item in candidates]
            if needle in normalized or any(needle == item for item in normalized):
                method, confidence = "exact_normalized", 100
            elif any(needle in item or item in needle for item in normalized):
                method, confidence = "contained_text", 92
            else:
                section_tokens = _tokens(" ".join(candidates))
                overlap = len(needle_tokens & section_tokens) / max(1, len(needle_tokens))
                sequence = max(SequenceMatcher(None, needle, item).ratio() for item in normalized)
                confidence = round(100 * (overlap * .7 + sequence * .3))
                method = "token_window"
            payload = {
                "heading": heading or None, "heading_level": section.get("heading_level"),
                "element_type": section.get("element_type", "paragraph"), "position": section.get("position", index + 1),
                "interactive": bool(section.get("interactive")), "hidden": bool(section.get("hidden")),
                "source_url": page.get("final_url") or page.get("requested_url"), "method": method, "confidence": confidence,
            }
            if best is None or confidence > best[0]:
                best = (confidence, payload)
    return best[1] if best and best[0] >= 55 else None


def _heading_score(question: str, heading: str | None) -> int:
    if not heading:
        return 30
    overlap = len(_tokens(question) & _tokens(heading)) / max(1, len(_tokens(question)))
    return 100 if overlap >= .5 else 80 if overlap >= .25 else 60


def _format_score(question_type: str, element_type: str, excerpt: str) -> int:
    if question_type in {"list", "steps"}:
        return 100 if element_type in {"list_item", "table"} else 60
    if question_type == "comparison":
        return 100 if element_type == "table" else 65
    if question_type == "definition":
        return 100 if element_type == "definition" else 85
    if question_type == "value":
        return 100 if re.search(r"\b\d+(?:[.:]\d+)?\b", " ".join(excerpt.split()[:25])) else 65
    return 90 if element_type in {"paragraph", "definition"} else 80


def _concision_score(question_type: str, words: int) -> int:
    upper = 150 if question_type in {"list", "steps", "comparison"} else 90
    return 100 if 12 <= words <= upper else 70 if 7 <= words < 12 or upper < words <= upper + 50 else 35


def _recommend(question_type: str, heading_issue: bool) -> str:
    lead = {
        "yes_no": "Begin with an explicit yes or no, then state any condition or exception.",
        "value": "Put the requested time, price, distance or value in the opening sentence.",
        "policy": "State the rule first, then list its conditions and exceptions.",
        "steps": "Present the answer as an ordered sequence of actions.",
        "comparison": "Use labelled criteria or a compact comparison table.",
        "list": "Present the supported options as a concise labelled list.",
        "definition": "Open with a one-sentence definition before adding detail.",
        "location": "State the place first and add distance or travel context immediately after it.",
        "explanation": "Lead with one direct, self-contained sentence before supporting detail.",
    }[question_type]
    if heading_issue:
        lead += " Place it immediately below a heading that names the question topic."
    return lead + " Preserve only the approved facts in the retained passage."


def analyze_answer_structure(capture: dict[str, Any], discovery: dict[str, Any], gap_result: dict[str, Any], page_url: str) -> dict[str, Any]:
    """Assess structure only for answers already retained by Answer Gap."""
    gap_detail = gap_result.get("detail", gap_result)
    entries: list[dict[str, Any]] = []
    for assessment in gap_detail.get("assessments", []):
        passage = assessment.get("passage") or {}
        excerpt = _clean(passage.get("excerpt"))
        if assessment.get("status") not in {"answered", "partial"} or not excerpt:
            continue
        locator = _locate(capture, excerpt)
        question_type = _question_type(assessment["question"])
        directness = int((assessment.get("dimensions") or {}).get("directness", 0))
        self_containment = int((assessment.get("dimensions") or {}).get("extractability", 0))
        words = len(re.findall(r"[A-Za-z0-9]+", excerpt))
        issues: list[str] = []
        dimensions: dict[str, int] = {}
        score: int | None = None
        if locator:
            dimensions = {
                "direct_opening": directness, "self_containment": self_containment,
                "heading_context": _heading_score(assessment["question"], locator["heading"]),
                "format_suitability": _format_score(question_type, locator["element_type"], excerpt),
                "concision": _concision_score(question_type, words),
            }
            score = round(sum(dimensions[key] * weight for key, weight in WEIGHTS.items()) / 100)
            if dimensions["direct_opening"] < 70: issues.append("The answer does not lead with the requested information.")
            if dimensions["self_containment"] < 70: issues.append("The answer depends on surrounding copy to be understood.")
            if dimensions["heading_context"] < 70: issues.append("The captured heading does not clearly name the question topic.")
            if dimensions["format_suitability"] < 70: issues.append(f"The answer format does not suit a {question_type.replace('_', ' ')} question.")
            if dimensions["concision"] < 70: issues.append("The answer length is outside the useful range for this question type.")
            if locator["hidden"]: issues.append("The server HTML marks this answer block as hidden.")
            elif locator["interactive"]: issues.append("The answer sits in an interactive container and needs rendered visibility review.")
            status = "strong" if score >= 85 and not locator["hidden"] else "needs_review" if score >= 65 and not locator["hidden"] else "weak"
        else:
            status = "unable_to_locate"
            issues.append("The retained passage could not be mapped confidently to a captured content section.")
        entries.append({
            "question_id": assessment["question_id"], "lineage_id": assessment.get("lineage_id", assessment["question_id"]),
            "question": assessment["question"], "question_type": question_type, "answer_status": assessment["status"],
            "structure_status": status, "structure_score": score, "assessment_confidence": locator["confidence"] if locator else 0,
            "locator_method": locator["method"] if locator else "unresolved", "heading": locator["heading"] if locator else None,
            "heading_level": locator["heading_level"] if locator else None, "element_type": locator["element_type"] if locator else None,
            "position": locator["position"] if locator else None, "interactive": locator["interactive"] if locator else None,
            "hidden": locator["hidden"] if locator else None, "word_count": words,
            "source_url": (locator or {}).get("source_url") or passage.get("source_url") or page_url,
            "source_excerpt": excerpt, "issues": issues,
            "recommended_action": _recommend(question_type, not locator or dimensions.get("heading_context", 0) < 70) if status != "strong" else None,
            "dimensions": dimensions,
        })
    scored = [item for item in entries if item["structure_score"] is not None]
    score = round(sum(item["structure_score"] for item in scored) / len(scored)) if scored else None
    confidence = round(sum(item["assessment_confidence"] for item in scored) / len(scored)) if scored else None
    # A passage we could not locate is an assessment limitation, not a verified
    # page defect. Keep it visible in the matrix without creating an action.
    improvements = [item for item in entries if item["structure_status"] in {"needs_review", "weak"}]
    unlocated = [item for item in entries if item["structure_status"] == "unable_to_locate"]
    return {"status": "complete", "detail": {
        "answer_structure_score": score, "assessment_confidence_score": confidence,
        "assessed_answer_count": len(entries), "scored_answer_count": len(scored),
        "strong_count": sum(item["structure_status"] == "strong" for item in entries),
        "needs_review_count": sum(item["structure_status"] == "needs_review" for item in entries),
        "weak_count": sum(item["structure_status"] == "weak" for item in entries),
        "unable_to_locate_count": sum(item["structure_status"] == "unable_to_locate" for item in entries),
        "structure_entries": entries, "structure_improvements": improvements, "unlocated_entries": unlocated,
        "scoring_weights": WEIGHTS,
        "upstream_provenance": gap_detail.get("discovery_provenance", {}),
        "limitations": [
            "Only answers retained by Answer Gap as answered or partial are assessed; missing answers remain Answer Gap work.",
            "The audit uses captured server HTML. Interactive visibility is flagged for rendered review rather than inferred.",
            "A strong structure score measures the captured answer block, not whether an answer engine will cite it.",
        ], "source_url": page_url,
    }}
