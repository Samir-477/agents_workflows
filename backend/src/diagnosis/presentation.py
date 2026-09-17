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
    "question_discovery": [
        ("Observed question evidence", ("observed", "question", "search")),
        ("Topic coverage", ("coverage", "answer", "topic")),
        ("Intent and journey mapping", ("intent", "journey", "customer")),
        ("Cross-engine handoff", ("seo", "aeo", "geo", "handoff")),
    ],
    "answer_gap": [
        ("Directness", ("direct", "answer", "question")),
        ("Completeness", ("complete", "missing", "partial")),
        ("Extractability", ("extract", "passage", "section")),
        ("Factual support", ("fact", "evidence", "support")),
    ],
    "answer_optimization": [
        ("Grounding fidelity", ("grounded", "unsupported", "passage")),
        ("Draft coverage", ("draft", "coverage", "partial")),
        ("Length compliance", ("length", "word", "target")),
        ("Handoff readiness", ("review", "approval", "editorial")),
    ],
    "faq_intelligence": [
        ("Category coverage", ("covered", "category", "ready")),
        ("Editorial readiness", ("review", "editorial", "draft")),
        ("Verified gaps", ("missing", "not covered", "gap")),
        ("Observed demand", ("observed", "question", "surfaced")),
    ],
    "question_intent": [
        ("High-value coverage", ("transactional", "comparison", "high-value")),
        ("Funnel distribution", ("distribution", "share", "informational")),
        ("Business-impact priority", ("weighted", "priority", "impact")),
        ("Content-strategy routing", ("route", "handoff", "strategy")),
    ],
    "answer_structure": [
        ("Direct opening", ("direct", "lead", "opening", "requested information")),
        ("Self-containment", ("extract", "surrounding", "self-contained")),
        ("Heading context", ("heading", "section", "context", "topic")),
        ("Format suitability", ("format", "list", "table", "sequence")),
        ("Concision", ("length", "word", "concise")),
    ],
    "aeo_opportunity": [
        ("Evidence confidence", ("observed", "evidence", "confidence", "verified")),
        ("Answer deficiency", ("missing", "partial", "gap", "answer")),
        ("Journey relevance", ("journey", "evaluate", "book", "manage")),
        ("Obstruction and dependencies", ("structure", "extract", "heading", "blocked", "depend")),
        ("Delivery fit", ("priority", "effort", "queue", "roadmap")),
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
    "question_discovery": [
        {"title": "Resolve the resort subject", "description": "Use the shared page capture to identify the property, destination and page role."},
        {"title": "Collect and consolidate questions", "description": "Combine captured question headings with a dated Google question sample when available, then deduplicate variants."},
        {"title": "Map coverage and intent", "description": "Classify intent, journey stage and page coverage while preserving observed versus inferred provenance."},
        {"title": "Prepare connected handoffs", "description": "Send validated themes to SEO, answer checks to AEO and prompt seeds to GEO without claiming unmeasured demand."},
    ],
    "answer_gap": [
        {"title": "Reuse observed questions", "description": "Consume saved Question Discovery output or perform bounded discovery inside a standalone run."},
        {"title": "Retrieve answer passages", "description": "Locate the strongest captured passage for each observed question without treating its heading as an answer."},
        {"title": "Assess answer quality", "description": "Measure directness, completeness, extractability and factual support with explicit rules."},
        {"title": "Retain verified gaps", "description": "Route only missing and incomplete observed answers to Answer Optimization."},
    ],
    "answer_optimization": [
        {"title": "Reuse verified gaps", "description": "Consume saved Answer Gap output or perform bounded discovery and gap analysis inside a standalone run."},
        {"title": "Draft from the retained passage only", "description": "Compress a partial answer's own captured passage into a 40-60 word direct answer; a missing answer has no passage to draft from."},
        {"title": "Validate every draft", "description": "Reject any draft that introduces a word absent from its source passage, falling back to a condensed excerpt of that passage instead."},
        {"title": "Route what cannot be drafted", "description": "Give a missing answer a fact-gathering action for the property team rather than an invented answer."},
    ],
    "faq_intelligence": [
        {"title": "Fix the audit taxonomy", "description": "Use a set hospitality FAQ categories rather than inventing one per resort."},
        {"title": "Classify every discovered question", "description": "Sort observed and inferred questions into that taxonomy independently of their discovery-time intent label."},
        {"title": "Take the strongest evidence per category", "description": "Prefer a validated Answer Optimization draft, then an Answer Gap answered passage, before treating a category as covered."},
        {"title": "Route uncovered categories", "description": "Give a category with no verified answer a fact-gathering action instead of a fabricated FAQ entry."},
    ],
    "question_intent": [
        {"title": "Separate stage, intent and topic", "description": "Classify each question across three distinct dimensions instead of combining them into one ambiguous label."},
        {"title": "Report observed-question distribution", "description": "Measure the journey-stage mix from observed questions only; retain inferred questions as separate planning hypotheses."},
        {"title": "Sequence verified gaps", "description": "Reorder Answer Gap's missing and partial answers using a transparent stage heuristic without claiming measured commercial impact."},
        {"title": "Route each stage", "description": "Recommend the specialist best suited to each observed journey stage."},
    ],
    "answer_structure": [
        {"title": "Reuse retained answers", "description": "Inspect only passages Answer Gap classified as answered or partial."},
        {"title": "Locate with confidence", "description": "Map each retained passage to a server-HTML block and withhold a score when the match is not reliable."},
        {"title": "Classify the question", "description": "Choose format expectations for yes/no, value, policy, steps, comparison, list, definition, location or explanatory answers."},
        {"title": "Score five dimensions", "description": "Apply disclosed weights to direct opening, self-containment, heading context, format suitability and concision."},
        {"title": "Retain structure work", "description": "Keep only answer blocks that need restructuring without changing Answer Gap's factual verdict."},
    ],
    "aeo_opportunity": [
        {"title": "Reuse connected evidence", "description": "Consume question, gap, structure, FAQ, journey and optional optimized-answer results from this session."},
        {"title": "Deduplicate by lineage", "description": "Collapse correlated evidence into one opportunity without rewarding the number of contributing agents."},
        {"title": "Separate implementation from research", "description": "Require observed question evidence for delivery work and keep inferred hypotheses in a research-only queue."},
        {"title": "Model dependencies", "description": "Block content production when approved property facts or another prerequisite is missing."},
        {"title": "Sequence delivery", "description": "Use disclosed evidence, deficiency, journey, obstruction, dependency and effort factors to assign Now, Next, Later or Blocked."},
    ],
}

