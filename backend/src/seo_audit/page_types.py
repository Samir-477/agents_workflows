from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from urllib.parse import urlsplit


def infer_page_type(url: str) -> str:
    """Return a conservative URL-based page-type hint for crawl sampling and rules."""
    path = urlsplit(url).path.lower()
    segments = [segment for segment in path.split("/") if segment]
    category_markers = {"category", "categories", "collection", "collections"}
    product_markers = {"product", "products", "item", "items"}

    if any(segment in category_markers for segment in segments):
        return "category"
    if any(segment in product_markers for segment in segments):
        return "product"
    # Common catalogue structure: /catalogue/<product-slug>/index.html.
    if "catalogue" in segments and len(segments) >= 2:
        return "product"
    return "other"


def representative_url_order(urls: Iterable[str]) -> list[str]:
    """Interleave likely category, product, and other URLs while preserving local order."""
    buckets: dict[str, deque[str]] = {
        "category": deque(),
        "product": deque(),
        "other": deque(),
    }
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        buckets[infer_page_type(url)].append(url)

    ordered: list[str] = []
    while any(buckets.values()):
        for page_type in ("category", "product", "other"):
            if buckets[page_type]:
                ordered.append(buckets[page_type].popleft())
    return ordered
