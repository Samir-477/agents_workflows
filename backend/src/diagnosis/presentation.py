from __future__ import annotations

from collections import defaultdict
from typing import Any


AGENT_SCORE_AREAS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    "seo_audit": [
        ("Crawl health", ("status", "redirect", "broken", "crawl", "robots")),
        ("Index directives", ("canonical", "index", "sitemap", "robots")),
        ("On-page quality", ("title", "description", "heading", "image", "content")),
        ("Structured data", ("schema", "json-ld", "structured")),
    ],
    "ai_visibility": [
        ("Discoverability", ("discover", "access", "robots", "crawl")),
        ("Machine readability", ("schema", "structured", "readab")),
        ("Entity clarity", ("entity", "identity", "name")),
        ("Citability", ("citation", "answer", "claim", "question")),
    ],
    "internal_linking": [
        ("Link coverage", ("coverage", "orphan", "inbound", "outbound")),
        ("Contextual relevance", ("context", "relevant", "placement")),
        ("Anchor quality", ("anchor", "wording")),
        ("Discovery paths", ("navigation", "depth", "discover")),
    ],
    "serp_competitor": [
        ("Brand presence", ("absent", "presence", "sterling", "exact")),
        ("Result relevance", ("intent", "result", "query")),
        ("Competitor evidence", ("competitor", "domain", "rival")),
        ("Research coverage", ("inspect", "sample", "question", "related")),
    ],
    "keyword_cluster": [
        ("Identity fit", ("identity", "property", "resort")),
        ("Intent coverage", ("intent", "theme", "keyword")),
        ("Theme separation", ("cluster", "overlap", "separation")),
        ("Evidence quality", ("evidence", "volume", "serp", "demand")),
    ],
    "metadata": [
        ("Title quality", ("title",)),
        ("Description quality", ("description", "meta")),
        ("Identity alignment", ("identity", "property", "name")),
        ("Search intent", ("intent", "query", "snippet")),
    ],
    "schema_markup": [
        ("Syntax validity", ("json", "parse", "syntax", "malformed")),
        ("Entity alignment", ("identity", "name", "property")),
        ("Visible fact support", ("visible", "fact", "claim")),
        ("Markup readiness", ("schema", "type", "publish")),
    ],
    "content_brief": [
        ("Search intent", ("intent", "audience", "goal")),
        ("Outline coverage", ("outline", "section", "coverage")),
        ("Evidence support", ("evidence", "research", "serp")),
        ("Handoff readiness", ("handoff", "quality", "writer")),
    ],
    "local_seo": [
        ("Property identity", ("identity", "name", "property")),
        ("Contact clarity", ("phone", "contact", "address")),
        ("Location signals", ("location", "destination", "map")),
        ("Listing verification", ("listing", "third-party", "verify")),
    ],
    "content_optimizer": [
        ("Intent alignment", ("intent", "keyword", "audience")),
        ("Content coverage", ("coverage", "topic", "depth")),
        ("Structure", ("heading", "structure", "section")),
        ("Evidence and clarity", ("evidence", "clarity", "readab")),
    ],
}

