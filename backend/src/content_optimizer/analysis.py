from __future__ import annotations

import re
from dataclasses import dataclass

from content_optimizer.models import (
    ContentOptimizerResult,
    OptimizerAction,
    OptimizerAssessment,
    OptimizerEvidence,
)


WORDS = re.compile(r"[\w'-]+", re.UNICODE)
SENTENCES = re.compile(r"(?<=[.!?])\s+")


@dataclass
class ContentInput:
    mode: str
    text: str
    url: str | None = None
    title: str | None = None
    meta_description: str | None = None
    headings: list[tuple[str, str]] | None = None
    internal_links: int | None = None
    external_links: int | None = None
    images_total: int | None = None
    images_missing_alt: int | None = None
    images_empty_alt: int | None = None
    schema_types: list[str] | None = None
    json_ld_errors: list[str] | None = None
    truncated: bool = False


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)", text.casefold()) is not None


def _excerpt(text: str, limit: int = 220) -> str:
    clean = " ".join(text.split())
    return clean[:limit] + ("…" if len(clean) > limit else "")


def analyze_content(run, content: ContentInput, *, research=None, brief=None, warnings=None):
    request = run.request
    warnings = list(warnings or [])
    words = WORDS.findall(content.text)
    word_count = len(words)
    normalized_text = " ".join(words).casefold()
    primary = request.target_keyword.casefold()
    exact_count = len(re.findall(rf"(?<!\w){re.escape(primary)}(?!\w)", normalized_text))
    headings = content.headings or []
    heading_text = " ".join(text for _, text in headings)
    evidence: list[OptimizerEvidence] = []
    assessments: list[OptimizerAssessment] = []
    actions: list[OptimizerAction] = []

    def add_evidence(identifier, label, observed, source_type="page", source_url=None):
        evidence.append(OptimizerEvidence(id=identifier, label=label, observed=observed, source_type=source_type, source_url=source_url))

    def assess(key, label, status, summary, evidence_ids=None):
        assessments.append(OptimizerAssessment(key=key, label=label, status=status, summary=summary, evidence_ids=evidence_ids or []))

    def action(priority, category, issue, section, observed, proposed, confidence, effort, rationale, ids=None):
        actions.append(OptimizerAction(priority=priority, category=category, issue=issue, affected_section=section, observed_text=observed, proposed_action=proposed, confidence=confidence, effort=effort, impact_rationale=rationale, evidence_ids=ids or []))

    source_type = "page" if content.mode == "url" else "supplied_text"
    add_evidence("content:body", "Content sample", _excerpt(content.text), source_type, content.url)
    add_evidence("content:word-count", "Observed word count", str(word_count), source_type, content.url)
    add_evidence("content:keyword-count", "Exact target phrase uses", str(exact_count), source_type, content.url)

    title_or_heading = " ".join(filter(None, [content.title, heading_text]))
    opening = " ".join(words[:120])
    aligned = _contains(title_or_heading, request.target_keyword) or _contains(opening, request.target_keyword)
    assess("intent_alignment", "Intent alignment", "good" if aligned else "review", "The target phrase is visible in a prominent element or opening." if aligned else "The target phrase was not found in the title, headings or opening sample.", ["content:body"])
    if not aligned:
        action("high", "Content", "Target topic is not established early", "Title, H1 or introduction", _excerpt(opening), f"State the page's relationship to ‘{request.target_keyword}’ naturally in a prominent heading or the opening, while matching the reader's actual intent.", "high", "small", "Clear early topic framing helps readers and search systems understand the page.", ["content:body"])

    if exact_count == 0:
        assess("keyword_usage", "Keyword use", "review", "The exact target phrase was not observed in the analyzed body text.", ["content:keyword-count"])
        action("medium", "Content", "Target phrase is absent", "Most relevant section", "0 exact uses", f"Use ‘{request.target_keyword}’ once where it reads naturally; do not force a density target.", "high", "small", "A natural exact mention can remove ambiguity without encouraging repetition.", ["content:keyword-count"])
    elif word_count and exact_count >= 6 and exact_count / word_count > 0.025:
        assess("keyword_usage", "Keyword use", "review", f"The exact phrase appears {exact_count} times in {word_count} words; repetition needs editorial review.", ["content:keyword-count", "content:word-count"])
        action("medium", "Content", "Potentially repetitive exact phrase", "Whole page", f"{exact_count} exact uses across {word_count} words", "Read the repeated passages aloud and replace only awkward uses with specific, natural wording. Keep necessary technical repetitions.", "medium", "medium", "Reducing mechanical repetition can improve clarity; the threshold is a review trigger, not a ranking rule.", ["content:keyword-count", "content:word-count"])
    else:
        assess("keyword_usage", "Keyword use", "good", f"The exact phrase appears {exact_count} time(s) without triggering the conservative repetition review.", ["content:keyword-count", "content:word-count"])

    if request.secondary_keywords:
        missing_secondary = [item for item in request.secondary_keywords if not _contains(content.text, item)]
        add_evidence("content:secondary-keywords", "Secondary keyword review", f"Supplied: {', '.join(request.secondary_keywords)}; not found: {', '.join(missing_secondary) or 'none'}", source_type, content.url)
        assess("secondary_keywords", "Secondary topics", "review" if missing_secondary else "good", f"{len(missing_secondary)} of {len(request.secondary_keywords)} supplied secondary phrases were not found exactly.", ["content:secondary-keywords"])
        if missing_secondary:
            action("low", "Content", "Review missing secondary topics", "Relevant sections", ", ".join(missing_secondary), "Use these phrases or close variants only where they represent useful subtopics; do not insert them mechanically.", "medium", "small", "Supplied secondary phrases can reveal intended coverage, but exact-match absence alone is not an SEO defect.", ["content:secondary-keywords"])
    else:
        assess("secondary_keywords", "Secondary topics", "not_assessed", "No secondary keywords were supplied.")

    if headings:
        add_evidence("content:headings", "Ordered headings", " | ".join(f"{level.upper()}: {text}" for level, text in headings[:30]), source_type, content.url)
        h1_count = sum(level == "h1" for level, _ in headings)
        structure_good = h1_count == 1 and any(level in {"h2", "h3"} for level, _ in headings)
        assess("heading_structure", "Heading structure", "good" if structure_good else "review", f"Observed {h1_count} H1 and {sum(level == 'h2' for level, _ in headings)} H2 headings.", ["content:headings"])
        if not structure_good:
            action("medium", "Structure", "Heading hierarchy needs review", "Page outline", evidence[-1].observed, "Use one descriptive H1 and organize distinct reader questions under clear H2/H3 headings without skipping levels for styling.", "high", "medium", "A clear outline improves scanning and machine interpretation.", ["content:headings"])
    else:
        assess("heading_structure", "Heading structure", "not_assessed" if content.mode == "text" else "review", "Plain text does not expose HTML headings." if content.mode == "text" else "No H1-H3 headings were observed.")
        if content.mode == "url":
            action("high", "Structure", "No semantic headings observed", "Page outline", "No H1-H3 elements", "Add a descriptive H1 and reader-centered H2 sections.", "high", "medium", "Headings make the page easier to navigate and interpret.")

    if word_count < 150:
        assess("content_depth", "Content depth", "review", f"Only {word_count} words were available for analysis.", ["content:word-count"])
        action("medium", "Content", "Limited answer depth", "Whole page", f"{word_count} observed words", "Check whether the page fully answers the reader's task; add only missing explanations, examples or proof rather than writing to a universal word target.", "medium", "large", "Very short copy may leave the intended task unresolved, depending on page type.", ["content:word-count"])
    else:
        assess("content_depth", "Content depth", "good", f"{word_count} words were available; adequacy still depends on intent and evidence.", ["content:word-count"])

    sentences = [item for item in SENTENCES.split(content.text) if WORDS.search(item)]
    average_sentence = round(word_count / len(sentences), 1) if sentences else None
    if average_sentence is None:
        assess("readability", "Readability", "not_assessed", "Sentence boundaries were not reliable enough to assess.")
    elif average_sentence > 28:
        add_evidence("content:sentence-length", "Average observed sentence length", f"{average_sentence} words", source_type, content.url)
        assess("readability", "Readability", "review", f"Average observed sentence length is {average_sentence} words.", ["content:sentence-length"])
        action("low", "Readability", "Long sentence pattern", "Whole page", f"Average {average_sentence} words per detected sentence", "Split sentences that contain several independent ideas, while preserving necessary technical detail.", "medium", "small", "Shorter idea units can make complex content easier to scan.", ["content:sentence-length"])
    else:
        assess("readability", "Readability", "good", f"Average observed sentence length is {average_sentence} words.")

    observed_topics: list[tuple[str, list[str], str]] = []
    if research is not None:
        for index, item in enumerate(research.topic_patterns[:12]):
            identifier = f"serp:topic:{index + 1}"
            add_evidence(identifier, f"Observed SERP title pattern: {item.label}", f"Repeated across {item.count} result(s).", "serp", item.source_urls[0] if item.source_urls else None)
            tokens = [token.casefold() for token in WORDS.findall(item.label)]
            useful = (
                len(tokens) >= 2
                and not any(token.isdigit() or token in {"updated", "update"} for token in tokens)
                and not all(token in primary.split() for token in tokens)
                and not (tokens[0] in {"hotel", "resort"} and all(token in primary.split() for token in tokens[1:]))
            )
            if useful:
                observed_topics.append((item.label, [identifier], "SERP title pattern"))
        warnings.append("Broad recurring words from result titles were retained as SERP observations, not treated as missing page topics.")
    if brief is not None:
        for index, item in enumerate(brief.brief.coverage[:20]):
            identifier = f"brief:coverage:{index + 1}"
            add_evidence(identifier, f"Brief coverage: {item.name}", item.why_include, "brief")
            observed_topics.append((item.name, [identifier], f"brief {item.source}"))
    missing = [(topic, ids, origin) for topic, ids, origin in observed_topics if not _contains(content.text, topic)]
    if observed_topics:
        assess("topic_coverage", "Topic coverage", "review" if missing else "good", f"{len(missing)} of {len(observed_topics)} research/brief themes were not found as exact phrases.", [identifier for _, ids, _ in missing[:8] for identifier in ids])
        for topic, ids, origin in missing[:6]:
            action("medium", "Coverage", f"Review potential topic: {topic}", "Most relevant section", f"Not found as an exact phrase; source: {origin}", f"Review the linked evidence and add coverage of ‘{topic}’ only if it helps this audience and intent.", "medium", "medium", "The theme appeared in selected research or the supplied brief; absence is an editorial opportunity, not proof of a gap.", ids)
    else:
        assess("topic_coverage", "Topic coverage", "not_assessed", "No SERP research or content brief was attached, so comparative topic coverage was not assessed.")

    if research is not None and research.questions:
        unanswered = []
        for index, item in enumerate(research.questions[:8]):
            identifier = f"serp:question:{index + 1}"
            add_evidence(identifier, "Observed search question", item.question, "serp", item.source_url)
            question_terms = [term for term in WORDS.findall(item.question.casefold()) if len(term) > 3]
            if question_terms and sum(term in normalized_text for term in question_terms) < max(1, len(question_terms) // 2):
                unanswered.append((item.question, identifier))
        assess("question_coverage", "Question coverage", "review" if unanswered else "good", f"{len(unanswered)} of {len(research.questions[:8])} observed questions need editorial review.", [item[1] for item in unanswered])
        for question, identifier in unanswered[:3]:
            action("low", "Snippet opportunity", f"Review observed question: {question}", "Relevant section or FAQ", "Question terms were not substantially present.", "Answer the question directly only if it fits the page intent; keep the answer factual and supported.", "medium", "small", "A direct answer can improve reader usefulness and answer extraction.", [identifier])
    else:
        assess("question_coverage", "Question coverage", "not_assessed", "No observed search questions were attached.")

    if content.mode == "url":
        title = content.title or ""
        description = content.meta_description or ""
        add_evidence("page:metadata", "Observed metadata", f"Title: {title or '[missing]'} | Description: {description or '[missing]'}", "page", content.url)
        metadata_good = bool(title and description)
        assess("metadata", "Metadata", "good" if metadata_good else "review", "A title and meta description were observed." if metadata_good else "The title or meta description is missing.", ["page:metadata"])
        if not metadata_good:
            action("high", "Metadata", "Missing search-result copy", "HTML head", evidence[-1].observed, "Write a specific title and meta description that accurately preview this page and its intended reader task.", "high", "small", "Complete, accurate metadata gives searchers a clearer preview.", ["page:metadata"])
        link_summary = f"{content.internal_links or 0} internal and {content.external_links or 0} external links"
        add_evidence("page:links", "Observed links", link_summary, "page", content.url)
        assess("links", "Links", "good" if (content.internal_links or 0) > 0 else "review", link_summary, ["page:links"])
        if not (content.internal_links or 0):
            action("medium", "Links", "No internal links observed", "Body content", link_summary, "Add contextual links to genuinely useful related pages using descriptive anchor text.", "high", "small", "Contextual links help readers continue their task and connect related site content.", ["page:links"])
        image_summary = f"{content.images_total or 0} images; {content.images_missing_alt or 0} missing alt; {content.images_empty_alt or 0} empty alt"
        add_evidence("page:images", "Observed image alternatives", image_summary, "page", content.url)
        image_status = "review" if (content.images_missing_alt or 0) > 0 or (content.images_empty_alt or 0) > 0 else "good"
        assess("images", "Images and alt text", image_status, image_summary, ["page:images"])
        if (content.images_missing_alt or 0) > 0:
            action("high", "Images", "Images without an alt attribute", "Image elements", image_summary, "Add concise alt text to informative images. Use empty alt only for images confirmed as decorative.", "high", "small", "Useful alternatives improve access and communicate image meaning.", ["page:images"])
        elif (content.images_empty_alt or 0) > 0:
            action("low", "Images", "Empty alt needs contextual review", "Image elements", image_summary, "Confirm each empty-alt image is decorative; describe any image that carries information.", "medium", "small", "Empty alt is correct for decorative images but hides informative ones.", ["page:images"])
        schema = content.schema_types or []
        add_evidence("page:schema", "Observed schema types", ", ".join(schema) if schema else "None observed", "page", content.url)
        schema_errors = content.json_ld_errors or []
        if schema_errors:
            add_evidence("page:schema-errors", "Structured data parsing errors", "\n".join(schema_errors), "page", content.url)
        assess("schema", "Structured data", "good" if schema and not schema_errors else "review", "Parsing errors: " + "; ".join(schema_errors) if schema_errors else ", ".join(schema) if schema else "No JSON-LD schema type was observed.", ["page:schema", *(["page:schema-errors"] if schema_errors else [])])
        assess("freshness", "Freshness evidence", "not_assessed", "Published/modified dates and factual currency require source-specific review.")
    else:
        for key, label in (("metadata", "Metadata"), ("links", "Links"), ("images", "Images and alt text"), ("schema", "Structured data"), ("freshness", "Freshness evidence")):
            assess(key, label, "not_assessed", "Plain text does not expose the HTML or page-level evidence required for this check.")

    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    actions.sort(key=lambda item: (rank[item.priority], item.category, item.issue))
    assessed = [item for item in assessments if item.status != "not_assessed"]
    good = sum(item.status == "good" for item in assessed)
    score = round(100 * good / len(assessed)) if assessed else None
    if content.truncated:
        warnings.append("The fetched page text exceeded the evidence limit; findings describe the retained sample.")
    return ContentOptimizerResult(
        run_id=run.id, source_mode=content.mode, source_url=content.url,
        target_keyword=request.target_keyword, audience=request.audience,
        word_count=word_count, overall_score=score, assessed_checks=len(assessed),
        total_checks=len(assessments), assessments=assessments, actions=actions,
        evidence=evidence, research_run_id=request.research_run_id if research else None,
        content_brief_id=request.content_brief_id if brief else None, warnings=warnings,
        limitations=[
            "The score is the share of assessed checks marked good; unassessed checks are excluded and the score is not a traffic forecast.",
            "Keyword repetition, sentence length and topic matching are conservative review signals, not universal ranking thresholds.",
            "Recommendations do not assert traffic, revenue or ranking gains and require editorial and factual review before publication.",
        ],
    )
