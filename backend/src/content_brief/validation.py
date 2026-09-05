from __future__ import annotations

import re
from dataclasses import dataclass

from content_brief.models import (
    BriefValidationIssue,
    ContentBriefCreate,
    ContentBriefDraft,
    ContentBriefResult,
)


GENERIC_ANCHORS = {"click here", "here", "read more", "learn more", "more", "this page"}
UNSUPPORTED_CLAIMS = re.compile(
    r"\b(guarantee(?:d|s)?|will rank|rank first|increase traffic|boost conversions|proven(?: to)?)\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class ValidationOutcome:
    result: ContentBriefResult
    repair_instructions: list[str]


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold()) if len(token) > 2}


def validate_brief(
    generation_id: str,
    request: ContentBriefCreate,
    draft: ContentBriefDraft,
) -> ValidationOutcome:
    issues: list[BriefValidationIssue] = []
    repair: list[str] = []

    keyword_tokens = _tokens(request.target_keyword)
    title_tokens = _tokens(draft.suggested_title)
    outline_text = " ".join(section.heading for section in draft.outline)
    if keyword_tokens and len(keyword_tokens & title_tokens) / len(keyword_tokens) < 0.6:
        issues.append(BriefValidationIssue(severity="warning", code="weak-title-keyword-alignment", message="The suggested title only weakly reflects the target keyword."))
    if keyword_tokens and len(keyword_tokens & _tokens(outline_text)) / len(keyword_tokens) < 0.6:
        issues.append(BriefValidationIssue(severity="error", code="missing-outline-topic", message="The outline does not clearly carry the target topic into its headings."))
        repair.append("Make the target topic explicit in at least one natural H2 without keyword stuffing.")

    seen_h2 = False
    headings: set[str] = set()
    for index, section in enumerate(draft.outline, start=1):
        normalized = re.sub(r"\W+", " ", section.heading.casefold()).strip()
        if section.heading_level == "H2":
            seen_h2 = True
        elif not seen_h2:
            issues.append(BriefValidationIssue(severity="error", code="h3-before-h2", message=f"Section {index} uses H3 before any H2."))
            repair.append("Ensure every H3 follows a relevant H2.")
        if normalized in headings:
            issues.append(BriefValidationIssue(severity="error", code="duplicate-heading", message=f"Duplicate outline heading: {section.heading}"))
            repair.append("Use unique headings with distinct section jobs.")
        headings.add(normalized)
    if sum(section.heading_level == "H2" for section in draft.outline) < 3:
        issues.append(BriefValidationIssue(severity="error", code="thin-outline", message="The brief needs at least three substantive H2 sections."))
        repair.append("Add enough distinct H2 sections for a complete writer handoff.")

    allocated_words = sum(section.suggested_words for section in draft.outline)
    if allocated_words < draft.target_word_count_min * 0.75 or allocated_words > draft.target_word_count_max * 1.25:
        issues.append(BriefValidationIssue(severity="warning", code="word-budget-mismatch", message=f"Section budgets total {allocated_words} words but the target range is {draft.target_word_count_min}–{draft.target_word_count_max}."))
        repair.append("Align section word allowances with the overall target range.")

    allowed_urls = {url.rstrip("/") for url in request.existing_urls}
    valid_links = []
    for link in draft.internal_links:
        normalized = link.target_url.rstrip("/")
        if normalized not in allowed_urls:
            issues.append(BriefValidationIssue(severity="error", code="invented-internal-url", message=f"Remove internal link not supplied by the user: {link.target_url}"))
            repair.append("Use only exact URLs from existing_urls; return no link when no supplied URL fits.")
            continue
        if link.anchor_direction.strip().casefold() in GENERIC_ANCHORS:
            issues.append(BriefValidationIssue(severity="warning", code="generic-anchor", message=f"Replace generic anchor direction for {link.target_url}."))
            repair.append("Use descriptive anchor direction that identifies the destination topic.")
        valid_links.append(link)

    conversion_notes = draft.conversion_notes
    if conversion_notes and not (request.business_goal or request.product_context):
        issues.append(BriefValidationIssue(severity="warning", code="unsupported-cta", message="Conversion notes were removed because no business goal or product context was supplied."))
        conversion_notes = []

    faq_seen: set[str] = set()
    for faq in draft.faqs:
        normalized = re.sub(r"\W+", " ", faq.question.casefold()).strip()
        if normalized in faq_seen:
            issues.append(BriefValidationIssue(severity="error", code="duplicate-faq", message=f"Duplicate FAQ question: {faq.question}"))
            repair.append("Return unique FAQ questions with different reader jobs.")
        faq_seen.add(normalized)
        if not faq.question.rstrip().endswith("?"):
            issues.append(BriefValidationIssue(severity="warning", code="faq-punctuation", message=f"FAQ should be phrased as a question: {faq.question}"))

    rendered = draft.model_dump_json()
    if UNSUPPORTED_CLAIMS.search(rendered):
        issues.append(BriefValidationIssue(severity="error", code="unsupported-outcome-claim", message="The brief contains an unsupported ranking, traffic or conversion promise."))
        repair.append("Remove outcome promises; describe editorial purpose without guaranteeing performance.")

    supplied_text = " ".join(filter(None, [request.target_keyword, request.audience, *request.secondary_keywords, request.angle, request.business_goal, request.product_context, request.source_notes])).casefold()
    for item in draft.coverage:
        if item.source == "provided" and item.name.casefold() not in supplied_text:
            issues.append(BriefValidationIssue(severity="warning", code="mislabelled-source", message=f"Coverage item '{item.name}' is not visibly present in the assignment and should be labelled inferred."))
            repair.append("Mark coverage items as provided only when their name appears in the assignment; otherwise use inferred.")

    sanitized = draft.model_copy(update={"internal_links": valid_links, "conversion_notes": conversion_notes}, deep=True)
    error_count = sum(issue.severity == "error" for issue in issues)
    warning_count = sum(issue.severity == "warning" for issue in issues)
    score = max(0, 100 - error_count * 18 - warning_count * 5)
    limitations = [
        "Search intent, questions and entities are inferred from the assignment; no live SERP or search-volume dataset was queried.",
        "Suggested facts, statistics, regulations and product claims must be verified by the writer before publication.",
    ]
    if not request.existing_urls:
        limitations.append("No existing page URLs were supplied, so the brief cannot contain a grounded internal-link plan.")
    result = ContentBriefResult(
        generation_id=generation_id, target_keyword=request.target_keyword,
        audience=request.audience, content_mode=request.content_mode, brief=sanitized,
        quality_score=score, ready_for_handoff=error_count == 0,
        issues=issues, warnings=[], evidence_limitations=limitations,
    )
    return ValidationOutcome(result=result, repair_instructions=list(dict.fromkeys(repair)))
