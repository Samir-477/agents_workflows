from __future__ import annotations

import re
from collections import defaultdict
from statistics import median

from serp_competitor.models import CompetitorEvidence, PatternEvidence, SerpItem, SerpResult


STOP = {"and", "are", "best", "for", "from", "how", "the", "this", "that", "with", "your"}


def infer_intent(keyword: str, results: list[SerpItem]):
    text = " ".join([keyword, *(item.title for item in results)]).casefold()
    navigational = bool(re.search(r"\b(login|official|website|portal)\b", keyword.casefold()))
    transactional = bool(re.search(r"\b(buy|book|coupon|deal|download|order|near me)\b", text))
    commercial = bool(re.search(r"\b(best|compare|comparison|pricing|reviews?|top|versus|vs)\b", text))
    informational = bool(re.search(r"\b(how|what|why|guide|tutorial|examples?)\b", text))
    labels = [name for name, present in (
        ("navigational", navigational), ("transactional", transactional),
        ("commercial", commercial), ("informational", informational),
    ) if present]
    intent = labels[0] if len(labels) == 1 else "mixed" if labels else "informational"
    rationale = (
        f"Observed query and result-title modifiers indicate {', '.join(labels)} intent."
        if labels else
        "No strong commercial, transactional or navigational modifier was observed; informational intent is the cautious default."
    )
    return intent, rationale


def _patterns(competitors: list[CompetitorEvidence], attribute: str, limit: int = 12):
    sources = defaultdict(set)
    labels = {}
    for page in competitors:
        if not page.fetched:
            continue
        for raw in getattr(page, attribute):
            normalized = " ".join(re.findall(r"[a-z0-9]+", raw.casefold()))
            if not normalized:
                continue
            labels.setdefault(normalized, raw)
            sources[normalized].add(page.url)
    return [
        PatternEvidence(label=labels[key], count=len(urls), source_urls=sorted(urls))
        for key, urls in sorted(sources.items(), key=lambda item: (-len(item[1]), item[0]))
        if len(urls) >= 2
    ][:limit]


def _topic_patterns(
    organic: list[SerpItem], competitors: list[CompetitorEvidence], limit: int = 12
) -> list[PatternEvidence]:
    """Find repeated one/two-word themes while retaining every supporting URL."""
    sources: dict[str, set[str]] = defaultdict(set)
    documents: dict[str, list[str]] = defaultdict(list)
    for item in organic:
        documents[item.url].append(item.title)
    for page in competitors:
        if page.fetched:
            documents[page.url].extend(page.headings)
    for url, parts in documents.items():
        tokens = [
            token for token in re.findall(r"[a-z0-9]+", " ".join(parts).casefold())
            if len(token) > 2 and token not in STOP
        ]
        terms = set(tokens)
        terms.update(
            f"{left} {right}" for left, right in zip(tokens, tokens[1:])
            if left != right
        )
        for term in terms:
            sources[term].add(url)
    recurring = [item for item in sources.items() if len(item[1]) >= 2]
    recurring.sort(key=lambda item: (-len(item[1]), -len(item[0].split()), item[0]))
    return [
        PatternEvidence(label=term, count=len(urls), source_urls=sorted(urls))
        for term, urls in recurring[:limit]
    ]


def compile_result(
    run, organic, questions, related, answer_box, observed_at, competitors, *, snapshot_source_run_id=None
):
    intent, rationale = infer_intent(run.request.target_keyword, organic)
    fetched = [page for page in competitors if page.fetched]
    heading_patterns = _patterns(competitors, "headings")
    schema_patterns = _patterns(competitors, "schema_types", 8)
    topic_patterns = _topic_patterns(organic, competitors)
    counts = [page.word_count for page in fetched if page.word_count is not None]
    warnings = []
    if not questions:
        warnings.append("No People Also Ask entries were present in this Serper response.")
    if not related:
        warnings.append("No related-search entries were present in this Serper response.")
    if len(fetched) < min(run.request.inspect_limit, len(organic)):
        warnings.append(f"Only {len(fetched)} of {min(run.request.inspect_limit, len(organic))} selected competitor pages were inspectable.")
    recommendations = [
        "Use the observed intent and source-backed patterns when creating the content brief; review each source before treating a pattern as required.",
        "Cover recurring competitor headings only when they help the target reader, and add original evidence or expertise rather than copying their structure.",
    ]
    if questions:
        recommendations.append("Answer the observed search questions clearly where they fit the page's intent.")
    return SerpResult(
        run_id=run.id, target_keyword=run.request.target_keyword,
        country=run.request.country.lower(), language=run.request.language.lower(),
        observed_at=observed_at, search_intent=intent, intent_rationale=rationale,
        organic_results=organic, questions=questions, related_searches=related,
        answer_box=answer_box,
        competitors=competitors, common_headings=heading_patterns,
        topic_patterns=topic_patterns,
        common_schema=schema_patterns,
        median_word_count=round(median(counts)) if counts else None,
        recommendations=recommendations, warnings=warnings,
        limitations=[
            "Search results are a timestamped Google SERP sample for the selected country and language; rankings can vary by time, location and personalization.",
            "Word counts, headings and schema describe only successfully fetched HTML pages. They are observations, not universal content targets.",
            "This workflow does not measure search volume, traffic, backlinks or AI-answer citations.",
        ],
        snapshot_source_run_id=snapshot_source_run_id,
    )
