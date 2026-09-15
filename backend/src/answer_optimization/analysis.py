from __future__ import annotations

import re
from typing import Any

STOP = {
    "a", "an", "and", "are", "at", "be", "can", "do", "does", "for", "how",
    "in", "is", "it", "of", "on", "or", "resort", "the", "this", "to", "what",
    "where", "which", "who", "with", "your",
}
# The word budget from the product brief. Kept as a wide accept band so a
# fully grounded, well-formed answer is never discarded over a soft target;
# `within_target_length` still reports whether the 40-60 goal was hit.
ACCEPT_WORD_RANGE = (25, 75)
TARGET_WORD_RANGE = (40, 60)
BATCH_SIZE = 3
PROTECTED_MEANING_TERMS = {
    "not", "no", "never", "without", "except", "only", "must", "cannot",
    "may", "might", "included", "excluded", "free",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", str(value or "").casefold()) if len(token) > 2 and token not in STOP}


def _ordered_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z]+|\d+(?:[.:]\d+)?", str(value or "").casefold())


def _lcs_ratio(left: list[str], right: list[str]) -> float:
    if not left:
        return 0.0
    row = [0] * (len(right) + 1)
    for token in left:
        previous = 0
        for index, other in enumerate(right, 1):
            saved = row[index]
            row[index] = previous + 1 if token == other else max(row[index], row[index - 1])
            previous = saved
    return row[-1] / len(left)


def _fallback_extract(excerpt: str) -> str:
    words = excerpt.split()
    if len(words) <= ACCEPT_WORD_RANGE[1]:
        return excerpt
    return " ".join(words[: ACCEPT_WORD_RANGE[1]]).rstrip(",.;:") + "…"


def _validate_draft(draft: str, passage_excerpt: str, question: str = "") -> tuple[bool, str]:
    """Apply conservative lexical safety checks before editorial review.

    This deterministic gate catches unsupported vocabulary, changed protected
    meaning terms, introduced numbers and large word-order changes. It reduces
    obvious grounding failures but does not replace editorial fact review.
    """
    words = draft.split()
    if not (ACCEPT_WORD_RANGE[0] <= len(words) <= ACCEPT_WORD_RANGE[1]):
        return False, f"Draft length ({len(words)} words) fell outside the acceptable range."
    draft_tokens = _tokens(draft)
    passage_tokens = _tokens(passage_excerpt)
    unsupported = draft_tokens - passage_tokens
    if unsupported:
        return False, "The draft introduced terms absent from the retained passage: " + ", ".join(sorted(unsupported)[:6]) + "."
    source_ordered, draft_ordered = _ordered_tokens(passage_excerpt), _ordered_tokens(draft)
    source_protected = [term for term in source_ordered if term in PROTECTED_MEANING_TERMS]
    draft_protected = [term for term in draft_ordered if term in PROTECTED_MEANING_TERMS]
    if source_protected != draft_protected:
        return False, "The draft changed or removed a protected polarity, obligation, exclusivity, or inclusion term."
    source_numbers = [term for term in source_ordered if re.fullmatch(r"\d+(?:[.:]\d+)?", term)]
    draft_numbers = [term for term in draft_ordered if re.fullmatch(r"\d+(?:[.:]\d+)?", term)]
    if any(term not in source_numbers for term in draft_numbers):
        return False, "The draft introduced a number or time absent from the retained passage."
    if _lcs_ratio(draft_ordered, source_ordered) < 0.60:
        return False, "The draft rearranged too much source wording for deterministic validation."
    subject = _tokens(question)
    if subject and not (subject & draft_tokens):
        return False, "The draft did not retain the question's subject terms."
    return True, "The draft passed lexical, order, polarity and numeric safety checks; editorial fact review is still required."


def _checklist_item(gap: dict[str, Any]) -> dict[str, Any]:
    topic = gap.get("topic") or "this topic"
    return {
        "question_id": gap["question_id"], "lineage_id": gap.get("lineage_id", gap["question_id"]), "question": gap["question"],
        "topic": gap.get("topic"), "intent": gap.get("intent"), "priority": gap.get("priority", "medium"),
        "priority_score": gap.get("priority_score", 0), "status": "needs_facts", "fallback_reason": None,
        "draft_answer": None, "word_count": None, "within_target_length": None, "grounding_verified": None,
        "checklist_action": f"No captured passage addresses this question. Confirm the {topic} fact with the property "
                             f"team, then write one direct sentence answering ‘{gap['question']}’ using the confirmed fact.",
        "source_excerpt": None, "source_url": None,
        "reason": "No retained passage was close enough to this question's subject to draft from.",
    }