PRIORITY_PENALTY = {"critical": 28, "high": 20, "medium": 11, "low": 5}
CLASSIFICATION_FACTOR = {"confirmed": 1.0, "review": 0.7, "opportunity": 0.45, "insufficient": 0.0}

AGENT_ENGINES = {
    "seo_audit": "SEO", "internal_linking": "SEO", "serp_competitor": "SEO",
    "keyword_cluster": "SEO", "metadata": "SEO", "content_brief": "SEO",
    "local_seo": "SEO", "content_optimizer": "SEO",
    "schema_markup": "AEO", "ai_visibility": "GEO",
    "question_discovery": "AEO", "answer_gap": "AEO", "answer_optimization": "AEO", "faq_intelligence": "AEO", "question_intent": "AEO", "answer_structure": "AEO", "aeo_opportunity": "AEO",
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
        ("question_coverage_score", "Question coverage across the assessed discovery set"),
        ("answer_readiness_score", "Answer readiness across assessable observed questions"),
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
    if output_quality == "rejected":
        return {"label": "Excluded from use", "tone": "review"}
    if task_status in {"failed", "needs_review"}:
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
        "question_discovery": [
            ("Questions discovered", len(detail.get("questions", [])), "Observed and labelled inferred candidates"),
            ("Observed questions", detail.get("observed_question_count", 0), "Page or Google question evidence"),
            ("Research hypotheses", detail.get("inferred_question_count", 0), "Planning candidates excluded from page findings"),
            ("Answer Gap candidates", len(detail.get("answer_gap_candidate_ids", [])), "Observed questions awaiting answer validation"),
        ],
        "answer_gap": [
            ("Observed questions assessed", detail.get("question_count", 0), "Inferred hypotheses excluded"),
            ("Answered", detail.get("answered_count", 0), "Direct usable passage retained"),
            ("Partial answers", detail.get("partial_count", 0), "Needs completion"),
            ("Missing answers", detail.get("missing_count", 0), "No matching passage retained"),
        ],
        "answer_optimization": [
            ("Verified gaps received", detail.get("gap_count", 0), "From Answer Gap"),
            ("Drafted answers", detail.get("drafted_count", 0), "Grounded and word-checked"),
            ("Auto-condensed fallbacks", detail.get("fallback_count", 0), "Draft rejected or unavailable this run"),
            ("Needs property facts", detail.get("needs_facts_count", 0), "No retained passage to draft from"),
        ],
        "faq_intelligence": [
            ("Categories covered", detail.get("ready_count", 0), f"Of {detail.get('assessed_category_count', 0)} categories with observed questions"),
            ("Needs editorial review", detail.get("needs_review_count", 0), "Captured but not yet complete"),
            ("Verified gaps", detail.get("not_covered_count", 0), "Observed question checked, no answer found"),
            ("No demand observed", detail.get("no_question_count", 0), "No observed question in this category"),
        ],
        "question_intent": [
            ("Questions classified", detail.get("question_count", 0), "Observed and inferred"),
            ("High-value questions", detail.get("high_value_question_count", 0), "Transactional or comparison intent"),
            ("Reprioritized gaps", detail.get("reprioritized_gap_count", 0), "High-value gaps needing action first"),
            ("Funnel stages present", sum(row["count"] > 0 for row in detail.get("distribution", [])), "Out of 5 fixed stages"),
        ],
        "answer_structure": [
            ("Answers retained", detail.get("assessed_answer_count", 0), "Answered or partial passages from Answer Gap"),
            ("Blocks scored", detail.get("scored_answer_count", 0), "Confidently mapped to captured server HTML"),
            ("Unable to locate", detail.get("unable_to_locate_count", 0), "Score withheld below the locator threshold"),
            ("Locator confidence", f"{detail.get('assessment_confidence_score')}%" if detail.get("assessment_confidence_score") is not None else "Not scored", "Average across located blocks"),
        ],
        "aeo_opportunity": [
            ("Implementation queue", detail.get("implementation_count", 0), "Observed and dependency-ready lineages"),
            ("Blocked", detail.get("blocked_count", 0), "A prerequisite must be resolved first"),
            ("Research queue", detail.get("research_count", 0), "Inferred hypotheses excluded from implementation"),
            ("Observed assessed", f"{detail.get('assessed_question_count', 0)}/{detail.get('observed_question_count', 0)}", "Observed question lineages checked by Answer Gap"),
        ],
    }
    return [{"label": label, "value": str(value), "note": note} for label, value, note in values[agent]]


