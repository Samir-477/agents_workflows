from __future__ import annotations

import re
from collections import defaultdict
from urllib.robotparser import RobotFileParser

from ai_visibility.models import (
    BotPolicy, DimensionScore, PageVisibilitySummary, VisibilityFinding,
    VisibilityRecord, VisibilityResult,
)
from seo_audit.crawler import CrawlResult


BOTS = ("GPTBot", "ChatGPT-User", "PerplexityBot", "ClaudeBot")
WEIGHTS = {"discoverability": 0.35, "machine_readability": 0.25, "entity_clarity": 0.20, "citability": 0.20}
SEVERITY_POINTS = {"critical": 30, "important": 16, "opportunity": 7}


def _finding(dimension, severity, title, observation, why, recommendation, urls, evidence, confidence="high"):
    base = {"critical": 90, "important": 65, "opportunity": 38}[severity]
    return VisibilityFinding(
        dimension=dimension, severity=severity, confidence=confidence, title=title,
        observation=observation, why_it_matters=why, recommendation=recommendation,
        affected_urls=urls[:20], evidence=evidence[:10],
        priority_score=min(100, base + min(10, len(urls))),
    )


def _bot_policies(crawl: CrawlResult, target_url: str) -> list[BotPolicy]:
    if not crawl.robots_txt:
        return [BotPolicy(user_agent=bot, status="not_declared", evidence="No readable robots.txt policy was observed.") for bot in BOTS]
    parser = RobotFileParser()
    parser.parse(crawl.robots_txt.splitlines())
    return [BotPolicy(
        user_agent=bot,
        status="allowed" if parser.can_fetch(bot, target_url) else "blocked",
        evidence=f"robots.txt {'allows' if parser.can_fetch(bot, target_url) else 'disallows'} {bot} at the audited path.",
    ) for bot in BOTS]