METHODS: dict[str, list[dict[str, str]]] = {
    "seo_audit": [
        {"title": "Capture the page", "description": "Fetch the requested URL and the bounded supporting-page sample."},
        {"title": "Apply deterministic checks", "description": "Inspect response, directives, metadata, headings, images and structured data."},
        {"title": "Retain supported findings", "description": "Keep only conclusions linked to captured evidence and order them by severity."},
    ],
    "ai_visibility": [
        {"title": "Inspect machine access", "description": "Review crawler access and the page signals available to answer systems."},
        {"title": "Assess answer readiness", "description": "Measure entity clarity, extractable answers and citation support."},
        {"title": "State the boundary", "description": "Separate on-page readiness from unmeasured live assistant mentions."},
    ],
    "internal_linking": [
        {"title": "Build the observed graph", "description": "Record links and their positions in the captured page sample."},
        {"title": "Test contextual relevance", "description": "Keep a suggestion only when the source passage supports the destination."},
        {"title": "Prepare reviewable placements", "description": "Return the source, target, context and proposed wording together."},
    ],
    "serp_competitor": [
        {"title": "Resolve the query", "description": "Build the search phrase from the verified page identity."},
        {"title": "Capture a dated sample", "description": "Store the returned result positions, titles, domains and URLs."},
        {"title": "Compare supported signals", "description": "Report only visible result and fetched-page evidence with its limits."},
    ],
    "keyword_cluster": [
        {"title": "Collect grounded terms", "description": "Use the verified identity, page copy and saved search evidence."},
        {"title": "Group related intent", "description": "Organize supported phrases without treating model ideas as measured demand."},
        {"title": "Map page roles", "description": "Show which themes fit this page and which need separate review."},
    ],
    "metadata": [
        {"title": "Read current metadata", "description": "Extract the title and description from the captured HTML."},
        {"title": "Measure and validate", "description": "Check presence, length and identity alignment using explicit rules."},
        {"title": "Prepare supported copy", "description": "Show an alternative only when captured facts support it."},
    ],
    "schema_markup": [
        {"title": "Parse every block", "description": "Validate JSON-LD syntax and preserve parser evidence."},
        {"title": "Compare visible entities", "description": "Check names, URLs and types against the visible page."},
        {"title": "Prepare a safe correction", "description": "Use observed facts and keep unconfirmed fields out of the draft."},
    ],
    "content_brief": [
        {"title": "Assemble the evidence", "description": "Reuse the page, verified identity, search sample and keyword themes."},
        {"title": "Build the brief", "description": "Define intent, sections, questions and evidence requirements."},
        {"title": "Validate the handoff", "description": "Score the proposal and expose gaps before editorial use."},
    ],
    "local_seo": [
        {"title": "Resolve the property", "description": "Confirm the resort and destination from corroborating page signals."},
        {"title": "Extract local facts", "description": "Inspect contact, location and structured business information."},
        {"title": "Require verification", "description": "Keep unverified third-party listing claims out of the result."},
    ],
    "content_optimizer": [
        {"title": "Inspect the live content", "description": "Measure the captured copy against the selected page intent."},
        {"title": "Score assessed checks", "description": "Exclude checks that lack enough evidence instead of treating them as failures."},
        {"title": "Build the improvement queue", "description": "Tie every retained action to a section and evidence record."},
    ],
}

PRIORITY_PENALTY = {"critical": 28, "high": 20, "medium": 11, "low": 5}
CLASSIFICATION_FACTOR = {"confirmed": 1.0, "review": 0.7, "opportunity": 0.45, "insufficient": 0.0}

AGENT_ENGINES = {
    "seo_audit": "SEO", "internal_linking": "SEO", "serp_competitor": "SEO",
    "keyword_cluster": "SEO", "metadata": "SEO", "content_brief": "SEO",
    "local_seo": "SEO", "content_optimizer": "SEO",
    "schema_markup": "AEO", "ai_visibility": "GEO",
}


def _number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return max(0, min(100, round(value)))
    return None


def _native_score(detail: dict[str, Any]) -> tuple[int | None, str | None]:
    for key, label in (
        ("site_score", "Native technical audit score"),
        ("overall_score", "Native assessed-check score"),
        ("quality_score", "Validated output-quality score"),
    ):
        score = _number(detail.get(key))
        if score is not None:
            return score, label
    return None, None


def _finding_penalty(finding: dict[str, Any]) -> int:
    base = PRIORITY_PENALTY.get(finding.get("priority"), 8)
    factor = CLASSIFICATION_FACTOR.get(finding.get("classification"), 0.6)
    return round(base * factor)


