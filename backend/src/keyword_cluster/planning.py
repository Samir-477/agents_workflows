from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from keyword_cluster.models import (
    ConsolidatedCluster,
    ConsolidatedClusterSet,
    InternalLinkRecommendation,
    KeywordClusterResult,
    KeywordClusterResultItem,
    KeywordItem,
    PillarPlan,
)
from keyword_cluster.quality import (
    bucket_intent,
    choose_primary,
    confidence_for,
    dominant_bucket,
    sanitize_claims,
    sanitize_title,
    score_priority,
    split_on_conflicting_intent,
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-")[:90] or "topic"


def display_title(keyword: str) -> str:
    words = keyword.title().split()
    return " ".join(word.upper() if word.casefold() in {"crm", "seo", "saas", "b2b", "b2c"} else word for word in words)


def compile_plan(
    generation_id: str,
    source: list[KeywordItem],
    draft: ConsolidatedClusterSet,
    *,
    input_count: int,
    duplicate_count: int,
    warnings: list[str],
) -> KeywordClusterResult:
    by_key = {item.keyword.casefold(): item for item in source}
    assigned: set[str] = set()
    used_slugs: set[str] = set()
    clusters: list[KeywordClusterResultItem] = []
    pieces: list[tuple[ConsolidatedCluster, str | None, list[KeywordItem]]] = []
    quality_warnings: list[str] = []

    for cluster in draft.clusters:
        items: list[KeywordItem] = []
        for keyword in cluster.keywords:
            key = keyword.casefold()
            if key in by_key and key not in assigned:
                assigned.add(key)
                items.append(by_key[key])
        primary = by_key.get(cluster.primary_keyword.casefold())
        if primary and primary.keyword.casefold() not in assigned:
            assigned.add(primary.keyword.casefold())
            items.insert(0, primary)
        if not items:
            continue
        partitions = split_on_conflicting_intent(items)
        if len(partitions) > 1:
            quality_warnings.append(
                f"Split '{cluster.name}' because explicit query modifiers indicated different page intents."
            )
        pieces.extend((cluster, bucket, members) for bucket, members in partitions)

    cluster_volumes = [sum(item.volume or 0 for item in members) for _, _, members in pieces]
    max_cluster_volume = max(cluster_volumes, default=0) or None
    for cluster, bucket, items in pieces:
        contains_model_primary = any(item.keyword.casefold() == cluster.primary_keyword.casefold() for item in items)
        primary_item = choose_primary(items, cluster.primary_keyword if contains_model_primary else None)
        intent = bucket_intent(bucket or dominant_bucket(items), cluster.intent)
        role = cluster.role if contains_model_primary else "supporting"
        base_slug = slugify(primary_item.keyword)
        slug = base_slug
        suffix = 2
        while slug in used_slugs:
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        used_slugs.add(slug)
        volumes = [item.volume for item in items if item.volume is not None]
        suggested_title, removed_year = sanitize_title(
            cluster.suggested_title if contains_model_primary else display_title(primary_item.keyword),
            [item.keyword for item in source],
        )
        if removed_year:
            quality_warnings.append(f"Removed an unsupported year from the title for '{cluster.name}'.")
        reasoning, softened_claim = sanitize_claims(cluster.reasoning)
        if softened_claim:
            quality_warnings.append(f"Softened an unsupported outcome claim in '{cluster.name}'.")
        priority, priority_factors = score_priority(
            role=role, intent=intent, items=items, max_cluster_volume=max_cluster_volume
        )
        name = cluster.name if contains_model_primary else display_title(primary_item.keyword)
        clusters.append(KeywordClusterResultItem(
            name=name,
            pillar_name=cluster.pillar_name,
            role=role,
            intent=intent,
            primary_keyword=primary_item.keyword,
            keywords=items,
            reasoning=reasoning,
            recommended_page_type=cluster.recommended_page_type if contains_model_primary else (
                "Pricing page" if bucket == "pricing" else "How-to guide" if bucket == "how-to" else "Dedicated intent page"
            ),
            suggested_title=suggested_title,
            suggested_slug=f"/{slug}/",
            build_priority=priority,
            total_volume=sum(volumes) if volumes else None,
            confidence=confidence_for(items, intent),
            priority_factors=priority_factors,
        ))

    unassigned = [item for item in source if item.keyword.casefold() not in assigned]
    for item in unassigned:
        slug = slugify(item.keyword)
        base_slug, suffix = slug, 2
        while slug in used_slugs:
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        used_slugs.add(slug)
        clusters.append(KeywordClusterResultItem(
            name=item.keyword.title(), pillar_name="Unassigned opportunities", role="supporting",
            intent="mixed", primary_keyword=item.keyword, keywords=[item],
            reasoning="Kept as a separate opportunity because the consolidation pass did not assign it confidently.",
            recommended_page_type="Research required", suggested_title=item.keyword.title(),
            suggested_slug=f"/{slug}/", build_priority=20, total_volume=item.volume,
            confidence="low", priority_factors=["unassigned by the model", "manual review required"],
        ))
    if unassigned:
        warnings.append(f"{len(unassigned)} keyword{'s were' if len(unassigned) != 1 else ' was'} kept as separate opportunities for manual review.")

    grouped: dict[str, list[KeywordClusterResultItem]] = defaultdict(list)
    for cluster in clusters:
        grouped[cluster.pillar_name].append(cluster)
    pillars: list[PillarPlan] = []
    for name, members in grouped.items():
        owner = next((item for item in members if item.role == "pillar"), max(members, key=lambda item: item.build_priority))
        volumes = [item.total_volume for item in members if item.total_volume is not None]
        supporting_count = sum(item.id != owner.id for item in members)
        established = supporting_count >= 2 and len(source) >= 10
        pillars.append(PillarPlan(
            name=name, primary_keyword=owner.primary_keyword, suggested_title=owner.suggested_title,
            suggested_slug=owner.suggested_slug, cluster_ids=[item.id for item in members],
            supporting_page_ids=[item.id for item in members if item.id != owner.id], intent=owner.intent,
            build_priority=max(item.build_priority for item in members), total_volume=sum(volumes) if volumes else None,
            recommendation_status="established" if established else "candidate",
            rationale=(
                "The input contains enough distinct supporting pages to form a defensible hub-and-spoke section."
                if established else
                "Treat this as a topic-hub candidate: the supplied list is too small or shallow to prove a full pillar architecture."
            ),
        ))
    pillars.sort(key=lambda item: item.build_priority, reverse=True)

    links: list[InternalLinkRecommendation] = []
    for pillar in pillars:
        members = [item for item in clusters if item.id in pillar.cluster_ids]
        owner = next(item for item in members if item.suggested_slug == pillar.suggested_slug)
        supporting = [item for item in members if item.id != owner.id]
        for index, item in enumerate(supporting):
            links.append(InternalLinkRecommendation(
                source_cluster_id=owner.id, target_cluster_id=item.id,
                source_slug=owner.suggested_slug, target_slug=item.suggested_slug,
                anchor_text=item.primary_keyword,
                reason=f"Let the {pillar.name} pillar introduce its supporting {item.name} page.",
            ))
            links.append(InternalLinkRecommendation(
                source_cluster_id=item.id, target_cluster_id=owner.id,
                source_slug=item.suggested_slug, target_slug=owner.suggested_slug,
                anchor_text=owner.primary_keyword,
                reason=f"Connect the supporting {item.name} page to its {pillar.name} pillar.",
            ))
            for sibling in supporting[index + 1:index + 3]:
                links.append(InternalLinkRecommendation(
                    source_cluster_id=item.id, target_cluster_id=sibling.id,
                    source_slug=item.suggested_slug, target_slug=sibling.suggested_slug,
                    anchor_text=sibling.primary_keyword,
                    reason="Connect closely related supporting pages where the topic is naturally discussed.",
                ))

    strategy_summary, softened_summary = sanitize_claims(draft.strategy_summary)
    if softened_summary:
        quality_warnings.append("Softened unsupported ranking, traffic, bounce-rate, or conversion claims in the strategy summary.")
    if len(source) < 10:
        quality_warnings.append("This is a small keyword set; pillar labels are candidates until broader research confirms topic depth.")
    return KeywordClusterResult(
        generation_id=generation_id, input_count=input_count,
        unique_keyword_count=len(source), duplicate_count=duplicate_count,
        clusters=sorted(clusters, key=lambda item: item.build_priority, reverse=True),
        pillars=pillars, internal_links=links, strategy_summary=strategy_summary,
        assumptions=draft.assumptions, warnings=list(dict.fromkeys([*warnings, *quality_warnings])),
    )
