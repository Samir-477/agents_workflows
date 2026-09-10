from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from seo_audit.models import ContentSection, HeadingRecord, ImageEvidence, JsonLdErrorDetail, LinkRecord, PageRecord


WHITESPACE = re.compile(r"\s+")
NON_CONTENT_CONTAINERS = {"header", "nav", "footer", "aside"}


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
    open_graph_tag = soup.find("meta", attrs={"property": lambda value: value and value.lower() == "og:title"})
    open_graph_title = clean_text(str(open_graph_tag.get("content", "")) if open_graph_tag else None)

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
    ordered_headings = [
        HeadingRecord(level=tag.name, text=text)
        for tag in soup.find_all(["h1", "h2", "h3"])
        if (text := clean_text(tag.get_text(" ", strip=True)))
    ]

    scope = urlsplit(scope_origin)
    links: list[LinkRecord] = []
    external_links: list[LinkRecord] = []
    link_occurrences: list[LinkRecord] = []
    seen_links: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        raw_url = urljoin(final_url, str(anchor["href"]).strip())
        parsed_raw = urlsplit(raw_url)
        if parsed_raw.scheme not in {"http", "https"} or not parsed_raw.hostname:
            continue
        url = urlunsplit((parsed_raw.scheme.lower(), parsed_raw.netloc.lower(), parsed_raw.path or "/", parsed_raw.query, ""))
        parsed = urlsplit(url)
        container = anchor.find_parent(["nav", "header", "footer", "aside", "main", "article"])
        container_name = container.name if container else None
        if container_name in {"nav", "header", "aside"}:
            placement = "navigation"
        elif container_name == "footer":
            placement = "footer"
        elif container_name in {"main", "article"} or anchor.find_parent(["p", "li"]):
            placement = "content"
        else:
            placement = "other"
        context_container = anchor.find_parent(["p", "li"])
        context_text = clean_text(context_container.get_text(" ", strip=True)) if context_container else None
        previous_heading = anchor.find_previous(["h1", "h2", "h3"])
        section_heading = clean_text(previous_heading.get_text(" ", strip=True)) if previous_heading else None
        record = LinkRecord(
            url=url,
            anchor_text=clean_text(anchor.get_text(" ", strip=True)) or "",
            placement=placement,
            section_heading=section_heading,
            context_text=context_text[:500] if context_text else None,
        )
        if parsed.scheme != scope.scheme or parsed.netloc.lower() != scope.netloc.lower():
            external_links.append(record)
            continue
        discovered_url = canonicalize_discovered_url(final_url, str(anchor["href"]))
        if not discovered_url:
            continue
        record = record.model_copy(update={"url": discovered_url})
        link_occurrences.append(record)
        if url not in seen_links:
            seen_links.add(url)
            links.append(record)

    images = soup.find_all("img")
    reviewed_images = []
    excluded_images = 0
    missing_alt = 0
    empty_alt = 0
    generic_alt = 0
    image_evidence: list[ImageEvidence] = []
    def retain_image_evidence(issue: str) -> bool:
        return sum(item.issue == issue for item in image_evidence) < 5

    for image in images:
        src = str(image.get("src") or image.get("data-src") or "").strip() or None
        src = urljoin(final_url, src) if src else None
        if _is_non_content_image(image, src):
            excluded_images += 1
            continue
        reviewed_images.append(image)
        if not image.has_attr("alt"):
            missing_alt += 1
            if retain_image_evidence("missing_alt"):
                image_evidence.append(ImageEvidence(src=src, alt=None, issue="missing_alt"))
            continue
        alt = clean_text(str(image.get("alt", "")))
        if not alt:
            empty_alt += 1
            if retain_image_evidence("empty_alt"):
                image_evidence.append(ImageEvidence(src=src, alt="", issue="empty_alt"))
        elif _is_generic_alt(alt):
            generic_alt += 1
            if retain_image_evidence("generic_alt"):
                image_evidence.append(ImageEvidence(src=src, alt=alt, issue="generic_alt"))

    schema_types: list[str] = []
    schema_names: list[str] = []
    json_ld_errors: list[str] = []
    json_ld_error_details: list[JsonLdErrorDetail] = []
    for index, script in enumerate(soup.find_all("script", attrs={"type": "application/ld+json"}), start=1):
        raw = script.string or script.get_text()
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            message = f"JSON-LD block {index} could not be parsed."
            json_ld_errors.append(message)
            detail = str(exc) if isinstance(exc, json.JSONDecodeError) else "The block did not contain valid JSON text."
            source = str(raw or "")
            if isinstance(exc, json.JSONDecodeError):
                start = max(0, exc.pos - 220)
                end = min(len(source), exc.pos + 220)
                excerpt = source[start:end].strip()
                if start:
                    excerpt = "..." + excerpt
                if end < len(source):
                    excerpt += "..."
                correction_start = max(0, exc.pos - 90)
                correction_end = min(len(source), exc.pos + 90)
                original_context = source[correction_start:correction_end]
                invalid_character = source[exc.pos:exc.pos + 1]
                escaped_character = json.dumps(invalid_character, ensure_ascii=False)[1:-1] if invalid_character else ""
                corrected_context = original_context[:exc.pos - correction_start] + escaped_character + original_context[exc.pos - correction_start + len(invalid_character):]
                corrected_excerpt = "BEFORE\n" + original_context + "\n\nAFTER\n" + corrected_context
            else:
                excerpt = WHITESPACE.sub(" ", source).strip()[:500]
                corrected_excerpt = None
            json_ld_error_details.append(JsonLdErrorDetail(block=index, message=detail, excerpt=excerpt, corrected_excerpt=corrected_excerpt))
            continue
        schema_types.extend(_collect_schema_types(payload))
        schema_names.extend(_collect_lodging_names(payload))

    content_sections: list[ContentSection] = []
    active_heading: str | None = None
    seen_section_text: set[str] = set()
    total_section_characters = 0
    semantic_roots = soup.find_all(["main", "article"])
    content_root = max(
        semantic_roots,
        key=lambda node: len(clean_text(node.get_text(" ", strip=True)) or ""),
        default=None,
    )
    body_root = soup.body or soup
    if content_root is None or len(clean_text(content_root.get_text(" ", strip=True)) or "") < 120:
        content_root = body_root
    for tag in content_root.find_all(["h1", "h2", "h3", "p", "li"]):
        if tag.find_parent(list(NON_CONTENT_CONTAINERS)):
            continue
        text = clean_text(tag.get_text(" ", strip=True))
        if not text:
            continue
        if tag.name in {"h1", "h2", "h3"}:
            active_heading = text[:240]
            continue
        normalized = text.casefold()
        if normalized in seen_section_text or len(text) < 35:
            continue
        clipped = text[:700]
        content_sections.append(ContentSection(heading=active_heading, text=clipped))
        seen_section_text.add(normalized)
        total_section_characters += len(clipped)
        if len(content_sections) >= 40 or total_section_characters >= 12_000:
            break

    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()
    visible_text = clean_text(soup.get_text(" ", strip=True)) or ""
    semantic_roots = soup.find_all(["main", "article"])
    main_root = max(
        semantic_roots,
        key=lambda node: len(clean_text(node.get_text(" ", strip=True)) or ""),
        default=None,
    )
    body_root = soup.body or soup
    if main_root is None or len(clean_text(main_root.get_text(" ", strip=True)) or "") < 120:
        main_root = body_root
    full_main_text = clean_text(main_root.get_text(" ", strip=True)) or ""
    main_text_limit = 20_000
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
        headings=ordered_headings,
        word_count=len(words),
        internal_links=links,
        external_links=external_links,
        link_occurrences=link_occurrences,
        content_sections=content_sections,
        main_text=full_main_text[:main_text_limit],
        main_text_truncated=len(full_main_text) > main_text_limit,
        images_total=len(reviewed_images),
        images_excluded_from_alt_review=excluded_images,
        images_missing_alt=missing_alt,
        images_empty_alt=empty_alt,
        images_generic_alt=generic_alt,
        image_evidence=image_evidence,
        schema_types=list(dict.fromkeys(schema_types)),
        schema_names=list(dict.fromkeys(schema_names)),
        open_graph_title=open_graph_title,
        json_ld_errors=json_ld_errors,
        json_ld_error_details=json_ld_error_details,
        has_viewport=soup.find("meta", attrs={"name": "viewport"}) is not None,
        content_hash=hashlib.sha256(visible_text.lower().encode("utf-8")).hexdigest()
        if visible_text
        else None,
        content_simhash=str(simhash(visible_text)) if words else None,
    )


