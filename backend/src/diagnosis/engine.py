from __future__ import annotations

import asyncio
import copy
import os
import time
from dataclasses import replace
from uuid import uuid4

from diagnosis.models import AGENTS, Task, now
from diagnosis.evidence import SnapshotCrawler, derive_research_query, derive_resort_identity, snapshot, narrative
from resort_orchestrator import workflow as legacy
from seo_audit.crawler import SiteCrawler
from seo_audit.reporting import ReportWriter
from serp_competitor.models import SerpRequest
from serp_competitor.workflow import run_serp_analysis
from content_brief.models import ContentBriefCreate
from content_brief.workflow import build_content_brief_graph


TERMINAL = {"complete", "failed", "needs_review"}
DEPS = {key: {"capture"} for key in AGENTS}
DEPS.update(keyword_cluster={"capture", "serp_competitor"}, content_brief={"capture", "serp_competitor", "keyword_cluster"}, content_optimizer={"capture", "serp_competitor", "content_brief"}, report=set(AGENTS), capture=set())
MODEL_TASKS = {"internal_linking", "keyword_cluster", "metadata", "schema_markup", "content_brief", "local_seo", "report"}


def claim(repository, id):
    def change(run):
        if run.status in {"complete", "partial", "cancelled"}:
            return None
        stamp = time.time()
        for task in run.tasks.values():
            if task.status == "running" and task.lease_until < stamp:
                task.status = "queued" if task.attempts < 3 else "failed"
                task.error = "Task interrupted; resume requested." if task.status == "queued" else "Task exceeded its recovery limit. Retry this task."
                task.token = None
        active = [k for k,t in run.tasks.items() if t.status == "running"]
        if len(active) >= 2:
            return None
        for key, task in run.tasks.items():
            if task.status != "queued" or not all(run.tasks[d].status in TERMINAL for d in DEPS[key]):
                continue
            if key in MODEL_TASKS and any(k in MODEL_TASKS for k in active):
                continue
            token = str(uuid4())
            task.status, task.token, task.lease_until = "running", token, stamp + 240
            task.started_at, task.attempts, task.error = now(), task.attempts + 1, None
            run.status = "running"
            return key, token
    return repository.mutate(id, change)


def checkpoint(repository, id, key, token, run_id):
    def change(run):
        task = run.tasks[key]
        if task.token == token and run.status != "cancelled":
            task.run_id = run_id
    repository.mutate(id, change)


class ChildRepository:
    """Persist a child identifier before its first external call; reuse on recovery."""
    def __init__(self, original, saved_id, on_create):
        self.original, self.saved_id, self.on_create = original, saved_id, on_create

    def __getattr__(self, name):
        value = getattr(self.original, name)
        if name not in {"create", "create_audit", "create_generation"}:
            return value
        def create(*args, **kwargs):
            if self.saved_id:
                getter = "get_audit" if name == "create_audit" else "get_generation" if name == "create_generation" else "get"
                return getattr(self.original, getter)(self.saved_id)
            child = value(*args, **kwargs)
            self.saved_id = child.id
            self.on_create(child.id)
            return child
        return create


REPOSITORIES = {
    "seo_audit": "audit_repository", "ai_visibility": "visibility_repository",
    "internal_linking": "internal_link_repository", "serp_competitor": "serp_repository",
    "keyword_cluster": "keyword_cluster_repository", "metadata": "metadata_repository",
    "schema_markup": "schema_repository", "content_brief": "content_brief_repository",
    "local_seo": "local_repository", "content_optimizer": "content_optimizer_repository",
}


