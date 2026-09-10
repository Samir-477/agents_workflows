"""Turn one resort page URL into the inputs the other nine agents actually need.

Every derivation here stays literal on purpose: the keyword comes from the URL's
own slug, and the "facts" text handed to the prompt-first agents (Metadata, Schema,
Local SEO) is built only from text the crawler actually extracted from the live
page. Those agents already reject anything not grounded in their supplied source
text, so feeding them real scraped text keeps that guarantee intact automatically —
this module does not invent a single fact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from seo_audit.config import Settings
from seo_audit.crawler import SiteCrawler
from seo_audit.models import PageRecord
from seo_audit.url_safety import validate_public_target


@dataclass(slots=True)
class PageFacts:
    url: str
    title: str | None
    meta_description: str | None
    h1: list[str]
    h2: list[str]
    body_text: str
    schema_types: list[str]
    json_ld_errors: list[str]
    word_count: int
    images_total: int
    images_missing_alt: int
    images_generic_alt: int
    phone_numbers: list[str]


_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?\d{10}\b")


async def fetch_page_facts(settings: Settings, url: str) -> tuple[PageFacts, list[str]]:
    """Crawl exactly one page and return its extracted facts plus any warnings."""
    target = await validate_public_target(url, allow_private_networks=settings.allow_private_networks)
    crawler = SiteCrawler(settings)
    result = await crawler.crawl("orchestrator-context", target.url, 1)
    if not result.pages or result.pages[0].fetch_error:
        error = result.pages[0].fetch_error if result.pages else "no page returned"
        raise ValueError(f"Could not fetch the resort page: {error}")
    page: PageRecord = result.pages[0]
    body_text = (page.main_text or "")[:8000]
    phones = list(dict.fromkeys(_PHONE_RE.findall(body_text)))
    facts = PageFacts(
        url=page.final_url,
        title=page.title,
        meta_description=page.meta_description,
        h1=list(page.h1),
        h2=list(page.h2),
        body_text=body_text,
        schema_types=list(page.schema_types),
        json_ld_errors=list(page.json_ld_errors),
        word_count=page.word_count,
        images_total=page.images_total,
        images_missing_alt=page.images_missing_alt,
        images_generic_alt=page.images_generic_alt,
        phone_numbers=phones,
    )
    return facts, list(result.warnings)


def derive_keyword_from_url(url: str) -> str:
    """Turn a URL slug into a readable phrase: /resorts-hotels/lake-palace-alleppey -> 'Lake Palace Alleppey'.

    Chosen over the page's own H1 or <title> because slugs are consistently
    name-like across an entire resort catalogue, while H1s range from plain
    property names to marketing taglines that make poor search phrases.
    """
    path = urlsplit(url).path.strip("/")
    if not path:
        return "this resort"
    slug = path.rsplit("/", 1)[-1]
    words = re.split(r"[-_]+", slug)
    words = [w for w in words if w and not w.isdigit()]
    return " ".join(word.capitalize() for word in words) or "this resort"


def build_fact_narrative(facts: PageFacts, keyword: str) -> str:
    """A plain-language paragraph of only what the crawler actually found.

    This is handed to Metadata, Schema and Local SEO as their source text. Every
    one of those agents validates its own output against whatever text it is
    given, so the discipline lives in feeding them only real extracted content —
    never a paraphrase, never an inferred amenity.
    """
    lines = [f"Resort page: {keyword}. Official URL: {facts.url}."]
    if facts.title:
        lines.append(f"Page title: {facts.title}")
    if facts.meta_description:
        lines.append(f"Page description: {facts.meta_description}")
    if facts.h1:
        lines.append("Main heading: " + "; ".join(facts.h1))
    if facts.h2:
        lines.append("Section headings: " + "; ".join(facts.h2[:10]))
    if facts.phone_numbers:
        lines.append("Telephone number shown on the page: " + facts.phone_numbers[0])
    if facts.body_text:
        lines.append("Visible page content: " + facts.body_text)
    lines.append(
        "These are the only facts observed on the live page. Do not add amenities, "
        "ratings, prices, hours, or claims not present in this text."
    )
    return "\n".join(lines)