# Alt text that is technically present but tells a reader or a machine nothing.
_GENERIC_ALT_WORDS = {
    "alt", "background", "banner", "gallery image", "graphic", "icon", "image",
    "img", "logo", "photo", "picture", "placeholder", "thumbnail",
}
_FILENAME_ALT = re.compile(r"^[\w\-. ]+\.(?:jpe?g|png|gif|webp|svg|avif)$", re.IGNORECASE)
_NUMBERED_ALT = re.compile(r"^(?:image|img|photo|picture|slide|banner|gallery)[\s_-]*\d+$", re.IGNORECASE)
_TRACKING_IMAGE = re.compile(r"(?:facebook\.com/tr(?:[/?]|$)|google-analytics|doubleclick|analytics|tracking[-_/]?pixel|pixel\.gif)", re.IGNORECASE)


def _is_non_content_image(image, src: str | None) -> bool:
    """Exclude analytics pixels and other non-visible instrumentation from alt checks."""
    if image.find_parent("noscript") is not None or (src and _TRACKING_IMAGE.search(src)):
        return True
    def dimension(name):
        match = re.search(r"\d+", str(image.get(name) or ""))
        return int(match.group()) if match else None
    width, height = dimension("width"), dimension("height")
    return width is not None and height is not None and width <= 2 and height <= 2


