from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AgentRunSummary(BaseModel):
    id: str
    agent_slug: str
    agent_name: str
    title: str
    detail: str
    status: str
    stage: str
    progress: int
    result_available: bool
    created_at: datetime
    updated_at: datetime


class AgentRunHistoryResponse(BaseModel):
    items: list[AgentRunSummary]
    total: int
    limit: int
    offset: int


class AgentRunHistoryService:
    """Compose agent-specific stores into one filterable history surface."""

    def __init__(self, audit_repository, metadata_repository, schema_repository, keyword_cluster_repository):
        self.audit_repository = audit_repository
        self.metadata_repository = metadata_repository
        self.schema_repository = schema_repository
        self.keyword_cluster_repository = keyword_cluster_repository

    def list_runs(self, *, limit: int, offset: int, query: str | None, agent: str | None) -> AgentRunHistoryResponse:
        candidates: list[AgentRunSummary] = []
        requested = limit + offset
        if agent in {None, "", "all", "seo-audit"}:
            for audit in self.audit_repository.list_audits(requested, 0, query):
                pages, findings = self.audit_repository.counts(audit.id)
                candidates.append(AgentRunSummary(
                    id=audit.id, agent_slug="seo-audit", agent_name="SEO/AEO Audit Agent",
                    title=audit.requested_url,
                    detail=f"{pages} pages · {findings} findings · limit {audit.crawl_limit}",
                    status=audit.status.value, stage=audit.stage.value, progress=audit.progress,
                    result_available=self.audit_repository.get_report(audit.id) is not None,
                    created_at=audit.created_at, updated_at=audit.updated_at,
                ))
        if agent in {None, "", "all", "meta-title-description"}:
            for run in self.metadata_repository.list_generations(requested, 0, query):
                page_count = len(run.parsed_brief.pages) if run.parsed_brief else 0
                candidates.append(AgentRunSummary(
                    id=run.id, agent_slug="meta-title-description", agent_name="Meta Title & Description Generator",
                    title=run.prompt, detail=f"{page_count} page{'s' if page_count != 1 else ''} · metadata generation",
                    status=run.status.value, stage=run.stage.value, progress=run.progress,
                    result_available=run.result is not None, created_at=run.created_at, updated_at=run.updated_at,
                ))
        if agent in {None, "", "all", "schema-markup"}:
            for run in self.schema_repository.list_generations(requested, 0, query):
                schema_types = [entity.schema_type for entity in run.parsed_brief.entities] if run.parsed_brief else []
                detail = f"{len(schema_types)} schema type{'s' if len(schema_types) != 1 else ''}" + (f" · {', '.join(schema_types)}" if schema_types else " · schema generation")
                candidates.append(AgentRunSummary(
                    id=run.id, agent_slug="schema-markup", agent_name="Schema Markup Generator",
                    title=run.prompt, detail=detail, status=run.status.value, stage=run.stage.value,
                    progress=run.progress, result_available=run.result is not None,
                    created_at=run.created_at, updated_at=run.updated_at,
                ))
        if agent in {None, "", "all", "keyword-cluster"}:
            for run in self.keyword_cluster_repository.list_generations(requested, 0, query):
                keyword_count = len(run.parsed_keywords)
                cluster_count = len(run.result.clusters) if run.result else 0
                pillar_count = len(run.result.pillars) if run.result else 0
                title = next((item.keyword for item in run.parsed_keywords), run.raw_keywords.splitlines()[0] if run.raw_keywords.splitlines() else "Keyword plan")
                candidates.append(AgentRunSummary(
                    id=run.id, agent_slug="keyword-cluster", agent_name="Keyword Cluster Agent",
                    title=title, detail=f"{keyword_count} keywords · {cluster_count} clusters · {pillar_count} pillars",
                    status=run.status.value, stage=run.stage.value, progress=run.progress,
                    result_available=run.result is not None, created_at=run.created_at, updated_at=run.updated_at,
                ))
        candidates.sort(key=lambda item: item.created_at, reverse=True)
        return AgentRunHistoryResponse(
            items=candidates[offset:offset + limit], total=self._count(query=query, agent=agent),
            limit=limit, offset=offset,
        )

    def _count(self, *, query: str | None, agent: str | None) -> int:
        total = 0
        if agent in {None, "", "all", "seo-audit"}:
            total += self.audit_repository.count_audits(query)
        if agent in {None, "", "all", "meta-title-description"}:
            total += self.metadata_repository.count_generations(query)
        if agent in {None, "", "all", "schema-markup"}:
            total += self.schema_repository.count_generations(query)
        if agent in {None, "", "all", "keyword-cluster"}:
            total += self.keyword_cluster_repository.count_generations(query)
        return total
