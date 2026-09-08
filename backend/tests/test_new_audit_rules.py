"""Rules added after auditing a real site found problems no rule looked for."""

from __future__ import annotations

from seo_audit.extractor import extract_page, simhash, simhash_distance
from seo_audit.rules import audit_pages

ORIGIN = "https://example.com"


def page(url: str, body: str, head: str = "") -> object:
    html = f"<html><head><meta name='viewport' content='width=device-width'>{head}</head><body>{body}</body></html>"
    return extract_page(
        audit_id="audit-1", requested_url=url, final_url=url, status_code=200,
        content_type="text/html", html=html, depth=1, scope_origin=ORIGIN,
    )


def rule_ids(pages) -> set[str]:
    return {finding.rule_id for finding in audit_pages("audit-1", pages)}


def finding(pages, rule_id):
    return next(item for item in audit_pages("audit-1", pages) if item.rule_id == rule_id)


HEAD = (
    "<title>A perfectly reasonable page title for testing</title>"
    "<meta name='description' content='"
    + "A description that comfortably sits inside the practical display range for snippets. " * 1
    + "It reads naturally and ends here.'>"
    "<link rel='canonical' href='https://example.com/a'>"
)
BODY = "<h1>Heading</h1><p>" + ("Real sentence content for the page. " * 60) + "</p>"


def test_unrendered_template_placeholder_in_h1_is_critical():
    # The exact shape found on the audited site: the framework expression reached
    # the served HTML because it was never interpolated.
    pages = [page(f"{ORIGIN}/a", "<h1>{{keyValues.title}}</h1>" + BODY, HEAD)]
    result = finding(pages, "unrendered_template")
    assert result.severity.value == "critical"
    assert "keyValues.title" in result.evidence


def test_real_headings_do_not_trigger_the_template_rule():
    assert "unrendered_template" not in rule_ids([page(f"{ORIGIN}/a", BODY, HEAD)])


def test_placeholder_alt_text_is_reported_separately_from_missing_alt():
    body = (
        "<h1>Gallery</h1>"
        "<img src='1.jpg' alt='Gallery Image'>"
        "<img src='2.jpg' alt='Gallery Image'>"
        "<img src='3.jpg' alt='A guest suite overlooking the courtyard'>"
        + BODY
    )
    result = finding([page(f"{ORIGIN}/a", body, HEAD)], "generic_image_alt")
    assert "2 of 3" in result.evidence
    assert "missing_image_alt" not in rule_ids([page(f"{ORIGIN}/a", body, HEAD)])


def test_file_name_alt_text_counts_as_placeholder():
    body = "<h1>X</h1><img src='a.jpg' alt='hero-banner-2.png'>" + BODY
    assert "generic_image_alt" in rule_ids([page(f"{ORIGIN}/a", body, HEAD)])


def test_empty_alt_is_reviewed_separately_from_a_missing_attribute():
    body = (
        "<h1>Gallery</h1>"
        "<img src='decorative-line.svg' alt=''>"
        "<img src='team.jpg'>"
        + BODY
    )
    extracted = page(f"{ORIGIN}/a", body, HEAD)
    assert extracted.images_empty_alt == 1
    assert extracted.images_missing_alt == 1
    findings = {item.rule_id: item for item in audit_pages("audit-1", [extracted])}
    assert findings["empty_image_alt_review"].confidence.value == "low"
    assert findings["missing_image_alt"].confidence.value == "high"


def test_extraction_retains_ordered_headings_external_links_and_schema_errors():
    body = (
        "<h1>CRM guide</h1><h2>Choose a plan</h2><h3>Compare limits</h3>"
        "<main><p>" + ("Detailed CRM comparison guidance for growing teams. " * 20) + "</p>"
        "<a href='https://source.example/report?year=2026#methods'>Industry report</a></main>"
    )
    head = HEAD + '<script type="application/ld+json">{invalid}</script>'
    extracted = page(f"{ORIGIN}/a", body, head)
    assert [(item.level, item.text) for item in extracted.headings[:3]] == [
        ("h1", "CRM guide"), ("h2", "Choose a plan"), ("h3", "Compare limits")
    ]
    assert extracted.external_links[0].url == "https://source.example/report?year=2026"
    assert extracted.main_text.startswith("Detailed CRM comparison guidance")
    assert extracted.main_text_truncated is False
    assert extracted.json_ld_errors == ["JSON-LD block 1 could not be parsed."]
    assert "invalid_json_ld" in rule_ids([extracted])