def _is_generic_alt(alt: str) -> bool:
    normalized = alt.strip().casefold()
    return (
        normalized in _GENERIC_ALT_WORDS
        or bool(_FILENAME_ALT.match(alt.strip()))
        or bool(_NUMBERED_ALT.match(alt.strip()))
    )


def simhash(text: str, bits: int = 64) -> int:
    """A 64-bit SimHash over word trigrams.

    Near-identical pages produce hashes within a few bits of each other, which is what
    templated location pages need: an exact hash misses them because a swapped place
    name changes every byte-level digest.
    """
    words = re.findall(r"[a-z0-9]+", text.casefold())
    if len(words) < 3:
        return 0
    vector = [0] * bits
    for index in range(len(words) - 2):
        shingle = " ".join(words[index : index + 3])
        digest = int.from_bytes(
            hashlib.blake2b(shingle.encode("utf-8"), digest_size=8).digest(), "big"
        )
        for bit in range(bits):
            vector[bit] += 1 if digest >> bit & 1 else -1
    result = 0
    for bit in range(bits):
        if vector[bit] > 0:
            result |= 1 << bit
    return result


def simhash_distance(left: str | None, right: str | None) -> int | None:
    """Hamming distance between two stored SimHash values, or None if unavailable."""
    if not left or not right:
        return None
    try:
        return bin(int(left) ^ int(right)).count("1")
    except ValueError:
        return None


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


def _collect_lodging_names(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        raw_type = value.get("@type")
        types = [raw_type] if isinstance(raw_type, str) else raw_type if isinstance(raw_type, list) else []
        name = clean_text(str(value.get("name", "")))
        if name and any(str(item).casefold() in {"lodgingbusiness", "hotel", "resort"} for item in types):
            yield name
        for child in value.values():
            yield from _collect_lodging_names(child)
    elif isinstance(value, list):
        for child in value:
            yield from _collect_lodging_names(child)
