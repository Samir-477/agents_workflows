from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from seo_audit.config import Settings
from seo_audit.crawler import CrawlResult, SiteCrawler
from seo_audit.models import AuditStage, AuditStatus
from seo_audit.reporting import ReportWriter
from seo_audit.rules import audit_crawl_limitations, audit_pages
from seo_audit.scoring import score_findings
from seo_audit.storage import AuditRepository
from seo_audit.url_safety import ValidatedTarget, validate_public_target


class AuditWorkflowState(TypedDict, total=False):
    audit_id: str
    normalized_origin: str
    pages_crawled: int
    findings_count: int
    warnings: list[str]
    report_saved: bool
    error: str


TargetValidator = Callable[..., Awaitable[ValidatedTarget]]


def build_audit_graph(
    settings: Settings,
    repository: AuditRepository,
    *,
    crawler: SiteCrawler | None = None,
    report_writer: ReportWriter | None = None,
    target_validator: TargetValidator = validate_public_target,
):
    crawler = crawler or SiteCrawler(settings)
    report_writer = report_writer or ReportWriter(settings)

    async def validate_scope_node(state: AuditWorkflowState) -> AuditWorkflowState:
        audit = repository.get_audit(state["audit_id"])
        repository.update_audit(
            audit.id,
            status=AuditStatus.RUNNING,
            stage=AuditStage.VALIDATING,
            progress=5,
        )
        try:
            target = await target_validator(
                audit.requested_url,
                allow_private_networks=settings.allow_private_networks,
            )
        except Exception as exc:
            return {"error": str(exc)}
        repository.update_audit(
            audit.id,
            status=AuditStatus.RUNNING,
            stage=AuditStage.VALIDATING,
            progress=10,
            normalized_origin=target.origin,
        )
        return {"normalized_origin": target.origin}

    async def crawl_site_node(state: AuditWorkflowState) -> AuditWorkflowState:
        audit = repository.get_audit(state["audit_id"])
        repository.update_audit(
            audit.id,
            status=AuditStatus.RUNNING,
            stage=AuditStage.CRAWLING,
            progress=15,
        )
        try:
            result: CrawlResult = await crawler.crawl(
                audit.id, audit.requested_url, audit.crawl_limit
            )
        except Exception as exc:
            return {"error": str(exc)}
        repository.replace_pages(audit.id, result.pages)
        warnings = list(dict.fromkeys([*audit.warnings, *result.warnings]))
        repository.update_audit(
            audit.id,
            status=AuditStatus.RUNNING,
            stage=AuditStage.CRAWLING,
            progress=55,
            normalized_origin=result.origin,
            warnings=warnings,
        )
        return {
            "normalized_origin": result.origin,
            "pages_crawled": len(result.pages),
            "warnings": warnings,
        }

    def run_rules_node(state: AuditWorkflowState) -> AuditWorkflowState:
        audit = repository.get_audit(state["audit_id"])
        repository.update_audit(
            audit.id,
            status=AuditStatus.RUNNING,
            stage=AuditStage.AUDITING,
            progress=65,
        )
        try:
            pages = repository.list_pages(audit.id)
            findings = audit_pages(audit.id, pages)
            findings.extend(
                audit_crawl_limitations(
                    audit.id,
                    audit.requested_url,
                    audit.warnings,
                )
            )
            repository.replace_findings(audit.id, findings)
            return {"findings_count": len(findings)}
        except Exception as exc:
            return {"error": str(exc)}

    def score_findings_node(state: AuditWorkflowState) -> AuditWorkflowState:
        audit = repository.get_audit(state["audit_id"])
        repository.update_audit(
            audit.id,
            status=AuditStatus.RUNNING,
            stage=AuditStage.SCORING,
            progress=78,
        )
        try:
            findings = repository.list_findings(audit.id)
            scored = score_findings(findings, audit.important_urls)
            repository.replace_findings(audit.id, scored)
            return {"findings_count": len(scored)}
        except Exception as exc:
            return {"error": str(exc)}

    async def generate_report_node(state: AuditWorkflowState) -> AuditWorkflowState:
        audit = repository.get_audit(state["audit_id"])
        repository.update_audit(
            audit.id,
            status=AuditStatus.RUNNING,
            stage=AuditStage.REPORTING,
            progress=88,
        )
        try:
            pages = repository.list_pages(audit.id)
            findings = repository.list_findings(audit.id)
            report = await report_writer.write(audit, pages, findings)
            repository.save_report(report)
            return {"report_saved": True}
        except Exception as exc:
            return {"error": str(exc)}

    def fail_audit_node(state: AuditWorkflowState) -> AuditWorkflowState:
        error = state.get("error") or "The audit failed for an unknown reason"
        repository.update_audit(
            state["audit_id"],
            status=AuditStatus.FAILED,
            stage=AuditStage.FAILED,
            progress=100,
            error=error,
        )
        return {"error": error}

    def route(state: AuditWorkflowState) -> Literal["continue", "fail"]:
        return "fail" if state.get("error") else "continue"

    graph = StateGraph(AuditWorkflowState)
    graph.add_node("validate_scope", validate_scope_node)
    graph.add_node("crawl_site", crawl_site_node)
    graph.add_node("run_rules", run_rules_node)
    graph.add_node("score_findings", score_findings_node)
    graph.add_node("generate_report", generate_report_node)
    graph.add_node("fail_audit", fail_audit_node)

    graph.add_edge(START, "validate_scope")
    graph.add_conditional_edges(
        "validate_scope",
        route,
        {"continue": "crawl_site", "fail": "fail_audit"},
    )
    graph.add_conditional_edges(
        "crawl_site",
        route,
        {"continue": "run_rules", "fail": "fail_audit"},
    )
    graph.add_conditional_edges(
        "run_rules",
        route,
        {"continue": "score_findings", "fail": "fail_audit"},
    )
    graph.add_conditional_edges(
        "score_findings",
        route,
        {"continue": "generate_report", "fail": "fail_audit"},
    )
    graph.add_conditional_edges(
        "generate_report",
        route,
        {"continue": END, "fail": "fail_audit"},
    )
    graph.add_edge("fail_audit", END)
    return graph.compile()
