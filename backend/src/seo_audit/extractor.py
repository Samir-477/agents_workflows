from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from seo_audit.models import LinkRecord, PageRecord


WHITESPACE = re.compile(r"\s+")


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = WHITESPACE.sub(" ", value).strip()
    return cleaned or None


def canonicalize_discovered_url(base_url: str, href: str) -> str | None:
    absolute = urljoin(base_url, href.strip())
    parsed = urlsplit(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.query:
        return None
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def extract_page(
    *,
    audit_id: str,
    requested_url: str,
    final_url: str,
    status_code: int,
    content_type: str | None,
    html: str,
    depth: int,
    scope_origin: str,
) -> PageRecord:
    soup = BeautifulSoup(html, "html.parser")
    title = clean_text(soup.title.get_text(" ", strip=True) if soup.title else None)

    description_tag = soup.find(
        "meta", attrs={"name": lambda value: value and value.lower() == "description"}
    )
    meta_description = clean_text(
        str(description_tag.get("content", "")) if description_tag else None
    )

    canonical_tag = soup.find(
        "link",
        rel=lambda value: value
        and "canonical" in [item.lower() for item in (value if isinstance(value, list) else [value])],
    )
    canonical = None
    if canonical_tag and canonical_tag.get("href"):
        canonical = urljoin(final_url, str(canonical_tag["href"]).strip())

    robots_directives: list[str] = []
    for tag in soup.find_all(
        "meta", attrs={"name": lambda value: value and value.lower() in {"robots", "googlebot"}}
    ):
        robots_directives.extend(
            directive.strip().lower()
            for directive in str(tag.get("content", "")).split(",")
            if directive.strip()
        )
    robots_directives = list(dict.fromkeys(robots_directives))

    headings = {
        name: [
            text
            for tag in soup.find_all(name)
            if (text := clean_text(tag.get_text(" ", strip=True)))
        ]
        for name in ("h1", "h2")
    }

    scope = urlsplit(scope_origin)
    links: list[LinkRecord] = []
    seen_links: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        url = canonicalize_discovered_url(final_url, str(anchor["href"]))
        if not url or url in seen_links:
            continue
        parsed = urlsplit(url)
        if parsed.scheme != scope.scheme or parsed.netloc.lower() != scope.netloc.lower():
            continue
        seen_links.add(url)
        links.append(
            LinkRecord(
                url=url,
                anchor_text=clean_text(anchor.get_text(" ", strip=True)) or "",
            )
        )

    images = soup.find_all("img")
    missing_alt = sum(
        1 for image in images if not clean_text(str(image.get("alt", "")))
    )

    schema_types: list[str] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        schema_types.extend(_collect_schema_types(payload))

    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    visible_text = clean_text(soup.get_text(" ", strip=True)) or ""
    words = visible_text.split()

    return PageRecord(
        audit_id=audit_id,
        requested_url=requested_url,
        final_url=final_url,
        status_code=status_code,
        depth=depth,
        content_type=content_type,
        title=title,
        meta_description=meta_description,
        canonical=canonical,
        robots_directives=robots_directives,
        h1=headings["h1"],
        h2=headings["h2"],
        word_count=len(words),
        internal_links=links,
        images_total=len(images),
        images_missing_alt=missing_alt,
        schema_types=list(dict.fromkeys(schema_types)),
        has_viewport=soup.find("meta", attrs={"name": "viewport"}) is not None,
        content_hash=hashlib.sha256(visible_text.lower().encode("utf-8")).hexdigest()
        if visible_text
        else None,
    )


def _collect_schema_types(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        schema_type = value.get("@type")
        if isinstance(schema_type, str):
            yield schema_type
        elif isinstance(schema_type, list):
            yield from (item for item in schema_type if isinstance(item, str))
        for child in value.values():
            yield from _collect_schema_types(child)
    elif isinstance(value, list):
        for child in value:
            yield from _collect_schema_types(child)
