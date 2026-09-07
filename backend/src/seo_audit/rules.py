from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from urllib.parse import urlsplit

from seo_audit.extractor import simhash_distance
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
    "generic_image_alt",
    "thin_content",
    "missing_product_schema",
    "title_too_long",
    "title_too_short",
    "meta_description_too_long",
    "meta_description_too_short",
    "no_structured_data",
    "unrendered_template",
}

# Practical display ranges. Search engines truncate by pixel width rather than a hard
# character count, so these are reported as truncation risk, not as rule violations.
TITLE_RANGE = (30, 60)
DESCRIPTION_RANGE = (70, 160)

# Template syntax that reached the served HTML because it was never interpolated.
UNRENDERED_TEMPLATE = re.compile(r"\{\{[^}]{1,80}\}\}|\$\{[^}]{1,80}\}|<%=[^%]{1,80}%>")

# Two pages within this Hamming distance of each other, out of 64 bits, are treated as
# near-duplicates. Chosen to catch templated pages that differ only by a place name.
NEAR_DUPLICATE_DISTANCE = 6


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
    findings.extend(_near_duplicate_findings(audit_id, pages))
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
        # An error page has no title, H1, canonical or description by nature. Reporting
        # each of those separately buries the one finding that matters behind five that
        # disappear the moment the page is fixed.
        return
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
    elif len(page.title) > TITLE_RANGE[1]:
        yield _finding(
            audit_id,
            "title_too_long",
            "Page title is long enough to be truncated",
            Severity.MINOR,
            Confidence.MEDIUM,
            f"The title is {len(page.title)} characters, above the practical {TITLE_RANGE[1]}-character display range.",
            "A truncated title hides the end of the message in search results, which usually costs clicks.",
            f"Front-load the distinctive words and aim for roughly {TITLE_RANGE[0]}-{TITLE_RANGE[1]} characters.",
            [url],
        )
    elif len(page.title) < TITLE_RANGE[0]:
        yield _finding(
            audit_id,
            "title_too_short",
            "Page title is very short",
            Severity.MINOR,
            Confidence.MEDIUM,
            f"The title is only {len(page.title)} characters.",
            "A very short title leaves available space unused and often omits useful context.",
            "Add the distinguishing detail a searcher needs to tell this page apart from similar ones.",
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
    elif len(page.meta_description) > DESCRIPTION_RANGE[1]:
        yield _finding(
            audit_id,
            "meta_description_too_long",
            "Meta description is long enough to be truncated",
            Severity.MINOR,
            Confidence.MEDIUM,
            f"The description is {len(page.meta_description)} characters, above the practical {DESCRIPTION_RANGE[1]}-character display range.",
            "The end of a long description is usually cut from the search snippet, so any call to action there is lost.",
            f"Put the essential message first and aim for roughly {DESCRIPTION_RANGE[0]}-{DESCRIPTION_RANGE[1]} characters.",
            [url],
        )
    elif len(page.meta_description) < DESCRIPTION_RANGE[0]:
        yield _finding(
            audit_id,
            "meta_description_too_short",
            "Meta description is very short",
            Severity.MINOR,
            Confidence.MEDIUM,
            f"The description is only {len(page.meta_description)} characters.",
            "A very short description wastes snippet space that could answer the searcher's question.",
            "Expand it to describe what the page offers and why it answers the query.",
            [url],
        )
    template_fields = {
        name: value
        for name, value in (
            ("title", page.title),
            ("meta description", page.meta_description),
            ("H1", page.h1[0] if page.h1 else None),
        )
        if value and UNRENDERED_TEMPLATE.search(value)
    }
    if template_fields:
        sample = next(iter(template_fields.items()))
        yield _finding(
            audit_id,
            "unrendered_template",
            "Template placeholder was served instead of real content",
            Severity.CRITICAL,
            Confidence.HIGH,
            f"The {', '.join(template_fields)} still contains an uninterpolated placeholder, for example {sample[0]}: {sample[1][:120]}",
            "The served HTML shows placeholder syntax rather than the real value, so anything reading the page without running its JavaScript sees no usable title or heading. Most crawlers and current AI answer systems read the served HTML.",
            "Render the value on the server, or emit the real text in the HTML and let JavaScript enhance it rather than replace it.",
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
            f"{page.images_missing_alt} of {page.images_total} images have no alt attribute.",
            "Relevant alt text improves accessibility and helps systems understand informative images.",
            "Add concise alt text to informative images; keep decorative images intentionally empty.",
            [url],
        )
    if page.images_empty_alt:
        yield _finding(
            audit_id,
            "empty_image_alt_review",
            "Images with empty alt text need contextual review",
            Severity.MINOR,
            Confidence.LOW,
            f"{page.images_empty_alt} of {page.images_total} images use an empty alt attribute.",
            "Empty alt text is correct for decorative images but hides informative images from screen-reader users and image understanding systems.",
            "Confirm each image is decorative; add concise descriptive alt text only when the image carries information.",
            [url],
        )
    if page.images_generic_alt:
        yield _finding(
            audit_id,
            "generic_image_alt",
            "Alt text is present but says nothing",
            Severity.MINOR,
            Confidence.HIGH,
            f"{page.images_generic_alt} of {page.images_total} images use placeholder alt text such as \"Gallery Image\", \"image\", or a file name.",
            "Placeholder alt text passes an automated presence check while telling a screen-reader user and a search system nothing about the image.",
            "Describe what each informative image actually shows; mark purely decorative images with an empty alt attribute instead.",
            [url],
        )
    if not page.schema_types and (page.word_count or 0) > 0:
        yield _finding(
            audit_id,
            "no_structured_data",
            "Page has no structured data",
            Severity.MINOR,
            Confidence.MEDIUM,
            "No parseable JSON-LD block was found on the page.",
            "Structured data is how a page states plainly what it is and who publishes it. Without it, machines must infer both from prose.",
            "Add JSON-LD that matches the visible content and the page's actual type, starting with the organization identity and the page's primary entity.",
            [url],
        )
    if page.json_ld_errors:
        yield _finding(
            audit_id,
            "invalid_json_ld",
            "JSON-LD could not be parsed",
            Severity.IMPORTANT,
            Confidence.HIGH,
            " ".join(page.json_ld_errors),
            "Invalid JSON-LD cannot reliably communicate the page's entities to search systems.",
            "Correct the JSON syntax, then validate the rendered page and confirm the markup matches visible content.",
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
            urls = groups[str(value).strip().lower()]
            # One page reachable at two requested URLs must not be reported as a
            # duplicate of itself.
            if page.final_url not in urls:
                urls.append(page.final_url)
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


def _near_duplicate_findings(audit_id: str, pages: list[PageRecord]) -> list[Finding]:
    """Group pages whose visible text is near-identical after templating.

    Exact hashing misses the common programmatic-SEO shape, where dozens of pages share
    one template and differ only by a place or product name.
    """
    healthy = [
        page
        for page in pages
        if page.content_simhash
        and not page.fetch_error
        and (page.status_code or 0) < 400
    ]
    exact = {page.content_hash for page in healthy if page.content_hash}
    seen_exact_pairs = len(exact) < len(healthy)
    clusters: list[list[PageRecord]] = []
    assigned: set[str] = set()
    for index, page in enumerate(healthy):
        if page.final_url in assigned:
            continue
        cluster = [page]
        for other in healthy[index + 1 :]:
            if other.final_url in assigned:
                continue
            distance = simhash_distance(page.content_simhash, other.content_simhash)
            if distance is not None and distance <= NEAR_DUPLICATE_DISTANCE:
                cluster.append(other)
                assigned.add(other.final_url)
        if len(cluster) > 1:
            assigned.add(page.final_url)
            clusters.append(cluster)

    findings: list[Finding] = []
    for cluster in clusters:
        urls = [page.final_url for page in cluster]
        # An exactly-identical set is already covered by the duplicate_content rule.
        if seen_exact_pairs and len({page.content_hash for page in cluster}) == 1:
            continue
        findings.append(
            _finding(
                audit_id,
                "near_duplicate_content",
                "Pages share nearly identical content",
                Severity.IMPORTANT,
                Confidence.MEDIUM,
                f"{len(urls)} pages have visible text that matches within {NEAR_DUPLICATE_DISTANCE} bits of a 64-bit similarity fingerprint, which usually means one template with a swapped name.",
                "Sets of near-identical pages compete with each other, spend crawl budget on repetition, and give answer systems no reason to prefer any single page. Large sets of them are a recognized quality risk.",
                "Give each page genuinely distinct, specific content, or consolidate the set into one strong page with the variants either merged or marked noindex.",
                urls,
            )
        )
    return findings


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