def _drafted_item(gap: dict[str, Any], draft: str | None, provider_error: str | None) -> dict[str, Any]:
    passage = gap.get("passage") or {}
    excerpt = passage.get("excerpt") or ""
    reason, fallback_reason = None, None
    if provider_error:
        # The drafting call itself never ran or never returned for this
        # question. That says something about this run's provider, not about
        # whether the resort's content answers the question, so it must not
        # be scored the same as a draft the model produced and got rejected.
        reason, fallback_reason = provider_error, "provider_unavailable"
    elif draft:
        ok, validation_reason = _validate_draft(draft, excerpt, gap.get("question", ""))
        if ok:
            words = draft.split()
            return {
                "question_id": gap["question_id"], "lineage_id": gap.get("lineage_id", gap["question_id"]), "question": gap["question"],
                "topic": gap.get("topic"), "intent": gap.get("intent"), "priority": gap.get("priority", "medium"),
                "priority_score": gap.get("priority_score", 0), "status": "drafted", "fallback_reason": None,
                "draft_answer": draft, "word_count": len(words),
                "within_target_length": TARGET_WORD_RANGE[0] <= len(words) <= TARGET_WORD_RANGE[1],
                "grounding_verified": False, "checklist_action": None,
                "source_excerpt": excerpt, "source_url": passage.get("source_url"), "reason": validation_reason,
            }
        reason, fallback_reason = validation_reason, "validation_failed"
    else:
        reason, fallback_reason = "The model did not return a draft for this question; the retained passage was used as-is.", "no_draft_returned"
    fallback = _fallback_extract(excerpt) if excerpt else None
    return {
        "question_id": gap["question_id"], "lineage_id": gap.get("lineage_id", gap["question_id"]), "question": gap["question"],
        "topic": gap.get("topic"), "intent": gap.get("intent"), "priority": gap.get("priority", "medium"),
        "priority_score": gap.get("priority_score", 0), "status": "fallback_extractive" if fallback else "needs_facts",
        "fallback_reason": fallback_reason if fallback else None,
        "draft_answer": fallback, "word_count": len(fallback.split()) if fallback else None,
        "within_target_length": (TARGET_WORD_RANGE[0] <= len(fallback.split()) <= TARGET_WORD_RANGE[1]) if fallback else None,
        "grounding_verified": False if fallback else None, "checklist_action": None if fallback else _checklist_item(gap)["checklist_action"],
        "source_excerpt": excerpt or None, "source_url": passage.get("source_url"), "reason": reason,
    }


async def optimize_answers(gap_result: dict[str, Any], page_url: str, generator) -> dict[str, Any]:
    """Draft grounded direct answers for verified Answer Gap results.

    A `partial` gap has a retained passage, so a compressed, word-checked
    rewrite of that passage is safe to draft. A `missing` gap has no such
    passage — nothing on the page supports an answer — so it receives a
    fact-gathering checklist instead of a fabricated answer. This split is
    the one deliberate change from a naive "always draft an answer" design:
    a resort's guests can be misled by an invented amenity or policy, and no
    other agent in this pipeline invents a fact the captured page never
    stated.
    """
    gap_detail = gap_result.get("detail", gap_result)
    gaps = gap_detail.get("prioritized_gaps", [])
    partial_gaps = [gap for gap in gaps if gap.get("status") == "partial" and (gap.get("passage") or {}).get("excerpt")]
    missing_gaps = [gap for gap in gaps if gap.get("status") != "partial"]

    drafts: dict[str, str] = {}
    batch_errors: dict[str, str] = {}
    for start in range(0, len(partial_gaps), BATCH_SIZE):
        batch = partial_gaps[start:start + BATCH_SIZE]
        try:
            drafts.update(await generator.draft_batch([
                {"question_id": gap["question_id"], "question": gap["question"], "passage": (gap.get("passage") or {}).get("excerpt", "")}
                for gap in batch
            ]))
        except Exception as error:
            for gap in batch:
                batch_errors[gap["question_id"]] = f"The drafting request failed ({error.__class__.__name__}); the retained passage was used as-is."

    optimized = [
        _drafted_item(gap, drafts.get(gap["question_id"]), batch_errors.get(gap["question_id"]))
        for gap in partial_gaps
    ] + [_checklist_item(gap) for gap in missing_gaps]
    optimized.sort(key=lambda item: (-item["priority_score"], item["question_id"]))

    drafted_count = sum(item["status"] == "drafted" for item in optimized)
    fallback_count = sum(item["status"] == "fallback_extractive" for item in optimized)
    needs_facts_count = sum(item["status"] == "needs_facts" for item in optimized)
    drafting_unavailable_count = sum(item.get("fallback_reason") in {"provider_unavailable", "no_draft_returned"} for item in optimized)
    # A provider outage or an empty model response says nothing about whether
    # this resort's content answers the question — the drafting step simply
    # never ran. Scoring it as a 0 would read as "this page has no coverage"
    # when the true state is "this run could not attempt it." Only a gap the
    # model actually attempted and failed to ground counts against coverage.
    scoreable = drafted_count + sum(item.get("fallback_reason") == "validation_failed" for item in optimized)
    optimization_coverage_score = round(100 * drafted_count / scoreable) if scoreable else None

    limitations = [
        "Drafts are generated only for gaps with a retained passage; a question the page never addresses "
        "receives a fact-gathering action, never an invented answer.",
        "Every draft receives conservative lexical, word-order, polarity and number checks against its source passage. "
        "Passing these checks is not factual approval; an editor must still compare meaning and context.",
        "The 40-60 word target is a starting point. Treat an accepted draft outside that range as needing "
        "an editorial pass, not a rejected result.",
        "This agent does not publish content. Every draft requires content-owner and editorial approval "
        "before use.",
        "Only questions Answer Gap verified from observed evidence are processed; inferred discovery "
        "hypotheses remain excluded.",
    ]
    if drafting_unavailable_count:
        limitations.append(
            f"{drafting_unavailable_count} gap(s) could not be attempted this run because the drafting provider "
            "was unavailable or returned no usable draft; the retained passage was shown instead and coverage "
            "excludes them rather than scoring them as failed drafts. Rerun this agent to attempt them."
        )

    return {
        "status": "complete",
        "detail": {
            "optimization_coverage_score": optimization_coverage_score,
            "gap_count": len(gaps),
            "partial_gap_count": len(partial_gaps),
            "missing_gap_count": len(missing_gaps),
            "drafted_count": drafted_count,
            "fallback_count": fallback_count,
            "needs_facts_count": needs_facts_count,
            "drafting_unavailable_count": drafting_unavailable_count,
            "upstream_provenance": gap_detail.get("discovery_provenance", {}),
            "optimized_answers": optimized,
            "discovery_provenance": gap_detail.get("discovery_provenance", {}),
            "limitations": limitations,
            "source_url": page_url,
        },
    }
