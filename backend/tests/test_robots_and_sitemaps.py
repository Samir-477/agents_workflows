"""Regression tests for defects found auditing a real site (sterlingholidays.com).

Each case here is a shape that appeared on a live site and that the previous
implementation got wrong.
"""

from __future__ import annotations

from agent_runtime.claims import unsupported_claims
from seo_audit.crawler import _parse_sitemap
from seo_audit.robots import RobotsPolicy

UA = "SEO-AEO-Audit-Agent/0.1 (+read-only audit)"

# Shortened from the real file. The blank line after `User-agent: *` is the point:
# RFC 9309 keeps the group open across it, but Python's stdlib parser ends the record
# there and silently drops every rule that follows.
REAL_WORLD_ROBOTS = """User-agent: *

# Block ads and config files
Disallow: /ads.txt

# Block policy and terms pages
Disallow: /privacy-policy

# Block additional promotional pages
Disallow: /sterling-mice-2023

# Sitemap location
Sitemap: https://example.com/sitemap-index.xml
"""


def test_blank_line_does_not_end_a_robots_group():
    policy = RobotsPolicy.parse(REAL_WORLD_ROBOTS)
    assert policy.declared is True
    for blocked in ("/ads.txt", "/privacy-policy", "/sterling-mice-2023"):
        assert policy.can_fetch(f"https://example.com{blocked}", UA) is False, blocked
    assert policy.can_fetch("https://example.com/bookings", UA) is True


def test_named_ai_crawler_rules_are_read_from_their_own_group():
    policy = RobotsPolicy.parse(
        "User-agent: *\nAllow: /\n\nUser-agent: GPTBot\n\nDisallow: /\n"
    )
    assert policy.can_fetch("https://example.com/guide", "GPTBot") is False
    assert policy.can_fetch("https://example.com/guide", "ClaudeBot") is True


def test_absent_or_unparseable_robots_permits_the_crawl():
    assert RobotsPolicy.parse(None).can_fetch("https://example.com/", UA) is True
    assert RobotsPolicy.parse(None).declared is False


def test_declared_sitemaps_are_read_from_the_policy():
    assert RobotsPolicy.parse(REAL_WORLD_ROBOTS).sitemaps() == [
        "https://example.com/sitemap-index.xml"
    ]


SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/resorts-sitemap.xml</loc></sitemap>
  <sitemap><loc>https://example.com/destinations-sitemap.xml</loc></sitemap>
</sitemapindex>
"""

URL_SET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/resorts-hotels/goa-varca</loc></url>
  <url><loc>https://example.com/resorts-hotels/mussoorie</loc></url>
  <url><loc>https://other.example.net/off-origin</loc></url>
</urlset>
"""


def test_sitemap_index_yields_child_sitemaps_not_pages():
    pages, children = _parse_sitemap(
        SITEMAP_INDEX, "https://example.com/sitemap-index.xml", "https://example.com"
    )
    assert pages == []
    assert children == [
        "https://example.com/resorts-sitemap.xml",
        "https://example.com/destinations-sitemap.xml",
    ]


def test_url_set_yields_pages_and_stays_on_origin():
    pages, children = _parse_sitemap(
        URL_SET, "https://example.com/resorts-sitemap.xml", "https://example.com"
    )
    assert pages == [
        "https://example.com/resorts-hotels/goa-varca",
        "https://example.com/resorts-hotels/mussoorie",
    ]
    assert children == []


def test_unsupported_value_claims_are_detected_against_the_supplied_source():
    source = "Sterling Goa Varca. Services: accommodation, dining, spa. Area: Varca, Goa."
    generated = (
        "Luxury accommodation and premium spa at Sterling Goa Varca. "
        "Known for its serene environment."
    )
    found = unsupported_claims(generated, source)
    assert "luxury" in found
    assert "premium" in found
    assert "known for" in found


def test_claims_the_user_supplied_are_not_reported():
    source = "We are a luxury resort offering premium spa treatments."
    generated = "Luxury accommodation and premium spa services."
    assert unsupported_claims(generated, source) == []
