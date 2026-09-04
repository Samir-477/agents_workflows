from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from keyword_cluster.api import create_keyword_cluster_router
from keyword_cluster.models import (
    CandidateCluster,
    ConsolidatedCluster,
    ConsolidatedClusterSet,
    KeywordClusterCreate,
)
from keyword_cluster.parsing import parse_keywords
from keyword_cluster.quality import sanitize_claims, sanitize_title, split_on_conflicting_intent
from keyword_cluster.storage import MemoryKeywordClusterRepository
from keyword_cluster.workflow import build_keyword_cluster_graph
from seo_audit.config import Settings


RAW = """crm for freelancers, 1200
best crm for freelancers,900
crm pricing\t500
how to choose crm
CRM for freelancers, 800
"""


class FakeClusterGenerator:
    async def create_candidates(self, keywords):
        return [
            CandidateCluster(
                name="Freelancer CRM",
                intent="commercial",
                primary_keyword="crm for freelancers",
                keywords=[item.keyword for item in keywords],
                reasoning="These terms concern selecting or understanding a CRM.",
                recommended_page_type="Buying guide",
            )
        ]

    async def consolidate(self, keywords, candidates):
        return ConsolidatedClusterSet(
            strategy_summary="Build one commercial hub supported by a practical guide.",
            assumptions=["Volumes are monthly estimates supplied by the user."],
            clusters=[
                ConsolidatedCluster(
                    name="Freelancer CRM options",
                    pillar_name="Freelancer CRM",
                    role="pillar",
                    intent="commercial",
                    primary_keyword="crm for freelancers",
                    keywords=["crm for freelancers", "best crm for freelancers", "crm pricing"],
                    reasoning="The same commercial page can satisfy these choices.",
                    recommended_page_type="Pillar buying guide",
                    suggested_title="Best CRM for Freelancers",
                    build_priority=92,
                ),
                ConsolidatedCluster(
                    name="Choosing a CRM",
                    pillar_name="Freelancer CRM",
                    role="supporting",
                    intent="informational",
                    primary_keyword="how to choose crm",
                    keywords=["how to choose crm"],
                    reasoning="This query needs a practical educational guide.",
                    recommended_page_type="How-to guide",
                    suggested_title="How to Choose a CRM",
                    build_priority=70,
                ),
            ],
        )


def test_parser_deduplicates_and_reads_formatted_volumes():
    items, duplicates, warnings = parse_keywords("crm, 1,200\nCRM,900\nbest crm\t400")
    assert [(item.keyword, item.volume) for item in items] == [("crm", 1200), ("best crm", 400)]
    assert duplicates == 1
    assert warnings == ["Removed 1 duplicate keyword row."]


async def test_workflow_preserves_keywords_and_builds_bidirectional_pillar_links():
    repository = MemoryKeywordClusterRepository()
    run = repository.create_generation(KeywordClusterCreate(keywords=RAW))
    await build_keyword_cluster_graph(Settings(), repository, generator=FakeClusterGenerator()).ainvoke(
        {"generation_id": run.id}
    )
    completed = repository.get_generation(run.id)
    assert completed.status == "complete"
    assert completed.result is not None
    assert completed.result.unique_keyword_count == 4
    assert completed.result.duplicate_count == 1
    assert len(completed.result.clusters) == 3
    assert len(completed.result.pillars) == 1
    assert len(completed.result.internal_links) == 5
    assert completed.result.pillars[0].recommendation_status == "candidate"
    assert all(cluster.priority_factors for cluster in completed.result.clusters)


def test_api_create_process_result_and_delete_cycle():
    repository = MemoryKeywordClusterRepository()
    app = FastAPI()
    app.include_router(
        create_keyword_cluster_router(Settings(), repository, generator=FakeClusterGenerator())
    )
    with TestClient(app) as client:
        created = client.post(
            "/api/agents/keyword-cluster/generations", json={"keywords": RAW}
        )
        assert created.status_code == 202
        generation_id = created.json()["generation"]["id"]
        processed = client.post(
            f"/api/agents/keyword-cluster/generations/{generation_id}/process"
        )
        assert processed.status_code == 200
        result = client.get(
            f"/api/agents/keyword-cluster/generations/{generation_id}/result"
        )
        assert result.status_code == 200
        assert result.json()["pillars"][0]["name"] == "Freelancer CRM"
        assert client.delete(
            f"/api/agents/keyword-cluster/generations/{generation_id}"
        ).status_code == 204


def test_quality_guardrails_split_conflicting_intent_and_remove_invented_years():
    items, _, _ = parse_keywords("how to choose a crm\ncrm pricing\nbest crm for freelancers")
    partitions = split_on_conflicting_intent(items)
    assert {bucket for bucket, _ in partitions} == {"how-to", "pricing", "comparison"}
    title, changed = sanitize_title("Best CRM Tools Compared (2024)", [item.keyword for item in items])
    assert title == "Best CRM Tools Compared"
    assert changed is True
    summary, softened = sanitize_claims("This structure reduces bounce rates and improves conversions.")
    assert "reduces bounce rates" not in summary
    assert "improves conversions" not in summary
    assert softened is True