def _score_areas(agent: str, detail: dict[str, Any], findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if agent == "ai_visibility" and detail.get("dimensions"):
        dimensions = []
        for item in detail["dimensions"][:6]:
            score = _number(item.get("score"))
            if score is not None:
                dimensions.append({
                    "label": str(item.get("dimension", "Readiness")).replace("_", " ").title(),
                    "score": score,
                    "basis": item.get("summary") or "Calculated by the agent's documented readiness rules.",
                })
        if dimensions:
            return dimensions
    if agent == "content_optimizer" and detail.get("assessments"):
        values = {"good": 100, "review": 0}
        assessed = [item for item in detail["assessments"] if item.get("status") != "not_assessed"][:6]
        if assessed:
            return [{
                "label": item.get("label") or str(item.get("key", "Assessment")).replace("_", " ").title(),
                "score": values.get(item.get("status"), 0),
                "basis": item.get("summary") or "Assessed from the captured page.",
            } for item in assessed]

    areas = AGENT_SCORE_AREAS[agent]
    penalties: defaultdict[int, int] = defaultdict(int)
    for finding in findings:
        text = " ".join(str(finding.get(key, "")) for key in ("title", "observation", "action")).casefold()
        matches = [index for index, (_, terms) in enumerate(areas) if any(term in text for term in terms)]
        target = matches[0] if matches else len(areas) - 1
        penalties[target] += _finding_penalty(finding)
    return [{
        "label": label,
        "score": max(0, 100 - penalties[index]),
        "basis": "Reduced only by retained findings mapped to this score area." if penalties[index] else "No retained finding reduced this area in the captured scope.",
    } for index, (label, _) in enumerate(areas)]


def _status(score: int, output_quality: str, task_status: str) -> dict[str, str]:
    if output_quality == "rejected" or task_status in {"failed", "needs_review"}:
        return {"label": "Needs review", "tone": "review"}
    if score >= 85:
        return {"label": "Strong", "tone": "strong"}
    if score >= 70:
        return {"label": "Fair", "tone": "fair"}
    if score >= 50:
        return {"label": "At risk", "tone": "risk"}
    return {"label": "Critical", "tone": "critical"}


def _align_area_average(areas: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    """Keep relative deductions while making equal-weight bars reconcile to the displayed score."""
    if not areas:
        return areas
    current = round(sum(item["score"] for item in areas) / len(areas))
    delta = target - current
    aligned = [{**item, "score": max(0, min(100, item["score"] + delta))} for item in areas]
    # Clamping can leave a small residual. Distribute it one point at a time.
    while round(sum(item["score"] for item in aligned) / len(aligned)) != target:
        direction = 1 if sum(item["score"] for item in aligned) / len(aligned) < target else -1
        candidate = next((item for item in aligned if 0 <= item["score"] + direction <= 100), None)
        if candidate is None:
            break
        candidate["score"] += direction
    return aligned


def _measurements(agent: str, detail: dict[str, Any], capture: dict[str, Any], findings: list[dict[str, Any]]) -> list[dict[str, str]]:
    pages = capture.get("pages", [])
    primary = pages[0] if pages else {}
    values: dict[str, list[tuple[str, Any, str]]] = {
        "seo_audit": [
            ("Pages inspected", detail.get("pages_crawled", len(pages)), "Captured sample"),
            ("HTTP response", primary.get("status_code", "Unavailable"), "Selected page"),
            ("Indexability", primary.get("indexability") or primary.get("indexable") or "Not established", "Captured HTML"),
            ("Retained findings", len(findings), "Evidence threshold met"),
        ],
        "ai_visibility": [
            ("Pages inspected", detail.get("pages_crawled", len(pages)), "Captured sample"),
            ("URLs discovered", detail.get("discovered_url_count", "Unavailable"), "Bounded crawl"),
            ("Readiness dimensions", len(detail.get("dimensions", [])), "Assessed dimensions"),
            ("Retained findings", len(findings), "Evidence threshold met"),
        ],
        "internal_linking": [
            ("Pages mapped", detail.get("pages_crawled", len(detail.get("pages", []))), "Captured sample"),
            ("Observed links", detail.get("observed_edge_count", "Unavailable"), "Internal edges"),
            ("Contextual links", detail.get("contextual_edge_count", "Unavailable"), "Main content"),
            ("Retained opportunities", len(findings), "Context checked"),
        ],
        "serp_competitor": [
            ("Organic results", len(detail.get("organic_results", [])), "Dated SERP sample"),
            ("Pages fetched", sum(bool(item.get("fetched")) for item in detail.get("competitors", [])), "Competitor inspection"),
            ("Questions found", len(detail.get("questions", [])), "Returned SERP features"),
            ("Search intent", detail.get("search_intent", "Not established"), "Agent classification"),
        ],
        "keyword_cluster": [
            ("Input terms", detail.get("input_count", len(detail.get("clusters", []))), "Grounded inputs"),
            ("Unique terms", detail.get("unique_keyword_count", "Unavailable"), "After normalization"),
            ("Theme groups", len(detail.get("clusters", [])), "Planning output"),
            ("Demand data", "Not queried" if not any(item.get("total_volume") for item in detail.get("clusters", [])) else "Available", "Evidence boundary"),
        ],
        "metadata": [
            ("Title length", len(primary.get("title") or ""), "Characters"),
            ("Description length", len(primary.get("meta_description") or ""), "Characters"),
            ("Title present", "Yes" if primary.get("title") else "No", "Captured HTML"),
            ("Description present", "Yes" if primary.get("meta_description") else "No", "Captured HTML"),
        ],
        "schema_markup": [
            ("Schema types", len(primary.get("schema_types", [])), ", ".join(primary.get("schema_types", [])) or "None observed"),
            ("Parser errors", len(primary.get("json_ld_errors", [])), "Captured JSON-LD"),
            ("Schema names", len(primary.get("schema_names", [])), "Identity candidates"),
            ("Retained findings", len(findings), "Evidence threshold met"),
        ],
        "content_brief": [
            ("Quality score", detail.get("quality_score", "Unavailable"), "Proposal quality, not page health"),
            ("Outline sections", len((detail.get("brief") or {}).get("outline", [])), "Draft structure"),
            ("Questions", len((detail.get("brief") or {}).get("faqs", [])), "Draft questions"),
            ("Handoff ready", "Yes" if detail.get("ready_for_handoff") else "No", "Validation state"),
        ],
        "local_seo": [
            ("Phone patterns", len(detail.get("phone_numbers", [])), "Needs owner verification"),
            ("Schema types", len(primary.get("schema_types", [])), "Captured page"),
            ("Property identity", detail.get("identity", "Not established"), "Corroborated page signals"),
            ("External listings", "Not checked", "Current scope"),
        ],
        "content_optimizer": [
            ("Word count", detail.get("word_count", primary.get("word_count", "Unavailable")), "Captured content"),
            ("Checks assessed", detail.get("assessed_checks", len(detail.get("assessments", []))), "Unassessed excluded"),
            ("Checks available", detail.get("total_checks", len(detail.get("assessments", []))), "Configured checks"),
            ("Retained actions", len(detail.get("actions", [])), "Agent output"),
        ],
    }
    return [{"label": label, "value": str(value), "note": note} for label, value, note in values[agent]]


def _effort(finding: dict[str, Any]) -> str:
    text = f"{finding.get('action', '')} {finding.get('title', '')}".casefold()
    if any(term in text for term in ("rebuild", "migration", "template", "architecture", "all pages")):
        return "High"
    if any(term in text for term in ("review", "confirm", "validate", "rewrite", "update")):
        return "Medium"
    return "Low"


def _timeframe(priority: str) -> str:
    return {"critical": "This week", "high": "This week", "medium": "This month", "low": "This quarter"}.get(priority, "Next review")


def build_agent_reports(
    run: Any,
    capture: dict[str, Any],
    cases: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    for case in cases:
        agent = case["agent"]
        task = run.tasks[agent]
        detail = task.result.get("detail", {})
        related = [item for item in findings if item["primary_agent"] == agent or agent in item["supporting_agents"]]
        primary = [item for item in related if item["primary_agent"] == agent]
        areas = _score_areas(agent, detail, primary)
        native_score, native_label = _native_score(detail)
        if native_score is not None and agent not in {"ai_visibility", "content_optimizer"}:
            areas = _align_area_average(areas, native_score)
        calculated_score = round(sum(item["score"] for item in areas) / max(1, len(areas)))
        score = native_score if native_score is not None else calculated_score
        if case.get("output_quality") == "rejected":
            score = 0
        elif task.status in {"failed", "needs_review"}:
            score = min(score, 40)
        status = _status(score, case.get("output_quality", "usable"), task.status)
        management = case.get("management", {})
        evidence_ids = list(dict.fromkeys(
            [eid for item in related for eid in item.get("evidence_ids", [])]
            + management.get("evidence_ids", [])
        ))
        action_items = []
        for item in primary:
            action_items.append({
                "finding_id": item["id"],
                "title": item["title"],
                "action": item["action"],
                "rationale": item["business_relevance"],
                "owner": item["owner"],
                "priority": item["priority"],
                "impact": "High" if item["priority"] in {"critical", "high"} else "Medium" if item["priority"] == "medium" else "Low",
                "effort": _effort(item),
                "timeframe": _timeframe(item["priority"]),
                "steps": [
                    item["action"],
                    item["completion_criteria"],
                    "Rerun this agent on the same URL and compare the saved result.",
                ],
                "done_when": item["completion_criteria"],
            })
        if not action_items:
            for index, action in enumerate(management.get("recommended_actions", [])[:3]):
                action_items.append({
                    "finding_id": None,
                    "title": action,
                    "action": action,
                    "rationale": management.get("why_management_should_care", "Keep the assessment current."),
                    "owner": case["owner"],
                    "priority": "review",
                    "impact": "Review",
                    "effort": "Medium",
                    "timeframe": "Next review",
                    "steps": [action, "Record the reviewer and supporting evidence.", "Rerun this agent if the page changes."],
                    "done_when": management.get("limitation") or "The recommendation has been reviewed and recorded.",
                })
        benchmarks = []
        for eid in evidence_ids:
            item = evidence.get(eid, {})
            if item.get("expected_value"):
                benchmarks.append({
                    "label": item.get("title") or "Evidence condition",
                    "observed": item.get("observed_value") or item.get("observed"),
                    "target": item["expected_value"],
                    "basis": "Captured evidence compared with the stated decision rule.",
                    "evidence_id": eid,
                })
        fix_items = [{
            "evidence_id": eid,
            "title": evidence[eid].get("fix_label") or evidence[eid].get("title") or "Suggested change",
            "context": evidence[eid].get("location") or evidence[eid].get("source_label"),
            "current": evidence[eid].get("excerpt") or evidence[eid].get("observed_value") or evidence[eid].get("observed"),
            "replacement": evidence[eid].get("fix_example"),
            "language": "HTML" if "<" in str(evidence[eid].get("fix_example", "")) else "Text",
        } for eid in evidence_ids if evidence.get(eid, {}).get("fix_example")]
        critical = sum(item.get("priority") == "critical" for item in primary)
        warnings = sum(item.get("priority") in {"high", "medium"} for item in primary)
        reports[agent] = {
            "agent": agent,
            "agent_label": case["agent_label"],
            "heading": case["heading"],
            "score": score,
            "score_status": status,
            "score_basis": native_label or "Project-defined evidence rubric: retained findings reduce the relevant score areas.",
            "score_breakdown": areas,
            "assessed_area_count": len(areas),
            "critical_count": critical,
            "warning_count": warnings,
            "finding_count": len(primary),
            "executive_summary": management.get("issue_identified") or "The agent completed its configured assessment.",
            "management_relevance": management.get("why_management_should_care") or "Review the captured result in its stated scope.",
            "measurements": _measurements(agent, detail, capture, primary),
            "finding_ids": [item["id"] for item in primary],
            "evidence_ids": evidence_ids,
            "benchmarks": benchmarks,
            "action_plan": action_items,
            "fixes": fix_items,
            "success_metrics": [
                {"metric": "Agent score", "current": str(score), "target": "85 or higher", "window": "Next validated rerun", "basis": "Project-defined strong band"},
                {"metric": "Critical findings", "current": str(critical), "target": "0", "window": "After priority fixes", "basis": "Retained findings in this agent"},
                {"metric": "Verified findings", "current": str(len(primary)), "target": "0 unresolved", "window": "Next review cycle", "basis": "Finding completion checks"},
            ],
            "trace": [
                {"step": "Page capture", "status": run.tasks["capture"].status, "reference": run.id, "detail": capture.get("method") or "Shared captured evidence", "at": capture.get("captured_at") or run.created_at},
                {"step": case["agent_label"], "status": task.status, "reference": task.run_id or run.id, "detail": f"{len(evidence_ids)} retained evidence record(s)", "at": task.finished_at or run.updated_at},
            ],
            "method": METHODS[agent],
            "limitations": case.get("limitations", []),
            "output_quality": case.get("output_quality", "usable"),
        }

    scored = [item["score"] for item in reports.values() if item["output_quality"] != "rejected"]
    session_score = round(sum(scored) / len(scored)) if scored else 0
    session = {
        "score": session_score,
        "score_status": _status(session_score, "usable", "complete"),
        "agent_count": len(reports),
        "finding_count": len(findings),
        "critical_count": sum(item.get("priority") == "critical" for item in findings),
        "score_basis": "Equal-weight average of participating agent scores. Each agent exposes its own scoring basis and assessed areas.",
    }
    return reports, session


def build_session_intelligence(
    reports: dict[str, dict[str, Any]],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Turn participating agent outputs into one traceable decision queue."""
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for report in reports.values():
        if report.get("output_quality") != "rejected":
            grouped[AGENT_ENGINES.get(report["agent"], "SEO")].append(report)

    engines = []
    engine_scores: dict[str, int] = {}
    for engine in ("SEO", "AEO", "GEO"):
        members = grouped.get(engine, [])
        if not members:
            continue
        score = round(sum(item["score"] for item in members) / len(members))
        engine_scores[engine] = score
        weakest = min(members, key=lambda item: item["score"])
        strongest = max(members, key=lambda item: item["score"])
        engines.append({
            "engine": engine,
            "score": score,
            "score_status": _status(score, "usable", "complete"),
            "agent_count": len(members),
            "finding_count": sum(item["finding_count"] for item in members),
            "critical_count": sum(item["critical_count"] for item in members),
            "warning_count": sum(item["warning_count"] for item in members),
            "weakest_agent": weakest["agent"],
            "weakest_agent_label": weakest["agent_label"],
            "strongest_agent": strongest["agent"],
            "strongest_agent_label": strongest["agent_label"],
        })

    finding_by_id = {item["id"]: item for item in findings}
    raw_actions = []
    for report in reports.values():
        if report.get("output_quality") == "rejected":
            continue
        engine = AGENT_ENGINES.get(report["agent"], "SEO")
        for action in report.get("action_plan", []):
            raw_actions.append((report, engine, action, finding_by_id.get(action.get("finding_id"))))
    with_findings = [item for item in raw_actions if item[2].get("finding_id")]
    candidates = with_findings if with_findings else raw_actions

    severity_points = {"critical": 45, "high": 36, "medium": 24, "low": 12, "review": 8}
    impact_points = {"High": 24, "Medium": 16, "Low": 8, "Review": 5}
    effort_points = {"Low": 16, "Medium": 10, "High": 4}
    priorities = []
    seen = set()
    for report, engine, action, finding in candidates:
        key = action.get("finding_id") or (report["agent"], action.get("action"))
        if key in seen:
            continue
        seen.add(key)
        severity = action.get("priority", "review")
        impact = action.get("impact", "Review")
        effort = action.get("effort", "Medium")
        weakness = round((100 - engine_scores.get(engine, report["score"])) * 0.15)
        score = min(100, severity_points.get(severity, 8) + impact_points.get(impact, 5) + effort_points.get(effort, 8) + weakness)
        priorities.append({
            "id": f"I-{len(priorities) + 1}",
            "finding_id": action.get("finding_id"),
            "title": action.get("title") or action["action"],
            "action": action["action"],
            "rationale": action.get("rationale") or "This is the next review step retained by the source agent.",
            "risk_if_delayed": (finding or {}).get("business_relevance") or action.get("rationale") or "The observed condition remains unresolved.",
            "agent": report["agent"],
            "agent_label": report["agent_label"],
            "engine": engine,
            "priority": severity,
            "impact": impact,
            "effort": effort,
            "timeframe": action.get("timeframe", "Next review"),
            "owner": action.get("owner", "Review owner"),
            "done_when": action.get("done_when", "The source agent's completion check passes on rerun."),
            "priority_score": score,
            "score_factors": {
                "severity": severity_points.get(severity, 8),
                "impact": impact_points.get(impact, 5),
                "effort": effort_points.get(effort, 8),
                "engine_weakness": weakness,
            },
        })
    priorities.sort(key=lambda item: (-item["priority_score"], item["title"]))
    for rank, item in enumerate(priorities, 1):
        item["rank"] = rank
        item["id"] = f"I-{rank}"
    priorities = priorities[:10]

    delivery = {"now": [], "next": [], "later": []}
    for item in priorities:
        bucket = "now" if item["timeframe"] == "This week" else "next" if item["timeframe"] == "This month" else "later"
        delivery[bucket].append(item["id"])
    missing = [engine for engine in ("SEO", "AEO", "GEO") if engine not in grouped]
    weakest_engine = min(engines, key=lambda item: item["score"]) if engines else None
    top = priorities[0] if priorities else None
    return {
        "engine_scores": engines,
        "missing_engines": missing,
        "decision_summary": (
            f"Start with: {top['action']} This is the highest-ranked next step from the agents that ran."
            if top else "No retained action requires implementation. Keep this result as a dated baseline and rerun after the page changes."
        ),
        "constraint": ({"engine": weakest_engine["engine"], "score": weakest_engine["score"]} if weakest_engine else None),
        "priorities": priorities,
        "quick_win_ids": [item["id"] for item in priorities if item["effort"] == "Low"][:3],
        "risk_ids": [item["id"] for item in priorities if item["priority"] in {"critical", "high"}][:4],
        "delivery": delivery,
        "method": "Priorities are calculated from retained severity, stated impact, estimated effort and the participating engine score. Every item links to its source agent and completion check.",
    }