def analyze_visibility(crawl: CrawlResult, run: VisibilityRecord) -> VisibilityResult:
    findings: list[VisibilityFinding] = []
    policies = _bot_policies(crawl, run.requested_url)
    blocked = [policy.user_agent for policy in policies if policy.status == "blocked"]
    if blocked:
        findings.append(_finding(
            "discoverability", "critical", "AI user-agent rules block the audited path",
            f"robots.txt disallows {', '.join(blocked)} at the audited URL.",
            "A declared block can prevent those user agents from fetching this path; it does not prove how any answer product will source your brand.",
            "Review the robots.txt groups intentionally. Allow only the crawlers that match your policy, then re-run the audit.",
            [run.requested_url], [policy.evidence for policy in policies if policy.status == "blocked"],
        ))

    valid_pages = [page for page in crawl.pages if not page.fetch_error and page.status_code == 200]
    failed = [page for page in crawl.pages if page.fetch_error or page.status_code != 200]
    if failed:
        findings.append(_finding(
            "discoverability", "critical", "Pages could not be fetched cleanly",
            f"{len(failed)} crawled page(s) returned an error or non-200 response.",
            "Content that is not retrievable cannot be reliably parsed or quoted.",
            "Resolve the response errors and verify the pages return stable HTML with HTTP 200.",
            [p.final_url for p in failed], [f"{p.final_url}: {p.fetch_error or 'HTTP ' + str(p.status_code)}" for p in failed],
        ))
    noindex = [p for p in valid_pages if "noindex" in p.robots_directives]
    if noindex:
        findings.append(_finding(
            "discoverability", "important", "Pages declare noindex",
            f"{len(noindex)} page(s) include a noindex directive.",
            "Noindex is a strong search exclusion signal and may conflict with visibility goals.",
            "Confirm the directive is intentional on every affected page and remove it from pages meant to be discovered.",
            [p.final_url for p in noindex], [f"{p.final_url}: robots directives {', '.join(p.robots_directives)}" for p in noindex],
        ))

    missing_structure = [p for p in valid_pages if not p.title or len(p.h1) != 1]
    if missing_structure:
        findings.append(_finding(
            "machine_readability", "important", "Core document structure is incomplete",
            f"{len(missing_structure)} page(s) lack a title or a single clear H1.",
            "Explicit titles and heading hierarchy help machines identify the subject and main content.",
            "Give each page a specific title and one descriptive H1 that agree on the page topic.",
            [p.final_url for p in missing_structure], [f"{p.final_url}: title={bool(p.title)}, H1 count={len(p.h1)}" for p in missing_structure],
        ))
    missing_schema = [p for p in valid_pages if not p.schema_types]
    if missing_schema:
        findings.append(_finding(
            "machine_readability", "opportunity", "No structured data was observed",
            f"{len(missing_schema)} page(s) contained no recognized JSON-LD schema types.",
            "Accurate structured data can make the page's entities and content type less ambiguous, but it does not guarantee citation.",
            "Add only schema that truthfully matches visible content, starting with the organization and primary page types.",
            [p.final_url for p in missing_schema], [f"{p.final_url}: schema types=[]" for p in missing_schema], confidence="medium",
        ))

    context_names = [name for name in (run.business_name, run.product_name) if name]
    if context_names and valid_pages:
        for name in context_names:
            absent = []
            for page in valid_pages:
                text = " ".join([page.title or "", *page.h1, *(s.text for s in page.content_sections)]).casefold()
                if name.casefold() not in text:
                    absent.append(page)
            if absent:
                findings.append(_finding(
                    "entity_clarity", "opportunity", f"Provided entity name is absent from key page copy",
                    f"'{name}' was not found in the extracted text of {len(absent)} page(s).",
                    "Consistent, explicit naming reduces ambiguity about who provides the product or information.",
                    "Where contextually appropriate, use the canonical name in visible copy and matching structured data.",
                    [p.final_url for p in absent], [f"{p.final_url}: '{name}' not found in extracted visible text" for p in absent], confidence="medium",
                ))
    elif valid_pages:
        org_schema = [p for p in valid_pages if any(t.casefold() in {"organization", "localbusiness"} for t in p.schema_types)]
        if not org_schema:
            findings.append(_finding(
                "entity_clarity", "opportunity", "Organization identity is not explicit in structured data",
                "No Organization or LocalBusiness type was observed in the crawled sample.",
                "A truthful organization entity can connect the site, brand, URL and official identifiers.",
                "Consider an Organization or appropriate subtype on the canonical home/about context, matching visible facts.",
                [valid_pages[0].final_url], ["Observed schema types: " + (", ".join(valid_pages[0].schema_types) or "none")], confidence="medium",
            ))

    thin = [p for p in valid_pages if p.word_count < 250]
    if thin:
        findings.append(_finding(
            "citability", "important", "Key pages provide little extractable text",
            f"{len(thin)} page(s) contain fewer than 250 extracted words.",
            "Very sparse pages often lack self-contained facts or explanations an answer system can quote accurately.",
            "Add concise, factual answers to the buyer questions the page owns; do not pad the page merely to reach a word count.",
            [p.final_url for p in thin], [f"{p.final_url}: {p.word_count} extracted words" for p in thin], confidence="medium",
        ))
    question_counts = {p.final_url: sum(1 for s in p.content_sections if s.heading and re.search(r"\?|^(what|why|how|when|where|who|can|does|is|are)\b", s.heading, re.I) and len(s.text.split()) >= 12) for p in valid_pages}
    no_answers = [p for p in valid_pages if question_counts[p.final_url] == 0 and len(p.h2) > 0]
    if no_answers:
        findings.append(_finding(
            "citability", "opportunity", "No clear question-and-answer sections were detected",
            f"{len(no_answers)} structured page(s) had headings, but no question-led section followed by a substantive answer.",
            "Direct answers are easier to extract accurately than claims buried in broad marketing prose.",
            "Where the page genuinely answers a common question, state the answer in one or two self-contained sentences before adding nuance.",
            [p.final_url for p in no_answers], [f"{p.final_url}: {len(p.h2)} H2s, 0 detected answer sections" for p in no_answers], confidence="low",
        ))

    deductions: dict[str, list[str]] = defaultdict(list)
    scores = {key: 100 for key in WEIGHTS}
    for finding in findings:
        deduction = min(SEVERITY_POINTS[finding.severity], scores[finding.dimension])
        scores[finding.dimension] -= deduction
        deductions[finding.dimension].append(f"-{deduction}: {finding.title}")
    if not valid_pages:
        scores = {key: 0 for key in scores}
    summaries = {
        "discoverability": "Whether the sampled URLs and declared crawler rules permit reliable retrieval.",
        "machine_readability": "Whether HTML structure and structured data make page meaning explicit.",
        "entity_clarity": "Whether the organization and product can be identified consistently from observed signals.",
        "citability": "A heuristic review of concise, structured, self-contained answer readiness.",
    }
    dimensions = [DimensionScore(dimension=key, score=scores[key], summary=summaries[key], deductions=deductions[key]) for key in WEIGHTS]
    overall = round(sum(scores[key] * WEIGHTS[key] for key in WEIGHTS))
    per_url_findings = defaultdict(int)
    for finding in findings:
        for url in finding.affected_urls:
            per_url_findings[url] += 1
    pages = [PageVisibilitySummary(
        url=p.final_url, title=p.title or p.final_url, score=max(0, 100 - per_url_findings[p.final_url] * 12),
        word_count=p.word_count, schema_types=p.schema_types, question_sections=question_counts.get(p.final_url, 0),
        findings=per_url_findings[p.final_url],
    ) for p in valid_pages]
    limitations = [
        "This URL audit measures on-site technical and content signals. It does not measure whether any answer engine currently cites or recommends the brand.",
        "Robots results describe declared user-agent rules at audit time; they do not test every provider's full retrieval pipeline.",
        "Citability and entity-clarity scores are documented heuristics, not guarantees of ranking or citation.",
    ]
    if not crawl.coverage_complete:
        limitations.append("The crawl did not establish complete site coverage, so results describe the sampled pages only.")
    return VisibilityResult(
        audit_id=run.id, requested_url=run.requested_url, normalized_origin=crawl.origin,
        pages_crawled=len(valid_pages), discovered_url_count=max(len(crawl.discovered_urls), len(crawl.pages)),
        coverage_complete=crawl.coverage_complete, overall_score=overall, dimensions=dimensions,
        bot_policies=policies, findings=sorted(findings, key=lambda f: f.priority_score, reverse=True), pages=pages,
        methodology="Weighted score: discoverability 35%, machine readability 25%, entity clarity 20%, citability 20%. Each surfaced rule deducts documented severity points.",
        warnings=list(dict.fromkeys(crawl.warnings)), limitations=limitations,
    )