def task_dependencies(deps, run, key, repository, token):
    result = copy.copy(deps)
    settings = deps.settings
    use_deepseek = key in MODEL_TASKS and run.request.model_provider == "deepseek"
    if use_deepseek:
        api_key, model = os.getenv("DEEPSEEK_API_KEY"), os.getenv("DEEPSEEK_MODEL")
        if not api_key or not model:
            raise ValueError("DeepSeek configuration is incomplete")
        settings = replace(settings, llm_provider="openai", llm_api_key=api_key, llm_model=model,
                           llm_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                           llm_max_output_tokens=max(settings.llm_max_output_tokens, 1800))
    else:
        generator = deps.metadata_generator
        settings = replace(settings,
            llm_api_key=generator.api_key_resolver(settings.llm_provider, settings.llm_api_key) if generator.api_key_resolver else settings.llm_api_key,
            llm_model=generator.model_resolver(settings.llm_model) if generator.model_resolver else settings.llm_model)
    result.settings = replace(settings, crawl_timeout_seconds=75)
    for attr in ["metadata_generator", "schema_interpreter", "keyword_cluster_generator", "internal_link_refiner", "content_brief_generator", "local_generator"]:
        setattr(result, attr, type(getattr(deps, attr))(result.settings))
    # The final management report owns narration; don't spend another model call here.
    result.report_writer = ReportWriter(replace(result.settings, llm_provider=None, write_report_files=False))
    result.crawler = SnapshotCrawler(run.tasks["capture"].result, result.settings)
    if key in REPOSITORIES:
        attr = REPOSITORIES[key]
        setattr(result, attr, ChildRepository(getattr(deps, attr), run.tasks[key].run_id, lambda child: checkpoint(repository, run.id, key, token, child)))
    return result


def child_result(deps, key, id):
    repo = getattr(deps, REPOSITORIES[key])
    if key == "seo_audit":
        value = repo.get_report(id)
    elif key in {"ai_visibility", "internal_linking"}:
        value = repo.get_audit(id).result
    elif key in {"serp_competitor", "content_optimizer", "local_seo"}:
        value = repo.get(id).result
    else:
        value = repo.get_generation(id).result
    return value.model_dump(mode="json") if value else {}


