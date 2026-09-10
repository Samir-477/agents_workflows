from __future__ import annotations

from dataclasses import asdict
import re
from urllib.parse import urlsplit
from seo_audit.crawler import CrawlResult, SiteCrawler
from seo_audit.models import PageRecord
from resort_orchestrator.context import PageFacts, build_fact_narrative
from diagnosis.models import now


def snapshot(crawl: CrawlResult):
    return {
        "captured_at": now(), "method": "server HTML", "origin": crawl.origin,
        "pages": [p.model_dump(mode="json") for p in crawl.pages],
        "warnings": crawl.warnings, "discovered_urls": crawl.discovered_urls,
        "sitemap_urls": crawl.sitemap_urls, "coverage_complete": crawl.coverage_complete,
        "robots_txt": crawl.robots_txt,
    }


def _legacy_research_query(data, fallback_url: str) -> str:
    """Choose a resort identity from observed page data, with the URL slug as fallback."""
    pages = data.get("pages", [])
    primary = pages[0] if pages else {}
    for heading in primary.get("h1", []):
        cleaned = " ".join(heading.split())
        candidate = re.split(r"\s[|–—]\s|\s+-\s+", cleaned, maxsplit=1)[0].strip()
        if 2 <= len(candidate) <= 100 and len(candidate.split()) <= 12:
            return candidate
    title = " ".join((primary.get("title") or "").split())
    if title:
        candidate = re.split(r"\s[|–—]\s|\s+-\s+", title, maxsplit=1)[0].strip()
        if 2 <= len(candidate) <= 100 and len(candidate.split()) <= 12:
            return candidate
    slug = urlsplit(primary.get("final_url") or fallback_url).path.rstrip("/").rsplit("/", 1)[-1]
    words = [part for part in re.split(r"[-_]+", slug) if part and not part.isdigit()]
    return " ".join(word.capitalize() for word in words) or "Resort"


def derive_resort_identity(data, fallback_url: str) -> dict:
    """Resolve a property name from corroborated signals and reject slogan-like H1s."""
    pages = data.get("pages", [])
    primary = pages[0] if pages else {}
    final_url = primary.get("final_url") or fallback_url
    slug = urlsplit(final_url).path.rstrip("/").rsplit("/", 1)[-1]
    words = [part for part in re.split(r"[-_]+", slug) if part and not part.isdigit()]
    slug_name = " ".join(word.capitalize() for word in words) or "Resort"
    slug_tokens = {item.casefold() for item in words if len(item) > 2}
    title = " ".join((primary.get("title") or "").split())
    og_title = " ".join((primary.get("open_graph_title") or "").split())
    schema_names = [" ".join(str(item).split()) for item in primary.get("schema_names", []) if str(item).strip()]
    page_signals = " ".join([title, og_title, *schema_names, (primary.get("main_text") or "")[:500]])
    brand = "Sterling" if re.search(r"\bsterling\b", page_signals, re.I) else ""
    branded_slug = f"{brand} {slug_name}".strip() if brand and brand.casefold() not in slug_tokens else slug_name
    candidates: list[tuple[int, str, str]] = []
    rejected = []
    for name in schema_names:
        schema_tokens = set(re.findall(r"[a-z0-9]+", name.casefold()))
        overlap = len(slug_tokens & schema_tokens)
        if 2 <= len(name) <= 120 and overlap >= max(1, len(slug_tokens) // 2):
            candidates.append((100, name, "lodging schema name corroborated by URL"))
        elif 2 <= len(name) <= 120:
            rejected.append({"value": name, "reason": "Lodging schema name conflicts with the requested property URL."})
    candidates.append((80 if brand else 65, branded_slug, "URL slug" + (" with observed brand" if brand else "")))
    generic_title = re.compile(r"\b(best|top|family|luxury|hotels?|resorts?|holidays?|booking)\b", re.I)
    for source, value in (("page title", title), ("Open Graph title", og_title)):
        candidate = re.split(r"\s(?:\||-|–|—)\s", value, maxsplit=1)[0].strip()
        overlap = len(slug_tokens & set(re.findall(r"[a-z0-9]+", candidate.casefold())))
        if candidate and overlap >= max(1, len(slug_tokens) // 2) and not generic_title.search(candidate):
            candidates.append((88, candidate, source))
    for heading in primary.get("h1", []):
        cleaned = " ".join(heading.split())
        tokens = set(re.findall(r"[a-z0-9]+", cleaned.casefold()))
        overlap = len(slug_tokens & tokens)
        if overlap >= max(1, len(slug_tokens) // 2) or any(name.casefold() in cleaned.casefold() for name in schema_names):
            # Keep the URL-corroborated property identity, not the promotional
            # phrase that may follow it in the same heading.
            candidate = branded_slug if cleaned.casefold().startswith(branded_slug.casefold()) else cleaned
            candidates.append((90, candidate, "H1 corroborated by identity signals"))
        else:
            rejected.append({"value": cleaned, "reason": "Heading does not match the URL or lodging schema and appears promotional."})
    score, name, source = max(candidates, key=lambda item: (item[0], len(item[1])))
    destination = words[-1].capitalize() if words else ""
    # Lodging schema often contains the official property name but omits the city.
    # Preserve that strong identity while keeping the URL-confirmed destination in
    # the branded research query used by downstream agents.
    branded_query = name
    if destination and destination.casefold() not in name.casefold():
        branded_query = f"{name} {destination}"
    return {
        "property_name": name, "brand": brand or None, "destination": destination or None,
        "confidence": "high" if score >= 80 else "medium", "supporting_sources": [source],
        "rejected_candidates": rejected, "branded_query": branded_query,
        "generic_query": f"resorts in {destination}" if destination else None,
    }


def derive_research_query(data, fallback_url: str) -> str:
    return derive_resort_identity(data, fallback_url)["branded_query"]


class SnapshotCrawler:
    def __init__(self, data, settings):
        self.data = data
        self.live = SiteCrawler(settings)

    async def crawl(self, audit_id, start_url, limit):
        pages = [PageRecord.model_validate(p) for p in self.data["pages"]]
        match = next((p for p in pages if start_url.rstrip("/") in {p.requested_url.rstrip("/"), p.final_url.rstrip("/")}), None)
        if match is None:
            return await self.live.crawl(audit_id, start_url, limit)
        selected = [match] if limit == 1 else [match, *(p for p in pages if p.id != match.id)][:limit]
        return CrawlResult(
            pages=[p.model_copy(update={"audit_id": audit_id}) for p in selected],
            origin=self.data["origin"], warnings=self.data["warnings"],
            discovered_urls=self.data["discovered_urls"], sitemap_urls=self.data["sitemap_urls"],
            coverage_complete=self.data["coverage_complete"] and len(selected) == len(pages),
            robots_txt=self.data["robots_txt"],
        )


def narrative(data):
    p = PageRecord.model_validate(data["pages"][0])
    phone_numbers = list(dict.fromkeys(
        match.strip()
        for match in re.findall(r"(?:\+?\d[\d\s().-]{7,}\d)", p.main_text)
    ))[:10]
    facts = PageFacts(
        url=p.final_url, title=p.title, meta_description=p.meta_description,
        h1=p.h1, h2=p.h2, body_text=p.main_text[:6500], schema_types=p.schema_types,
        json_ld_errors=p.json_ld_errors, word_count=p.word_count,
        images_total=p.images_total, images_missing_alt=p.images_missing_alt,
        images_generic_alt=p.images_generic_alt, phone_numbers=phone_numbers,
    )
    return build_fact_narrative(facts, p.title or p.final_url)