def _clip_step(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _effort(finding: dict[str, Any]) -> str:
    text = f"{finding.get('action', '')} {finding.get('title', '')}".casefold()
    if any(term in text for term in ("rebuild", "migration", "template", "architecture", "all pages")):
        return "High"
    if any(term in text for term in ("review", "confirm", "validate", "rewrite", "update")):
        return "Medium"
    return "Low"


def _timeframe(priority: str) -> str:
    return {"critical": "This week", "high": "This week", "medium": "This month", "low": "This quarter"}.get(priority, "Next review")


def _success_metrics(agent: str, detail: dict[str, Any], score: int, critical: int, findings: int, measurements: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    if agent == "question_discovery":
        return [
            {"metric": "Observed source types", "current": str(len(detail.get("evidence_quality", {}).get("observed_source_types", []))), "target": "Reviewed for sufficiency", "window": "Before downstream diagnosis", "basis": "Distinct dated sources, excluding the planning framework"},
            {"metric": "Observed questions", "current": str(detail.get("observed_question_count", 0)), "target": "Approved, merged or rejected", "window": "Discovery review", "basis": "Page headings and dated search-question features only"},
            {"metric": "Answer Gap candidates", "current": str(len(detail.get("answer_gap_candidate_ids", []))), "target": "Validated by Answer Gap", "window": "Next analysis", "basis": "Coverage hints are routing signals, not website findings"},
        ]
    if agent == "answer_gap":
        return [
            {"metric": "Observed questions assessed", "current": str(detail.get("question_count", 0)), "target": "Reassessed after approved changes", "window": "Next validated rerun", "basis": "Inferred hypotheses excluded"},
            {"metric": "Answer readiness", "current": str(detail.get("answer_readiness_score", "Not scored")), "target": "85 or higher", "window": "Next validated rerun", "basis": "Observed questions with assessable captured page evidence"},
            {"metric": "Missing answers", "current": str(detail.get("missing_count", 0)), "target": "0 unresolved", "window": "After approved content changes", "basis": "Verified observed-question gaps"},
            {"metric": "Partial answers", "current": str(detail.get("partial_count", 0)), "target": "0 unresolved", "window": "After approved content changes", "basis": "Captured passages below the completeness threshold"},
        ]
    if agent == "answer_optimization":
        return [
            {"metric": "Optimization coverage", "current": str(detail.get("optimization_coverage_score", "Not scored")), "target": "85 or higher", "window": "Next validated rerun", "basis": "Share of draftable gaps that passed grounding and length validation"},
            {"metric": "Drafted answers ready for review", "current": str(detail.get("drafted_count", 0)), "target": "Reviewed and approved", "window": "Editorial handoff", "basis": "Grounded, word-checked drafts"},
            {"metric": "Gaps needing property facts", "current": str(detail.get("needs_facts_count", 0)), "target": "0 unresolved", "window": "After property-fact confirmation", "basis": "No captured passage supports these questions yet"},
        ]
    if agent == "faq_intelligence":
        return [
            {"metric": "FAQ coverage", "current": str(detail.get("faq_coverage_score", "Not scored")), "target": "85 or higher", "window": "Next validated rerun", "basis": f"Covered categories out of {detail.get('assessed_category_count', 0)} with observed questions"},
            {"metric": "Categories needing editorial review", "current": str(detail.get("needs_review_count", 0)), "target": "0 unresolved", "window": "After Answer Optimization drafts", "basis": "Captured but not yet a complete direct answer"},
            {"metric": "Verified content gaps", "current": str(detail.get("not_covered_count", 0)), "target": "0 unresolved", "window": "After property-fact confirmation", "basis": "Observed question checked against the page with no answer found"},
        ]
    if agent == "question_intent":
        return [
            {"metric": "High-value answer readiness", "current": str(detail.get("high_value_readiness_score", "Not scored")), "target": "85 or higher", "window": "Next validated rerun", "basis": "Transactional and comparison questions with a captured answer"},
            {"metric": "Reprioritized high-value gaps", "current": str(detail.get("reprioritized_gap_count", 0)), "target": "0 unresolved", "window": "Before lower-value gaps", "basis": "Missing or partial answers to funnel-critical questions"},
            {"metric": "Questions classified", "current": str(detail.get("question_count", 0)), "target": "Reassessed after Question Discovery changes", "window": "Next validated rerun", "basis": "Observed and inferred, five-stage funnel taxonomy"},
        ]
    if agent == "answer_structure":
        return [
            {"metric": "Answer structure readiness", "current": str(detail.get("answer_structure_score") if detail.get("answer_structure_score") is not None else "Not scored"), "target": "85 or higher", "window": "Next validated rerun", "basis": "Weighted direct opening, self-containment, heading context, format suitability and concision"},
            {"metric": "Weak answer blocks", "current": str(detail.get("weak_count", 0)), "target": "0 unresolved", "window": "After approved restructuring", "basis": "Retained passages below the structure threshold"},
            {"metric": "Unlocated answer blocks", "current": str(detail.get("unable_to_locate_count", 0)), "target": "0 unresolved", "window": "Before accepting the score", "basis": "A score is withheld when a retained passage cannot be mapped confidently"},
            {"metric": "Locator confidence", "current": str(detail.get("assessment_confidence_score") if detail.get("assessment_confidence_score") is not None else "Not scored"), "target": "70 or higher", "window": "Current capture", "basis": "Average passage-to-section match confidence"},
        ]
    if agent == "aeo_opportunity":
        return [
            {"metric": "Observed-answer readiness", "current": str(detail.get("aeo_opportunity_score") if detail.get("aeo_opportunity_score") is not None else "Not scored"), "target": "85 or higher", "window": "Next validated rerun", "basis": "Sufficiently evidenced observed questions without unresolved AEO work"},
            {"metric": "Implementation opportunities", "current": str(detail.get("implementation_count", 0)), "target": "0 unresolved", "window": "Across delivery windows", "basis": "One task per observed stable question lineage"},
            {"metric": "Blocked opportunities", "current": str(detail.get("blocked_count", 0)), "target": "0 blocked", "window": "Before content production", "basis": "Missing facts or prerequisites are explicit dependencies"},
            {"metric": "Research hypotheses", "current": str(detail.get("research_count", 0)), "target": "Validated or rejected", "window": "Research review", "basis": "Inferred demand is never scheduled as implementation work"},
        ]
    # Leading with this agent's own headline measurement stops all eleven
    # reports from presenting an identical success table.
    leading = [
        {
            "metric": measurements[0]["label"],
            "current": measurements[0]["value"],
            "target": "Re-measured on the next validated run",
            "window": "Next validated rerun",
            "basis": measurements[0]["note"],
        }
    ] if measurements else []
    return [
        *leading,
        {"metric": "Agent score", "current": str(score), "target": "Maintain 85+" if score >= 85 else "85 or higher", "window": "Next validated rerun", "basis": "Project-defined strong band"},
        {"metric": "Critical findings", "current": str(critical), "target": "0", "window": "After priority fixes", "basis": "Retained findings in this agent"},
        {"metric": "Verified findings", "current": str(findings), "target": "0 unresolved", "window": "Next review cycle", "basis": "Finding completion checks"},
    ]


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
        if agent == "question_discovery":
            native_score = _number(detail.get("discovery_confidence_score"))
            native_label = "Discovery confidence from source provenance and observed question evidence"
        elif agent == "answer_gap":
            native_score = _number(detail.get("answer_readiness_score"))
            native_label = "Answer readiness across observed questions with assessable captured evidence"
            # No assessable observed question is a "nothing to assess" state,
            # not a failure. Forcing it to 0 read as every answer having
            # failed, while the breakdown below still showed the default
            # unreduced areas — the two contradicted each other. Falling
            # through to the calculated score matches every other
            # assessment-only agent's "no retained finding" convention.
        elif agent == "answer_optimization":
            native_score = _number(detail.get("optimization_coverage_score"))
            native_label = "Share of draftable gaps that produced a grounded, validated answer"
        elif agent == "faq_intelligence":
            native_score = _number(detail.get("faq_coverage_score"))
            native_label = f"Categories covered out of {detail.get('assessed_category_count', 0)} assessed hospitality FAQ categories"
        elif agent == "question_intent":
            native_score = _number(detail.get("high_value_readiness_score"))
            native_label = "Answer readiness across observed transactional and comparison questions"
        elif agent == "answer_structure":
            native_score = _number(detail.get("answer_structure_score"))
            native_label = "Weighted structural quality across confidently located retained answer blocks"
        elif agent == "aeo_opportunity":
            native_score = _number(detail.get("aeo_opportunity_score"))
            native_label = "Share of sufficiently evidenced observed questions without unresolved AEO work"
        if native_score is not None and agent not in {"ai_visibility", "content_optimizer"}:
            areas = _align_area_average(areas, native_score)
        calculated_score = round(sum(item["score"] for item in areas) / max(1, len(areas)))
        score = native_score if native_score is not None else calculated_score
        no_measurement_agents = {"answer_gap", "answer_optimization", "faq_intelligence", "question_intent", "answer_structure", "aeo_opportunity"}
        # A rejected output is excluded from the session average and from the
        # decision queue already. Zeroing it here only contradicted the score
        # breakdown, which still showed the measured areas.
        if task.status in {"failed", "needs_review"}:
            score = min(score, 40)
        status = _status(score, case.get("output_quality", "usable"), task.status)
        if agent == "question_discovery" and score < 70 and case.get("output_quality") != "rejected":
            status = {"label": "Evidence limited", "tone": "review"}
        if agent == "answer_gap" and not detail.get("question_count") and case.get("output_quality") != "rejected":
            status = {"label": "Evidence limited", "tone": "review"}
        if agent == "answer_optimization" and detail.get("optimization_coverage_score") is None and case.get("output_quality") != "rejected":
            # Covers both "nothing to draft" and "everything hit a provider
            # outage or an empty model response" — neither means the score
            # below (a calculated fallback) reflects a measured result.
            status = {"label": "Evidence limited", "tone": "review"}
        if agent == "faq_intelligence" and not detail.get("not_covered_count") and detail.get("no_question_count") and detail.get("assessed_category_count", 0) == 0 and case.get("output_quality") != "rejected":
            # A low score here can mean "most categories have a confirmed
            # missing answer" or "most categories never had an observed
            # question surface at all" — a discovery-coverage limitation, not
            # a proven content fault. Zero verified gaps means it's the latter.
            status = {"label": "Evidence limited", "tone": "review"}
        if agent == "question_intent" and detail.get("high_value_readiness_score") is None and case.get("output_quality") != "rejected":
            # No observed transactional or comparison question this run means
            # no assessable high-value demand surfaced, not that this
            # resort's funnel-critical questions all went unanswered.
            status = {"label": "Evidence limited", "tone": "review"}
        if agent == "answer_structure" and detail.get("answer_structure_score") is None and case.get("output_quality") != "rejected":
            status = {"label": "Evidence limited", "tone": "review"}
        if agent == "aeo_opportunity" and detail.get("aeo_opportunity_score") is None and case.get("output_quality") != "rejected":
            status = {"label": "Evidence limited", "tone": "review"}
        is_unscored = (
            (agent in no_measurement_agents and native_score is None)
            or (agent == "question_discovery" and not detail.get("observed_question_count"))
        )
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
                # The card already shows the action and prints the completion
                # check under "Done when", so the steps locate and verify the
                # work instead of restating either of them.
                "steps": [
                    f"Open the retained evidence for this finding: {_clip_step(item['observation'])}",
                    item["action"],
                    "Rerun this agent on the same URL and compare the saved result.",
                ],
                "done_when": item["completion_criteria"],
            })
        if not action_items and agent not in {"question_discovery", "answer_gap"}:
            for index, action in enumerate(management.get("recommended_actions", [])[:3]):
                action_items.append({
                    "finding_id": None,
                    "title": action,
                    "action": action,
                    # This paragraph is already the report's management
                    # relevance. Printing it under all three actions repeated
                    # the same answer three times in one section.
                    "rationale": management.get("why_management_should_care", "Keep the assessment current.") if index == 0 else "",
                    "owner": case["owner"],
                    "priority": "review",
                    "impact": "Review",
                    "effort": "Medium",
                    "timeframe": "Next review",
                    # The action is already this card's heading. Steps add the
                    # review path instead of repeating it, and the completion
                    # check is a real decision gate rather than the scope
                    # limitation, which now belongs in the limitations block.
                    "steps": [
                        f"Review the observations {case['agent_label']} retained for this resort page.",
                        "Record the decision, the reviewer and the date against this result.",
                    ],
                    "done_when": f"{case['owner']} has recorded an accept, revise or reject decision and a rerun of {case['agent_label']} reflects it.",
                })
        measurements = _measurements(agent, detail, capture, primary)
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
        if agent == "question_discovery":
            benchmarks = []
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
            "executive_summary": _clip_step(management.get("issue_identified") or "The agent completed its configured assessment.", 360),
            "management_relevance": _clip_step(management.get("why_management_should_care") or "Review the captured result in its stated scope.", 320),
            "measurements": measurements,
            "finding_ids": [item["id"] for item in primary],
            "evidence_ids": evidence_ids,
            "benchmarks": benchmarks,
            "action_plan": action_items,
            "fixes": fix_items,
            "success_metrics": _success_metrics(agent, detail, score, critical, len(primary), measurements),
            "trace": [
                {"step": "Page capture", "status": run.tasks["capture"].status, "reference": run.id, "detail": capture.get("method") or "Shared captured evidence", "at": capture.get("captured_at") or run.created_at},
                {"step": case["agent_label"], "status": task.status, "reference": task.run_id or run.id, "detail": f"{len(evidence_ids)} retained evidence record(s)", "at": task.finished_at or run.updated_at},
            ],
            "method": METHODS[agent],
            "limitations": case.get("limitations") or ([management["limitation"]] if management.get("limitation") else []),
            "output_quality": case.get("output_quality", "usable"),
            "question_landscape": detail.get("questions", []) if agent == "question_discovery" else [],
            "question_clusters": detail.get("clusters", []) if agent == "question_discovery" else [],
            "discovery_confidence_score": detail.get("discovery_confidence_score") if agent == "question_discovery" else None,
            "score_kind": "unscored" if is_unscored else ("evidence_confidence" if agent == "question_discovery" else "readiness"),
            "evidence_quality": detail.get("evidence_quality") if agent == "question_discovery" else None,
            "source_ledger": detail.get("source_ledger", []) if agent == "question_discovery" else [],
            "answer_gap_candidate_ids": detail.get("answer_gap_candidate_ids", []) if agent == "question_discovery" else [],
            "recommended_agent_handoffs": detail.get("recommended_agent_handoffs", []) if agent in {"question_discovery", "answer_gap"} else [],
            "answer_coverage": detail.get("assessments", []) if agent == "answer_gap" else [],
            "assessment_confidence_score": detail.get("assessment_confidence_score") if agent in {"answer_gap", "answer_structure", "aeo_opportunity"} else None,
            "optimized_answers": detail.get("optimized_answers", []) if agent == "answer_optimization" else [],
            "optimization_coverage_score": detail.get("optimization_coverage_score") if agent == "answer_optimization" else None,
            "faq_entries": detail.get("faq_entries", []) if agent == "faq_intelligence" else [],
            "faq_coverage_score": detail.get("faq_coverage_score") if agent == "faq_intelligence" else None,
            "intent_distribution": detail.get("distribution", []) if agent == "question_intent" else [],
            "reprioritized_gaps": detail.get("reprioritized_gaps", []) if agent == "question_intent" else [],
            "content_strategy": detail.get("content_strategy", []) if agent == "question_intent" else [],
            "high_value_readiness_score": detail.get("high_value_readiness_score") if agent == "question_intent" else None,
            "structure_entries": detail.get("structure_entries", []) if agent == "answer_structure" else [],
            "answer_structure_score": detail.get("answer_structure_score") if agent == "answer_structure" else None,
            "aeo_opportunities": detail.get("opportunities", []) if agent == "aeo_opportunity" else [],
            "aeo_research_opportunities": detail.get("research_opportunities", []) if agent == "aeo_opportunity" else [],
            "aeo_roadmap": detail.get("roadmap", {}) if agent == "aeo_opportunity" else {},
            "aeo_opportunity_score": detail.get("aeo_opportunity_score") if agent == "aeo_opportunity" else None,
        }

    readiness_scores = [item["score"] for item in reports.values() if item["output_quality"] != "rejected" and item.get("score_kind") == "readiness"]
    evidence_scores = [item["score"] for item in reports.values() if item["output_quality"] != "rejected" and item.get("score_kind") == "evidence_confidence"]
    scored = readiness_scores or evidence_scores
    session_score = round(sum(scored) / len(scored)) if scored else 0
    session_status = _status(session_score, "usable", "complete") if scored else {"label": "Evidence limited", "tone": "review"}
    session = {
        "score": session_score,
        "score_status": session_status,
        "agent_count": len(reports),
        "finding_count": len(findings),
        "critical_count": sum(item.get("priority") == "critical" for item in findings),
        "score_basis": ("Equal-weight average of participating readiness scores; planning-agent evidence confidence is shown separately." if readiness_scores else ("No readiness specialist participated; this value reflects planning-agent evidence confidence only." if evidence_scores else "No participating agent produced enough observed evidence for a scored assessment.")),
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
        readiness_members = [item for item in members if item.get("score_kind") == "readiness"]
        evidence_members = [item for item in members if item.get("score_kind") == "evidence_confidence"]
        scored_members = readiness_members or evidence_members
        score = round(sum(item["score"] for item in scored_members) / len(scored_members)) if scored_members else 0
        engine_scores[engine] = score
        ranked_members = scored_members or members
        weakest = min(ranked_members, key=lambda item: item["score"])
        strongest = max(ranked_members, key=lambda item: item["score"])
        engines.append({
            "engine": engine,
            "score": score,
            "score_status": _status(score, "usable", "complete") if scored_members else {"label": "Evidence limited", "tone": "review"},
            "agent_count": len(members),
            "finding_count": sum(item["finding_count"] for item in members),
            "critical_count": sum(item["critical_count"] for item in members),
            "warning_count": sum(item["warning_count"] for item in members),
            "weakest_agent": weakest["agent"],
            "weakest_agent_label": weakest["agent_label"],
            "strongest_agent": strongest["agent"],
            "strongest_agent_label": strongest["agent_label"],
            "score_kind": "readiness" if readiness_members else ("evidence_confidence" if evidence_members else "unscored"),
        })

    finding_by_id = {item["id"]: item for item in findings}
    raw_actions = []
    for report in reports.values():
        if report.get("output_quality") == "rejected":
            continue
        engine = AGENT_ENGINES.get(report["agent"], "SEO")
        for action in report.get("action_plan", []):
            raw_actions.append((report, engine, action, finding_by_id.get(action.get("finding_id"))))
    # Assessment and monitoring guidance belongs in the source report. The
    # intelligence queue contains implementation work backed by a retained
    # finding only, otherwise one sentence is repeated across every section.
    candidates = [item for item in raw_actions if item[2].get("finding_id")]

    severity_points = {"critical": 45, "high": 36, "medium": 24, "low": 12, "review": 8}
    impact_points = {"High": 24, "Medium": 16, "Low": 8, "Review": 5}
    effort_points = {"Low": 16, "Medium": 10, "High": 4}
    priorities = []
    seen = set()
    seen_text = set()
    for report, engine, action, finding in candidates:
        key = action.get("finding_id") or (report["agent"], action.get("action"))
        if key in seen:
            continue
        # Two agents can retain separate findings that resolve to the same
        # sentence. Deduplicating on the finding id alone let that sentence
        # appear several times in one decision queue.
        text = " ".join(str(action.get("action") or "").split()).casefold()
        if text and text in seen_text:
            continue
        seen.add(key)
        seen_text.add(text)
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
    handoffs = []
    for report in reports.values():
        for handoff in report.get("recommended_agent_handoffs", []):
            handoffs.append({**handoff, "source_agent": report["agent"], "source_agent_label": report["agent_label"], "engine": AGENT_ENGINES.get(report["agent"], "SEO")})
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
        "recommended_agent_handoffs": handoffs,
        "method": "Priorities are calculated from retained severity, stated impact, estimated effort and the participating engine score. Every item links to its source agent and completion check.",
    }
