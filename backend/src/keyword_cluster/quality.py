from __future__ import annotations

import math
import re
from collections import Counter

from keyword_cluster.models import KeywordItem, SearchIntent


YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
OUTCOME_CLAIM_RE = re.compile(
    r"\b(?:improv(?:e|es|ing)|increase(?:s|d|ing)?|boost(?:s|ed|ing)?|reduce(?:s|d|ing)?)\b"
    r"[^.!?]{0,90}\b(?:rankings?|traffic|conversions?|bounce rates?)\b",
    re.IGNORECASE,
)


def intent_bucket(keyword: str) -> str | None:
    value = f" {keyword.casefold()} "
    if re.search(r"\b(pricing|price|prices|cost|costs|fee|fees|package|packages|how much)\b", value):
        return "pricing"
    if re.search(r"\b(vs|versus|alternative|alternatives|best|top|review|reviews|compare|comparison)\b", value):
        return "comparison"
    if re.search(r"\b(buy|order|book|hire|near me|quote|trial|demo)\b", value):
        return "transactional"
    if re.search(r"\b(how to|guide|tutorial|steps|checklist)\b", value):
        return "how-to"
    if re.search(r"\b(what is|meaning|definition|why|examples?)\b", value):
        return "informational"
    if re.search(r"\b(login|sign in|support|contact)\b", value):
        return "navigational"
    return None


def bucket_intent(bucket: str | None, fallback: SearchIntent) -> SearchIntent:
    if bucket in {"pricing", "comparison"}:
        return "commercial"
    if bucket == "transactional":
        return "transactional"
    if bucket in {"how-to", "informational"}:
        return "informational"
    if bucket == "navigational":
        return "navigational"
    return fallback


def split_on_conflicting_intent(items: list[KeywordItem]) -> list[tuple[str | None, list[KeywordItem]]]:
    """Split a model cluster only when explicit query modifiers materially conflict."""
    buckets: dict[str, list[KeywordItem]] = {}
    neutral: list[KeywordItem] = []
    for item in items:
        bucket = intent_bucket(item.keyword)
        if bucket is None:
            neutral.append(item)
        else:
            buckets.setdefault(bucket, []).append(item)
    if len(buckets) < 2:
        return [(next(iter(buckets), None), items)]

    # Explicit modifiers such as "pricing" and "how to" describe different
    # page jobs. Neutral variants stay with the largest explicit group.
    largest = max(buckets, key=lambda key: len(buckets[key]))
    buckets[largest].extend(neutral)
    return [(bucket, members) for bucket, members in buckets.items() if members]


def sanitize_title(title: str, source_keywords: list[str]) -> tuple[str, bool]:
    allowed_years = {match.group(0) for keyword in source_keywords for match in YEAR_RE.finditer(keyword)}
    changed = False

    def remove_unknown_year(match: re.Match[str]) -> str:
        nonlocal changed
        if match.group(0) in allowed_years:
            return match.group(0)
        changed = True
        return ""

    clean = YEAR_RE.sub(remove_unknown_year, title)
    clean = re.sub(r"\(\s*\)", "", clean)
    clean = re.sub(r"\s+([:;,])", r"\1", clean)
    clean = re.sub(r"\s{2,}", " ", clean).strip(" -–—:,")
    return clean or source_keywords[0].title(), changed


def sanitize_claims(text: str) -> tuple[str, bool]:
    changed = bool(OUTCOME_CLAIM_RE.search(text))
    clean = OUTCOME_CLAIM_RE.sub("may support stronger search and user outcomes", text)
    clean = re.sub(
        r"\b(?:prevents?|eliminates?) keyword cannibalization\b",
        "reduces the risk of page overlap",
        clean,
        flags=re.IGNORECASE,
    )
    return clean, changed or clean != text


def choose_primary(items: list[KeywordItem], preferred: str | None = None) -> KeywordItem:
    if preferred:
        match = next((item for item in items if item.keyword.casefold() == preferred.casefold()), None)
        if match:
            return match
    return max(items, key=lambda item: (item.volume is not None, item.volume or 0, -len(item.keyword)))


def score_priority(
    *, role: str, intent: SearchIntent, items: list[KeywordItem], max_cluster_volume: int | None
) -> tuple[int, list[str]]:
    score = 42
    factors: list[str] = []
    if role == "pillar":
        score += 16
        factors.append("pillar role")
    intent_points = {"transactional": 15, "commercial": 12, "informational": 7, "navigational": 5, "mixed": 3}[intent]
    score += intent_points
    factors.append(f"{intent} intent")
    coverage_points = min(10, max(2, len(items) * 2))
    score += coverage_points
    factors.append(f"covers {len(items)} keyword{'s' if len(items) != 1 else ''}")
    total_volume = sum(item.volume or 0 for item in items)
    if total_volume and max_cluster_volume:
        volume_points = max(3, round(17 * math.sqrt(total_volume / max_cluster_volume)))
        score += volume_points
        factors.append(f"supplied volume {total_volume:,}")
    else:
        factors.append("no volume signal")
    return min(95, score), factors


def confidence_for(items: list[KeywordItem], intent: SearchIntent) -> str:
    buckets = [intent_bucket(item.keyword) for item in items]
    explicit = [bucket for bucket in buckets if bucket]
    if intent == "mixed" or len(items) == 1:
        return "low"
    if len(items) >= 3 and len(set(explicit)) <= 1:
        return "high"
    return "medium"


def dominant_bucket(items: list[KeywordItem]) -> str | None:
    counts = Counter(filter(None, (intent_bucket(item.keyword) for item in items)))
    return counts.most_common(1)[0][0] if counts else None