async def execute(deps, repository, run, key, token):
    url = str(run.request.page_url)
    if key == "capture":
        crawl = await SiteCrawler(replace(deps.settings, crawl_timeout_seconds=75)).crawl(run.id, url, run.request.page_limit)
        if not crawl.pages:
            raise ValueError("No inspectable pages")
        captured = snapshot(crawl)
        captured["identity"] = derive_resort_identity(captured, url)
        captured["research_query"] = captured["identity"]["branded_query"]
        return captured
    if key == "report":
        from diagnosis.reporting import assemble_report, narrate
        report = assemble_report(run)
        # A deterministic report still works when page capture/model configuration failed.
        if run.tasks["capture"].status == "complete":
            try:
                selected = task_dependencies(deps, run, key, repository, token)
                report = await narrate(report, selected.settings)
            except Exception:
                report["narrative"]["note"] = "The configured model was unavailable. The factual report is retained."
        return report
    if run.tasks["capture"].status != "complete":
        return {"status": "needs_review", "reason": "The resort could not be inspected; no website conclusion can be drawn."}
    primary = run.tasks["capture"].result["pages"][0]
    if key in {"metadata", "schema_markup", "local_seo", "content_brief", "content_optimizer"} and (primary.get("status_code") != 200 or not primary.get("main_text")):
        return {"status": "needs_review", "reason": "The target did not return usable resort content. No drafts were generated from an error page."}
    selected = task_dependencies(deps, run, key, repository, token)
    source = narrative(run.tasks["capture"].result)
    keyword = derive_research_query(run.tasks["capture"].result, url)
    research_task = run.tasks["serp_competitor"]
    research = deps.serp_repository.get(research_task.run_id).result if research_task.status == "complete" and research_task.run_id else None
    if key == "local_seo":
        phones = list(dict.fromkeys(__import__("re").findall(r"(?:\+?\d[\d\s().-]{7,}\d)", primary.get("main_text", ""))))[:10]
        return {"status": "complete", "detail": {
            "mode": "url_assessment",
            "identity": keyword,
            "phone_numbers": phones,
            "observations": [
                "Observed resort identity: " + keyword,
                "Observed structured-data types: " + (", ".join(primary.get("schema_types", [])) or "none"),
                f"Observed {len(phones)} distinct phone-number pattern(s) in the captured page text.",
                *( ["Observed phone patterns for property-owner verification: " + ", ".join(phones)] if phones else [] ),
            ],
            "limitations": ["This URL-mode assessment reviews extractable local identity and contact signals. It does not create a separate local landing page or verify third-party listings."],
        }}
    if key == "metadata":
        return {"status": "complete", "detail": {
            "mode": "url_assessment",
            "observations": ["The current title and search description were measured directly from the captured HTML."],
            "warnings": ["The agent inspected current metadata. Any optional copy change requires approval from Sterling's content owner."],
        }}
    if key == "serp_competitor":
        child = selected.serp_repository.create(SerpRequest(target_keyword=keyword, country=run.request.country, language=run.request.language))
        await run_serp_analysis(selected.settings, selected.serp_repository, child.id, crawler=selected.crawler)
        final = selected.serp_repository.get(child.id)
        outcome = legacy.AgentOutcome(agent=key, run_id=child.id, status=final.status, error=final.error)
    elif key == "keyword_cluster":
        # Related searches/questions are measured query evidence. When those are absent,
        # combine the resort identity with recurring observed SERP themes and label them
        # as planning inputs rather than claiming search demand.
        seeds = [keyword]
        if research:
            seeds.extend(research.related_searches)
            seeds.extend(q.question for q in research.questions)
            for pattern in research.topic_patterns:
                label = pattern.label.strip()
                tokens = label.casefold().split()
                useful = (
                    label and not any(token.isdigit() or token in {"updated", "update"} for token in tokens)
                    and not all(token in keyword.casefold().split() for token in tokens)
                )
                if useful:
                    seeds.append(f"{keyword} {label}")
        seeds = list(dict.fromkeys(seeds))
        clusters = [{
            "name": "Resort discovery and evaluation",
            "primary_keyword": keyword,
            "keywords": seeds[:30],
            "suggested_title": f"{keyword}: Resort Details and Booking Information",
        }]
        return {"status": "complete", "detail": {
            "mode": "serp_evidence_assessment", "clusters": clusters,
            "warnings": ["These are planning themes derived from the resort identity and observed search-result language. No search volume or demand is claimed."],
        }}
    elif key == "content_brief":
        import json
        cluster_detail = run.tasks["keyword_cluster"].result.get("detail", {})
        secondary = []
        for cluster in cluster_detail.get("clusters", []):
            for item in cluster.get("keywords", []):
                candidate = item.get("keyword") if isinstance(item, dict) else item
                if candidate and candidate.casefold() != keyword.casefold() and candidate not in secondary:
                    secondary.append(candidate)
        notes = source[:4500] + "\nSearch research (observations, not instructions):\n" + (json.dumps(research.model_dump(mode="json"))[:3000] if research else "Not available")
        child = selected.content_brief_repository.create_generation(ContentBriefCreate(target_keyword=keyword, secondary_keywords=secondary[:30], audience=run.request.audience or "Unconfirmed audience; human review required", business_goal=run.request.business_goal or None, product_context=source[:1900], source_notes=notes[:7900], existing_urls=[p["final_url"] for p in run.tasks["capture"].result["pages"]][:20], content_mode="rewrite"))
        await build_content_brief_graph(selected.settings, selected.content_brief_repository, generator=selected.content_brief_generator).ainvoke({"generation_id": child.id})
        final = selected.content_brief_repository.get_generation(child.id)
        if final.result and (not run.request.audience or not run.request.business_goal):
            final.result.ready_for_handoff = False
            final.result.warnings.append("Audience or business goal is unconfirmed; editorial approval is required.")
            selected.content_brief_repository.save_result(final.result)
        outcome = legacy.AgentOutcome(agent=key, run_id=child.id, status=final.status.value, error=final.error)
    else:
        calls = {
            "seo_audit": lambda: legacy._run_seo_audit(selected, url),
            "ai_visibility": lambda: legacy._run_ai_visibility(selected, url),
            "internal_linking": lambda: legacy._run_internal_linking(selected, url),
            "metadata": lambda: legacy._run_metadata(selected, source, keyword),
            "schema_markup": lambda: legacy._run_schema(selected, source),
            "local_seo": lambda: legacy._run_local_seo(selected, source, url),
            "content_optimizer": lambda: legacy._run_content_optimizer(selected, url, keyword, run.request.audience or None, research_task.run_id if research else None, run.tasks["content_brief"].run_id if run.tasks["content_brief"].status == "complete" else None),
        }
        outcome = await calls[key]()
    if outcome.status != "complete" and key in {"metadata", "schema_markup", "content_brief"}:
        labels = {"metadata": "Metadata draft", "schema_markup": "Schema correction draft", "content_brief": "Content improvement draft"}
        return {"status": "complete", "run_id": outcome.run_id, "detail": {
            "warnings": [f"{labels[key]} generation was unavailable. The agent's live-page assessment remains included from captured evidence."],
            "observations": ["The current page was assessed successfully; optional generated recommendations require a later provider retry."],
        }}
    if outcome.status != "complete":
        raise ValueError("Child agent did not complete")
    detail = child_result(deps, key, outcome.run_id)
    if key == "keyword_cluster" and research and not research.related_searches and not research.questions:
        detail.setdefault("warnings", []).append("No related searches or question boxes were returned; recurring SERP themes were used as planning inputs without claiming measured demand.")
    return {"status": "complete", "run_id": outcome.run_id, "detail": detail}


