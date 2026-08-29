from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from urllib.parse import urlsplit

from seo_audit.models import Confidence, Finding, PageRecord, Severity
from seo_audit.page_types import infer_page_type


GROUPED_PAGE_RULES = {
    "missing_title",
    "missing_meta_description",
    "missing_canonical",
    "missing_h1",
    "multiple_h1",
    "missing_viewport",
    "missing_image_alt",
    "thin_content",
    "missing_product_schema",
}


def audit_pages(audit_id: str, pages: list[PageRecord]) -> list[Finding]:
    page_findings: list[Finding] = []
    for page in pages:
        page_findings.extend(_audit_page(audit_id, page))
    findings = _group_repeated_page_findings(page_findings, len(pages))
    findings.extend(_duplicate_findings(audit_id, pages, "title", "duplicate_title"))
    findings.extend(
        _duplicate_findings(
            audit_id, pages, "meta_description", "duplicate_meta_description"
        )
    )
    findings.extend(_duplicate_findings(audit_id, pages, "content_hash", "duplicate_content"))
    findings.extend(_orphan_findings(audit_id, pages))
    return findings


def audit_crawl_limitations(
    audit_id: str,
    requested_url: str,
    warnings: list[str],
) -> list[Finding]:
    if not any("robots.txt disallowed the redirected start URL" in item for item in warnings):
        return []
    return [
        _finding(
            audit_id,
            "audit_blocked_by_robots",
            "Audit coverage was blocked by robots.txt",
            Severity.IMPORTANT,
            Confidence.HIGH,
            "The site's robots.txt policy disallowed this audit user-agent on the redirected start URL.",
            "The agent could not inspect page content, metadata, headings, schema, or internal links. This limitation does not by itself prove that major search-engine crawlers are blocked.",
            "Review the robots policy for intended crawlers or run an authorized audit using an approved crawl source. Do not treat this limited report as a site-health score.",
            [requested_url],
        )
    ]


def _audit_page(audit_id: str, page: PageRecord) -> Iterable[Finding]:
    url = page.final_url
    if page.fetch_error:
        yield _finding(
            audit_id,
            "fetch_failed",
            "Page could not be fetched",
            Severity.CRITICAL,
            Confidence.HIGH,
            f"The crawler could not fetch this URL: {page.fetch_error}",
            "Search systems may encounter the same access problem.",
            "Check DNS, TLS, server availability, bot protection, and redirect behavior.",
            [url],
        )
        return
    if page.status_code is not None and page.status_code >= 400:
        yield _finding(
            audit_id,
            "error_status",
            f"Page returned HTTP {page.status_code}",
            Severity.CRITICAL,
            Confidence.HIGH,
            f"The URL returned HTTP {page.status_code} during the audit.",
            "Broken important pages can disappear from search results and waste internal links.",
            "Restore the page or redirect it to the closest relevant working URL.",
            [url],
        )
    if any(directive in {"noindex", "none"} for directive in page.robots_directives):
        yield _finding(
            audit_id,
            "noindex",
            "Page asks search engines not to index it",
            Severity.CRITICAL,
            Confidence.HIGH,
            f"Robots directives include: {', '.join(page.robots_directives)}.",
            "An important page with noindex is normally excluded from search results.",
            "Remove noindex if the page is intended to appear in search.",
            [url],
        )
    if not page.title:
        yield _finding(
            audit_id,
            "missing_title",
            "Page title is missing",
            Severity.IMPORTANT,
            Confidence.HIGH,
            "No HTML title was found.",
            "The title is a strong description of the page for search systems and users.",
            "Add a unique, descriptive title that matches the page's main purpose.",
            [url],
        )
    if not page.meta_description:
        yield _finding(
            audit_id,
            "missing_meta_description",
            "Meta description is missing",
            Severity.IMPORTANT,
            Confidence.HIGH,
            "No meta description was found.",
            "Search systems may generate a less useful snippet from page content.",
            "Write a concise description that explains the page and supports a useful search snippet.",
            [url],
        )
    if not page.canonical:
        yield _finding(
            audit_id,
            "missing_canonical",
            "Canonical tag is missing",
            Severity.IMPORTANT,
            Confidence.HIGH,
            "No canonical link element was found.",
            "A canonical helps consolidate duplicate URL variants around a preferred page.",
            "Add a self-referencing canonical to the preferred indexable URL.",
            [url],
        )
    if not page.h1:
        yield _finding(
            audit_id,
            "missing_h1",
            "Primary heading is missing",
            Severity.IMPORTANT,
            Confidence.HIGH,
            "No H1 element was found.",
            "The main heading helps visitors and search systems identify the page's primary topic.",
            "Add one descriptive H1 near the beginning of the main content.",
            [url],
        )
    elif len(page.h1) > 1:
        yield _finding(
            audit_id,
            "multiple_h1",
            "Page has multiple primary headings",
            Severity.MINOR,
            Confidence.HIGH,
            f"The page contains {len(page.h1)} H1 elements.",
            "Several primary headings can make the content hierarchy less clear.",
            "Keep one page-level H1 and use H2/H3 elements for subsections.",
            [url],
        )
    if not page.has_viewport:
        yield _finding(
            audit_id,
            "missing_viewport",
            "Mobile viewport configuration is missing",
            Severity.IMPORTANT,
            Confidence.HIGH,
            "No viewport meta element was found.",
            "Mobile browsers may render the page at an unsuitable desktop width.",
            "Add a responsive viewport meta element and verify the page on mobile.",
            [url],
        )
    if infer_page_type(url) == "product" and not any(
        schema_type.lower() == "product" for schema_type in page.schema_types
    ):
        yield _finding(
            audit_id,
            "missing_product_schema",
            "Likely product page has no Product structured data",
            Severity.IMPORTANT,
            Confidence.MEDIUM,
            "The URL pattern suggests a product page, but no Product schema type was detected.",
            "Valid Product markup can help search systems understand product details and eligibility for product experiences.",
            "Add Product JSON-LD that matches the visible name, image, price, availability, and other supported details.",
            [url],
        )
    if page.images_missing_alt:
        yield _finding(
            audit_id,
            "missing_image_alt",
            "Some images have no useful alt text",
            Severity.MINOR,
            Confidence.HIGH,
            f"{page.images_missing_alt} of {page.images_total} images have missing or empty alt attributes.",
            "Relevant alt text improves accessibility and helps systems understand informative images.",
            "Add concise alt text to informative images; keep decorative images intentionally empty.",
            [url],
        )
    if 0 < page.word_count < 200:
        yield _finding(
            audit_id,
            "thin_content",
            "Page has limited visible text",
            Severity.MINOR,
            Confidence.MEDIUM,
            f"Approximately {page.word_count} visible words were found.",
            "A short page may not answer enough of the visitor's question, although some page types are naturally brief.",
            "Confirm the page satisfies its purpose; add useful details, examples, proof, or answers where needed.",
            [url],
        )