def test_extraction_uses_body_when_semantic_main_is_only_a_shell():
    html = """
    <html><body>
      <main>2</main>
      <section>
        <h1>Sterling Kodai Lake</h1>
        <p>This resort guide contains enough visible detail to support a useful content review.</p>
        <p>Travellers can compare rooms, facilities, dining, activities, and the location near the lake.</p>
      </section>
    </body></html>
    """
    extracted = extract_page(
        audit_id="audit", requested_url="https://example.com/resort",
        final_url="https://example.com/resort", status_code=200,
        content_type="text/html", html=html, depth=0,
        scope_origin="https://example.com",
    )
    assert "This resort guide" in extracted.main_text
    assert len(extracted.main_text.split()) > 15


def test_over_long_title_and_description_are_flagged():
    head = (
        "<title>" + "An extremely long page title that will certainly be truncated" * 2 + "</title>"
        "<meta name='description' content='" + "Padding sentence. " * 30 + "'>"
        "<link rel='canonical' href='https://example.com/a'>"
    )
    ids = rule_ids([page(f"{ORIGIN}/a", BODY, head)])
    assert "title_too_long" in ids
    assert "meta_description_too_long" in ids


def test_pages_without_any_json_ld_are_flagged():
    assert "no_structured_data" in rule_ids([page(f"{ORIGIN}/a", BODY, HEAD)])


def test_pages_with_json_ld_are_not_flagged():
    head = HEAD + '<script type="application/ld+json">{"@type":"Organization","name":"X"}</script>'
    assert "no_structured_data" not in rule_ids([page(f"{ORIGIN}/a", BODY, head)])


def test_template_pages_differing_only_by_place_name_are_near_duplicates():
    template = (
        "<h1>Meetings and Events</h1><p>"
        + ("Our venue offers conference space, catering and accommodation for corporate groups. " * 25)
        + "Located in {city}.</p>"
    )
    pages = [
        page(f"{ORIGIN}/events/nainital", template.replace("{city}", "Nainital"), HEAD),
        page(f"{ORIGIN}/events/puri", template.replace("{city}", "Puri"), HEAD),
        page(f"{ORIGIN}/events/kanha", template.replace("{city}", "Kanha"), HEAD),
    ]
    result = finding(pages, "near_duplicate_content")
    assert len(result.affected_urls) == 3
    assert result.severity.value == "important"


def test_genuinely_different_pages_are_not_near_duplicates():
    pages = [
        page(f"{ORIGIN}/a", "<h1>Spa</h1><p>" + ("Treatments, therapists and booking details. " * 25) + "</p>", HEAD),
        page(f"{ORIGIN}/b", "<h1>Golf</h1><p>" + ("Course layout, green fees and tee times. " * 25) + "</p>", HEAD),
    ]
    assert "near_duplicate_content" not in {item.rule_id for item in audit_pages("audit-1", pages)}


def test_one_page_reached_by_two_urls_is_not_a_duplicate_of_itself():
    # The crawler can queue "/x" and "/x/" separately; both resolve to one final URL.
    duplicate = [page(f"{ORIGIN}/a", BODY, HEAD), page(f"{ORIGIN}/a", BODY, HEAD)]
    ids = {item.rule_id for item in audit_pages("audit-1", duplicate)}
    assert "duplicate_title" not in ids
    assert "duplicate_content" not in ids
    assert "near_duplicate_content" not in ids


def test_simhash_distance_separates_similar_from_unrelated_text():
    # The shape that matters: a long templated document where one place name differs.
    body = (
        "our venue provides conference space catering accommodation and audio visual "
        "support for corporate groups of every size throughout the year " * 20
    )
    base = body + " the venue is located in nainital."
    swapped = body + " the venue is located in puri."
    unrelated = (
        "quarterly financial results for the software division were published today "
        "alongside guidance for the coming year " * 20
    )
    assert simhash_distance(str(simhash(base)), str(simhash(swapped))) <= 6
    assert simhash_distance(str(simhash(base)), str(simhash(unrelated))) > 6
    assert simhash_distance(None, str(simhash(base))) is None