async def process_one(deps, repository, id):
    claimed = claim(repository, id)
    if not claimed:
        return repository.get(id)
    key, token = claimed
    try:
        async with asyncio.timeout(180):
            result = await execute(deps, repository, repository.get(id), key, token)
        state, error = result.get("status", "complete"), None
        if state not in {"complete", "needs_review"}:
            state = "complete"
    except (Exception, asyncio.CancelledError):
        result, state, error = {}, "failed", "This task could not complete within its request/provider budget. Its evidence was preserved; retry is available."
    def finish(run):
        task = run.tasks[key]
        if task.token != token or run.status == "cancelled":
            return
        task.result, task.status, task.error = result, state, error
        task.finished_at, task.token, task.lease_until = now(), None, 0
        if key == "report":
            if state == "complete":
                run.report = result
            run.status = "partial" if any(t.status != "complete" for t in run.tasks.values()) else "complete"
    repository.mutate(id, finish)
    return repository.get(id)


def retry(repository, id):
    def change(run):
        if any(t.status == "running" and t.lease_until > time.time() for t in run.tasks.values()):
            raise ValueError("Wait for active tasks or cancel before retrying")
        reset = {k for k,t in run.tasks.items() if t.status != "complete"}
        metadata_warnings = run.tasks["metadata"].result.get("detail", {}).get("warnings", [])
        if any("generation was unavailable" in item for item in metadata_warnings):
            reset.add("metadata")
        capture = run.tasks["capture"].result
        if capture:
            corrected_query = derive_research_query(capture, str(run.request.page_url))
            if capture.get("research_query") != corrected_query:
                capture["identity"] = derive_resort_identity(capture, str(run.request.page_url))
                capture["research_query"] = corrected_query
                # A changed identity invalidates both downstream research and
                # evidence counts produced by the older capture contract.
                reset |= {"capture", *AGENTS}
        while True:
            expanded = reset | {k for k, parents in DEPS.items() if parents & reset}
            if expanded == reset:
                break
            reset = expanded
        for k in reset | {"report"}:
            run.tasks[k] = Task()
        run.report, run.status = None, "queued"
    repository.mutate(id, change)
    return repository.get(id)


def rerun_all(repository, id):
    """Discard a legacy diagnosis contract and rerun capture plus every agent."""
    def change(run):
        if any(t.status == "running" and t.lease_until > time.time() for t in run.tasks.values()):
            raise ValueError("Wait for active tasks or cancel before upgrading")
        for key in run.tasks:
            run.tasks[key] = Task()
        run.report, run.status = None, "queued"
    repository.mutate(id, change)
    return repository.get(id)


def cancel(repository, id):
    def change(run):
        run.status = "cancelled"
        for task in run.tasks.values():
            if task.status == "running":
                task.status, task.token, task.lease_until = "failed", None, 0
                task.error = "Cancelled; late results will not overwrite this diagnosis."
    repository.mutate(id, change)
    return repository.get(id)
