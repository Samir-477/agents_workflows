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

    def __init__(self, audit_repository, metadata_repository):
        self.audit_repository = audit_repository
        self.metadata_repository = metadata_repository

    def list_runs(
        self,
        *,
        limit: int,
        offset: int,
        query: str | None,
        agent: str | None,
    ) -> AgentRunHistoryResponse:
        candidates: list[AgentRunSummary] = []
        requested = limit + offset
        if agent in {None, "", "all", "seo-audit"}:
            for audit in self.audit_repository.list_audits(requested, 0, query):
                pages, findings = self.audit_repository.counts(audit.id)
                candidates.append(
                    AgentRunSummary(
                        id=audit.id,
                        agent_slug="seo-audit",
                        agent_name="SEO/AEO Audit Agent",
                        title=audit.requested_url,
                        detail=f"{pages} pages · {findings} findings · limit {audit.crawl_limit}",
                        status=audit.status.value,
                        stage=audit.stage.value,
                        progress=audit.progress,
                        result_available=self.audit_repository.get_report(audit.id) is not None,
                        created_at=audit.created_at,
                        updated_at=audit.updated_at,
                    )
                )
        if agent in {None, "", "all", "meta-title-description"}:
            for run in self.metadata_repository.list_generations(requested, 0, query):
                page_count = len(run.parsed_brief.pages) if run.parsed_brief else 0
                candidates.append(
                    AgentRunSummary(
                        id=run.id,
                        agent_slug="meta-title-description",
                        agent_name="Meta Title & Description Generator",
                        title=run.prompt,
                        detail=f"{page_count} page{'s' if page_count != 1 else ''} · metadata generation",
                        status=run.status.value,
                        stage=run.stage.value,
                        progress=run.progress,
                        result_available=run.result is not None,
                        created_at=run.created_at,
                        updated_at=run.updated_at,
                    )
                )
        candidates.sort(key=lambda item: item.created_at, reverse=True)
        total = self._count(query=query, agent=agent)
        return AgentRunHistoryResponse(
            items=candidates[offset : offset + limit],
            total=total,
            limit=limit,
            offset=offset,
        )

    def _count(self, *, query: str | None, agent: str | None) -> int:
        total = 0
        if agent in {None, "", "all", "seo-audit"}:
            total += self.audit_repository.count_audits(query)
        if agent in {None, "", "all", "meta-title-description"}:
            total += self.metadata_repository.count_generations(query)
        return total
