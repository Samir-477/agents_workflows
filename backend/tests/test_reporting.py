from seo_audit.models import (
    AuditRecord,
    Confidence,
    Finding,
    PageRecord,
    Severity,
)
from seo_audit.reporting import build_report, render_markdown


def test_site_score_penalty_is_capped_per_rule_and_markdown_is_readable():
    audit = AuditRecord(requested_url="https://example.com/")
    page = PageRecord(
        audit_id=audit.id,
        requested_url=audit.requested_url,
        final_url=audit.requested_url,
        status_code=200,
    )
    findings = [
        Finding(
            audit_id=audit.id,
            rule_id="missing_canonical",
            title="Canonical tag is missing",
            severity=Severity.IMPORTANT,
            confidence=Confidence.HIGH,
            evidence="Missing",
            why_it_matters="Consolidation",
            recommendation="Add one",
            affected_urls=[f"https://example.com/{index}"],
            score=60,
        )
        for index in range(2)
    ]

    report = build_report(audit, [page], findings)
    markdown = render_markdown(report)

    assert report.site_score == 93
    assert "# SEO/AEO Audit Report" in markdown
    assert "Canonical tag is missing" in markdown
