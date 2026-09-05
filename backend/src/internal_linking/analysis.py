from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from internal_linking.models import (
    InternalLinkRecommendation,
    LinkCandidate,
    LinkRefinement,
    PageLinkSummary,
)
from seo_audit.crawler import CrawlResult
from seo_audit.models import PageRecord


GENERIC_ANCHORS = {
    "click here", "here", "read more", "learn more", "more", "details", "view",
    "this page", "this article", "this link", "continue", "go", "see more",
}
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in",
    "is", "it", "of", "on", "or", "our", "that", "the", "this", "to", "with", "your",
}
IMPORTANT_PATH_WORDS = {
    "pricing", "price", "product", "products", "service", "services", "solutions",
    "category", "categories", "collection", "collections", "book", "buy", "contact",
}


@dataclass(slots=True)
class AnalysisResult:
    candidates: list[LinkCandidate]
    pages: list[PageLinkSummary]
    observed_edge_count: int
    contextual_edge_count: int
    confirmed_orphan_count: int
    orphan_candidate_count: int
    weak_anchor_count: int


def normalize_url(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def tokens(text: str) -> set[str]:
    return {
        word for word in re.findall(r"[a-z0-9]+", text.casefold())
        if len(word) > 2 and word not in STOPWORDS
    }


def page_text(page: PageRecord) -> str:
    return " ".join(filter(None, [page.title, *page.h1, *page.h2, *(s.heading for s in page.content_sections), *(s.text[:500] for s in page.content_sections[:8])]))


def similarity(source: PageRecord, target: PageRecord) -> float:
    left, right = tokens(page_text(source)), tokens(page_text(target))
    if not left or not right:
        return 0.0
    shared = left & right
    return min(1.0, len(shared) / max(3, min(len(left), len(right))))


def page_role(url: str) -> str:
    words = set(re.findall(r"[a-z0-9]+", urlsplit(url).path.casefold()))
    if words & {"blog", "article", "guide", "resources", "learn", "news"}:
        return "content"
    if words & IMPORTANT_PATH_WORDS:
        return "commercial"
    return "general"


def _best_section(source: PageRecord, target: PageRecord) -> tuple[str | None, str | None]:
    target_terms = tokens(" ".join(filter(None, [target.title, *target.h1, *target.h2])))
    ranked = []
    for section in source.content_sections:
        overlap = len(tokens(f"{section.heading} {section.text}") & target_terms)
        ranked.append((overlap, section.heading, section.text[:260]))
    if ranked:
        overlap, heading, snippet = max(ranked, key=lambda item: item[0])
        if overlap:
            return heading or None, snippet or None
    first = source.content_sections[0] if source.content_sections else None
    return (first.heading or None, first.text[:260]) if first else (None, None)


def analyze_crawl(crawl: CrawlResult, important_urls: list[str]) -> AnalysisResult:
    pages = [
        p for p in crawl.pages
        if not p.fetch_error
        and p.status_code is not None
        and 200 <= p.status_code < 300
        and "noindex" not in {directive.casefold() for directive in p.robots_directives}
    ]
    by_url = {normalize_url(p.final_url): p for p in pages}
    important = {normalize_url(url) for url in important_urls}
    sitemap_inventory = {normalize_url(url) for url in crawl.sitemap_urls}
    incoming: dict[str, set[str]] = defaultdict(set)
    contextual_incoming: dict[str, set[str]] = defaultdict(set)
    outgoing: dict[str, set[str]] = defaultdict(set)
    contextual_outgoing: dict[str, set[str]] = defaultdict(set)
    edges: set[tuple[str, str]] = set()
    contextual_edges: set[tuple[str, str]] = set()
    candidates: list[LinkCandidate] = []

    for page in pages:
        source = normalize_url(page.final_url)
        occurrences = page.link_occurrences or page.internal_links
        for link in occurrences:
            target = normalize_url(link.url)
            if target not in by_url or source == target:
                continue
            edges.add((source, target))
            incoming[target].add(source)
            outgoing[source].add(target)
            if link.placement == "content":
                contextual_edges.add((source, target))
                contextual_incoming[target].add(source)
                contextual_outgoing[source].add(target)
            if link.anchor_text.strip().casefold() in GENERIC_ANCHORS:
                candidates.append(LinkCandidate(
                    recommendation_type="weak_anchor", source_url=source,
                    source_title=page.title or source, target_url=target,
                    target_title=by_url[target].title or target, current_anchor=link.anchor_text.strip(),
                    section_heading=link.section_heading, context_snippet=link.context_text,
                    topical_score=similarity(page, by_url[target]),
                    target_importance=20 if target in important else 10 if page_role(target) == "commercial" else 0,
                    source_is_contextual=link.placement == "content",
                ))

    home = normalize_url(crawl.origin + "/")
    summary: list[PageLinkSummary] = []
    missing_pairs: set[tuple[str, str, str]] = set()
    for target_url, target in by_url.items():
        inbound = len(incoming[target_url])
        is_important = target_url in important or page_role(target_url) == "commercial"
        if target_url == home:
            orphan_status = "not_orphan"
        elif inbound == 0:
            orphan_status = (
                "confirmed"
                if crawl.coverage_complete and target_url in sitemap_inventory
                else "candidate"
            )
        else:
            orphan_status = "not_orphan"
        summary.append(PageLinkSummary(
            url=target_url, title=target.title or target_url, depth=target.depth,
            page_role=page_role(target_url), inbound_sources=inbound,
            contextual_inbound_sources=len(contextual_incoming[target_url]),
            outbound_targets=len(outgoing[target_url]),
            contextual_outbound_targets=len(contextual_outgoing[target_url]),
            important=is_important, orphan_status=orphan_status,
        ))

        kind: str | None = None
        if orphan_status == "confirmed":
            kind = "orphan"
        elif orphan_status == "candidate":
            kind = "orphan_candidate"
        elif is_important and len(contextual_incoming[target_url]) <= 1:
            kind = "underlinked_important"
        if kind:
            sources = sorted(
                (p for p in pages if normalize_url(p.final_url) != target_url and (normalize_url(p.final_url), target_url) not in edges),
                key=lambda p: similarity(p, target), reverse=True,
            )
            for source in sources[:3]:
                score = similarity(source, target)
                if score < 0.05 and kind == "underlinked_important":
                    continue
                source_url = normalize_url(source.final_url)
                heading, snippet = _best_section(source, target)
                key = (source_url, target_url, kind)
                if key in missing_pairs:
                    continue
                missing_pairs.add(key)
                candidates.append(LinkCandidate(
                    recommendation_type=kind, source_url=source_url,
                    source_title=source.title or source_url, target_url=target_url,
                    target_title=target.title or target_url, section_heading=heading,
                    context_snippet=snippet, topical_score=score,
                    target_importance=20 if is_important else 0, source_is_contextual=True,
                ))

    # Add a small set of strong, presently missing contextual relationships.
    possible = []
    for source_url, source in by_url.items():
        for target_url, target in by_url.items():
            if source_url == target_url or (source_url, target_url) in edges:
                continue
            score = similarity(source, target)
            if score >= 0.18:
                possible.append((score, source_url, source, target_url, target))
    for score, source_url, source, target_url, target in sorted(possible, reverse=True)[:10]:
        if any(c.source_url == source_url and c.target_url == target_url for c in candidates):
            continue
        heading, snippet = _best_section(source, target)
        candidates.append(LinkCandidate(
            recommendation_type="contextual_gap", source_url=source_url,
            source_title=source.title or source_url, target_url=target_url,
            target_title=target.title or target_url, section_heading=heading,
            context_snippet=snippet, topical_score=score,
            target_importance=20 if target_url in important else 10 if page_role(target_url) == "commercial" else 0,
            source_is_contextual=True,
        ))

    # Keep one weak-anchor observation per source/target/current-anchor.
    deduped: dict[tuple[str, str, str, str], LinkCandidate] = {}
    for candidate in candidates:
        key = (candidate.recommendation_type, candidate.source_url, candidate.target_url, candidate.current_anchor or "")
        deduped.setdefault(key, candidate)
    candidates = sorted(
        deduped.values(),
        key=lambda c: (_base_score(c.recommendation_type) + c.target_importance + round(c.topical_score * 20)),
        reverse=True,
    )[:30]
    return AnalysisResult(
        candidates=candidates, pages=sorted(summary, key=lambda p: (p.orphan_status == "not_orphan", p.inbound_sources, p.url)),
        observed_edge_count=len(edges), contextual_edge_count=len(contextual_edges),
        confirmed_orphan_count=sum(p.orphan_status == "confirmed" for p in summary),
        orphan_candidate_count=sum(p.orphan_status == "candidate" for p in summary),
        weak_anchor_count=sum(c.recommendation_type == "weak_anchor" for c in candidates),
    )


def _base_score(kind: str) -> int:
    return {"orphan": 45, "orphan_candidate": 38, "underlinked_important": 35, "weak_anchor": 25, "contextual_gap": 20}[kind]


def _fallback_anchor(candidate: LinkCandidate) -> str:
    cleaned = re.sub(r"\s+", " ", candidate.target_title).strip(" -|:")
    if cleaned.casefold() not in GENERIC_ANCHORS and 2 <= len(cleaned) <= 80:
        return cleaned
    path = urlsplit(candidate.target_url).path.strip("/").split("/")[-1].replace("-", " ")
    return path[:80] or "related page"


def compile_recommendations(
    candidates: list[LinkCandidate], refinements: list[LinkRefinement]
) -> list[InternalLinkRecommendation]:
    refined = {item.candidate_id: item for item in refinements}
    results = []
    for candidate in candidates:
        draft = refined.get(candidate.id)
        anchors = []
        for anchor in (draft.anchor_options if draft else []):
            anchor = re.sub(r"\s+", " ", anchor).strip()
            if 2 <= len(anchor) <= 80 and anchor.casefold() not in GENERIC_ANCHORS:
                anchors.append(anchor)
        fallback = _fallback_anchor(candidate)
        if not anchors:
            anchors = [fallback]
        anchors = list(dict.fromkeys(anchors))[:3]
        score = min(100, _base_score(candidate.recommendation_type) + candidate.target_importance + round(candidate.topical_score * 20) + (5 if candidate.section_heading else 0))
        tier = "critical" if score >= 70 else "important" if score >= 45 else "opportunity"
        confidence = "high" if candidate.topical_score >= 0.25 and candidate.recommendation_type != "orphan_candidate" else "medium" if candidate.topical_score >= 0.08 else "low"
        reason = draft.reasoning if draft else f"The source and target share topical signals, but no useful contextual link was observed in the crawl."
        note = draft.placement_note if draft else (
            f"Add the link naturally in the section '{candidate.section_heading}'." if candidate.section_heading else "Add the link in relevant body copy after confirming it helps the reader."
        )
        evidence = [f"Observed source: {candidate.source_url}", f"Observed target: {candidate.target_url}"]
        if candidate.current_anchor:
            evidence.append(f"Current anchor: {candidate.current_anchor}")
        if candidate.context_snippet:
            evidence.append(f"Source excerpt: {candidate.context_snippet}")
        factors = [f"{candidate.recommendation_type.replace('_', ' ')} base: {_base_score(candidate.recommendation_type)}", f"topical match: +{round(candidate.topical_score * 20)}"]
        if candidate.target_importance:
            factors.append(f"target importance: +{candidate.target_importance}")
        if candidate.section_heading:
            factors.append("section-level placement evidence: +5")
        results.append(InternalLinkRecommendation(
            id=candidate.id, recommendation_type=candidate.recommendation_type,
            priority_score=score, priority_tier=tier, confidence=confidence,
            source_url=candidate.source_url, source_title=candidate.source_title,
            target_url=candidate.target_url, target_title=candidate.target_title,
            current_anchor=candidate.current_anchor, anchor_options=anchors,
            placement_heading=candidate.section_heading, placement_snippet=candidate.context_snippet,
            placement_note=note, reasoning=reason, evidence=evidence, score_factors=factors,
        ))
    return sorted(results, key=lambda item: item.priority_score, reverse=True)[:20]
