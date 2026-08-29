from seo_audit.extractor import extract_page
from seo_audit.models import PageRecord, Severity
from seo_audit.rules import audit_pages
from seo_audit.scoring import score_findings


HTML = """
<!doctype html>
<html>
  <head>
    <title>Example Service</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="canonical" href="/service">
    <script type="application/ld+json">
      {"@context": "https://schema.org", "@type": "Service"}
    </script>
  </head>
  <body>
    <a href="/about">About us</a>
    <img src="team.jpg">
    <p>Short service introduction.</p>
  </body>
</html>
"""


def test_extracts_facts_and_rules_are_evidence_backed():
    page = extract_page(
        audit_id="audit-1",
        requested_url="https://example.com/service",
        final_url="https://example.com/service",
        status_code=200,
        content_type="text/html",
        html=HTML,
        depth=0,
        scope_origin="https://example.com",
    )

    assert page.title == "Example Service"
    assert page.canonical == "https://example.com/service"
    assert page.schema_types == ["Service"]
    assert page.internal_links[0].url == "https://example.com/about"
    assert page.images_missing_alt == 1

    findings = audit_pages("audit-1", [page])
    rule_ids = {finding.rule_id for finding in findings}
    assert {"missing_meta_description", "missing_h1", "missing_image_alt"} <= rule_ids
    assert "missing_title" not in rule_ids

    scored = score_findings(findings, ["https://example.com/service"])
    assert scored[0].severity in {Severity.CRITICAL, Severity.IMPORTANT}
    assert scored[0].score > 0


def test_repeated_page_issues_are_grouped_and_product_schema_is_checked():
    pages = [
        PageRecord(
            audit_id="audit-2",
            requested_url=f"https://shop.test/catalogue/book-{index}/index.html",
            final_url=f"https://shop.test/catalogue/book-{index}/index.html",
            status_code=200,
            title=f"Book {index}",
            h1=[f"Book {index}"],
            word_count=300,
            has_viewport=True,
        )
        for index in range(2)
    ]

    findings = audit_pages("audit-2", pages)
    by_rule = {finding.rule_id: finding for finding in findings}

    assert len(by_rule["missing_canonical"].affected_urls) == 2
    assert len(by_rule["missing_meta_description"].affected_urls) == 2
    assert len(by_rule["missing_product_schema"].affected_urls) == 2
    assert "2 of 2 crawled pages" in by_rule["missing_product_schema"].evidence