def _group_repeated_page_findings(
    findings: list[Finding], page_count: int
) -> list[Finding]:
    grouped: dict[str, list[Finding]] = defaultdict(list)
    untouched: list[Finding] = []
    for finding in findings:
        if finding.rule_id in GROUPED_PAGE_RULES:
            grouped[finding.rule_id].append(finding)
        else:
            untouched.append(finding)

    results = list(untouched)
    for rule_findings in grouped.values():
        if len(rule_findings) == 1:
            results.append(rule_findings[0])
            continue
        first = rule_findings[0]
        affected_urls = list(
            dict.fromkeys(
                url for finding in rule_findings for url in finding.affected_urls
            )
        )
        results.append(
            first.model_copy(
                update={
                    "evidence": (
                        f"This issue was detected on {len(affected_urls)} of "
                        f"{page_count} crawled pages."
                    ),
                    "affected_urls": affected_urls,
                }
            )
        )
    return results


def _duplicate_findings(
    audit_id: str,
    pages: list[PageRecord],
    field_name: str,
    rule_id: str,
) -> list[Finding]:
    groups: dict[str, list[str]] = defaultdict(list)
    for page in pages:
        value = getattr(page, field_name)
        if value and not page.fetch_error and (page.status_code or 0) < 400:
            groups[str(value).strip().lower()].append(page.final_url)
    results: list[Finding] = []
    titles = {
        "duplicate_title": "Multiple pages share the same title",
        "duplicate_meta_description": "Multiple pages share the same meta description",
        "duplicate_content": "Multiple pages have identical visible content",
    }
    recommendations = {
        "duplicate_title": "Give each indexable page a title that describes its unique purpose.",
        "duplicate_meta_description": "Write page-specific descriptions or intentionally omit low-value descriptions.",
        "duplicate_content": "Consolidate duplicates, add a canonical, redirect redundant URLs, or make each page genuinely distinct.",
    }
    for urls in groups.values():
        if len(urls) < 2:
            continue
        results.append(
            _finding(
                audit_id,
                rule_id,
                titles[rule_id],
                Severity.IMPORTANT,
                Confidence.HIGH,
                f"The same {field_name.replace('_', ' ')} was found on {len(urls)} pages.",
                "Duplicate signals make it harder to distinguish the purpose of each page.",
                recommendations[rule_id],
                urls,
            )
        )
    return results


def _orphan_findings(audit_id: str, pages: list[PageRecord]) -> list[Finding]:
    healthy = [
        page
        for page in pages
        if not page.fetch_error and page.status_code is not None and page.status_code < 400
    ]
    if len(healthy) < 2:
        return []
    inbound: dict[str, int] = defaultdict(int)
    for page in healthy:
        for link in page.internal_links:
            inbound[link.url] += 1
    shallowest = min(healthy, key=lambda page: page.depth).final_url
    candidates = [
        page.final_url
        for page in healthy
        if page.final_url != shallowest and inbound[page.final_url] == 0
    ]
    if not candidates:
        return []
    return [
        _finding(
            audit_id,
            "no_internal_inlinks",
            "Pages have no discovered internal links",
            Severity.IMPORTANT,
            Confidence.MEDIUM,
            f"No internal links pointed to {len(candidates)} crawled pages.",
            "Pages without internal links may be difficult for visitors and crawlers to discover in context.",
            "Link to these pages from relevant navigation, category, service, or content pages.",
            candidates,
        )
    ]


def _finding(
    audit_id: str,
    rule_id: str,
    title: str,
    severity: Severity,
    confidence: Confidence,
    evidence: str,
    why_it_matters: str,
    recommendation: str,
    affected_urls: list[str],
) -> Finding:
    return Finding(
        audit_id=audit_id,
        rule_id=rule_id,
        title=title,
        severity=severity,
        confidence=confidence,
        evidence=evidence,
        why_it_matters=why_it_matters,
        recommendation=recommendation,
        affected_urls=affected_urls,
    )
