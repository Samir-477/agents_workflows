# SEO/AEO Audit Agent - Automation Architecture Approaches

Last reviewed: 2026-08-28

## Why this document exists

This document keeps the main automation approaches for our SEO/AEO Audit Agent in one place. It compares their fit for our actual workflow rather than selecting a framework because it is marketed as "agentic."

Our audit has a mostly predictable process:

```text
Accept URL and context
        |
        v
Crawl the website
        |
        v
Extract structured page facts
        |
        v
Run deterministic audit rules
        |
        v
Run cross-page analysis
        |
        v
Prioritize findings
        |
        v
Generate explanations and suggested fixes
        |
        v
Validate and publish the report
```

The process contains two different kinds of automation:

1. **Job automation** - starting a crawl, running it outside the web request, tracking progress, retrying failures, persisting state, and returning the report.
2. **Reasoning automation** - using an LLM to explain evidence, group findings, adapt the report to business context, and draft fixes.

A framework choice should account for both. LangChain provides model, tool, agent, and structured-output abstractions, while LangGraph supplies lower-level workflow state and orchestration. Neither replaces the crawler, SEO rule engine, database, or background execution environment.

## Non-negotiable architecture rule

Regardless of framework:

> Code collects and verifies SEO facts. The LLM interprets those facts and drafts recommendations.

The model must not decide whether a page returned HTTP 404, whether a canonical tag exists, or how many H1 elements were found. Those observations come from normal code and are stored as evidence.

## Evaluation criteria

Each approach is evaluated against:

- MVP development speed;
- deterministic behavior;
- long-running audit support;
- retries and recovery;
- progress reporting;
- typed state and structured outputs;
- LLM flexibility;
- observability and debugging;
- infrastructure requirements;
- framework lock-in; and
- suitability for future human-approved fixes.

## Summary comparison

| Approach | Automation | Control | Setup | Best use | MVP fit |
|---|---:|---:|---:|---|---:|
| Plain Python pipeline + worker | High | Very high | Low | Fastest reliable audit MVP | Strong |
| LangGraph workflow + LangChain LLM nodes | High | Very high | Medium | Hybrid deterministic/AI workflow | **Best overall** |
| Free-form LangChain agent controlling tools | Medium | Low | Medium | Unpredictable research tasks | Weak |
| CrewAI Flow with optional crews | High | Medium | Medium | Role-oriented agent demos and workflows | Reasonable |
| PydanticAI + typed graph/workflow | High | High | Medium | Type-safe Python/LLM applications | Strong alternative |
| Temporal + an LLM framework | Very high | Very high | High | Durable production workflows at scale | Later-stage |

## Approach 1: Plain Python pipeline plus a background worker

### Shape

```text
FastAPI endpoint
      |
      v
Create Audit database row
      |
      v
Background worker claims audit
      |
      v
crawl() -> extract() -> rules() -> score() -> report()
      |
      v
Save result and mark complete
```

The workflow is implemented with ordinary Python functions. A worker runs the audit outside the HTTP request and polls queued audit rows in Supabase Postgres. Celery and a broker can be introduced when distributed workers are genuinely needed.

Celery is a task queue that sends work through a broker to worker processes and can track task state and results. This is useful for horizontal scaling, but it also introduces broker and worker infrastructure that a first local MVP may not need. See the [official Celery introduction](https://docs.celeryq.dev/en/stable/getting-started/introduction.html).

### Advantages

- Smallest dependency surface.
- Very easy to test each step.
- No agent framework controls factual audit logic.
- Lowest framework lock-in.
- Easy to understand for a mentor or new contributor.
- LLM provider can be called directly at the final reporting step.

### Disadvantages

- We must implement workflow state transitions ourselves.
- Retries, resumability, streaming progress, and branching need explicit code.
- Human approval and workflow replay become more work later.

### Suitable when

- We want the quickest possible MVP.
- Audits are limited to roughly 50 pages.
- Only one or a few audits run concurrently.
- The initial process is linear.

### Verdict

This is the baseline against which frameworks should be judged. If a framework does not remove meaningful work from this pipeline, we should not add it.

## Approach 2: LangGraph workflow with LangChain LLM components

### Shape

```text
FastAPI -> audit worker -> LangGraph

START
  |
  v
validate_scope
  |
  v
crawl_site
  |
  v
extract_pages
  |
  v
run_rules
  |
  v
analyze_site
  |
  v
score_findings
  |
  v
generate_report  [LLM]
  |
  v
validate_report
  |
  v
END
```

Each node is an ordinary Python function. Only `generate_report`, and perhaps a narrowly scoped content-quality node, needs an LLM.

LangGraph defines workflows through shared state, nodes, and edges. It is designed for long-running, stateful orchestration and provides persistence, streaming, and human-in-the-loop capabilities. LangChain can be used inside selected nodes for model access, tools, and structured output, but LangGraph can also be used without the rest of LangChain. See the official [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) and [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api).

LangGraph explicitly distinguishes workflows with predetermined paths from agents that dynamically decide their own process. Our audit is mainly a workflow. See [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents).

### Example state

```python
class AuditState(TypedDict):
    audit_id: str
    start_url: str
    business_context: dict
    page_ids: list[str]
    finding_ids: list[str]
    current_stage: str
    warnings: list[str]
    report_id: str | None
```

Large raw HTML documents should stay in our database or artifact storage. Graph state should primarily contain identifiers, summaries, counters, and routing information.

### Where LangChain fits

LangChain can provide:

- a common interface for supported model providers;
- prompts and messages;
- structured model outputs;
- tools for narrow agentic tasks;
- retries and middleware around model calls; and
- tracing integrations.

LangChain agents run models in a tool-use loop until they return a final answer or reach a stop condition. That is useful for unpredictable problems, but our main pipeline should use explicit LangGraph nodes. See [LangChain agents](https://docs.langchain.com/oss/python/langchain/agents).

### Advantages

- The workflow is explicit and visually understandable.
- Deterministic functions and LLM nodes can coexist.
- Conditional routing is straightforward.
- State can be checkpointed between stages.
- Progress can be streamed from graph events.
- Failed stages can be retried without redesigning the domain logic.
- Human approval can be added later before proposed fixes are applied.
- The crawler and rules remain framework-independent Python modules.

### Disadvantages

- More concepts than a plain function pipeline.
- Persistence and background execution still require correct deployment configuration.
- Passing too much crawl data through graph state can create storage and performance problems.
- LangSmith is optional but may create ecosystem coupling if adopted deeply.

### Suitable when

- We want a real automated workflow in the MVP.
- We expect branching, resumability, progress events, or future approval steps.
- We still want strict control over factual analysis.

### Verdict

**Recommended approach for this project**, provided we use LangGraph as a controlled workflow and not as permission for the model to control the crawler.

## Approach 3: A free-form LangChain agent controlling all tools

### Shape

```text
User goal
   |
   v
LLM agent decides repeatedly:
  - which URL to crawl;
  - which parser to call;
  - which audit check to run;
  - whether enough evidence exists;
  - how to write the report.
```

In this design, crawler and audit functions are exposed as tools and the agent decides what to call and in what order.

### Advantages

- Impressive interactive demonstration.
- Flexible for unusual one-off investigations.
- User can ask follow-up questions during analysis.

### Disadvantages

- Unpredictable crawl coverage.
- Higher token usage and latency.
- Difficult to guarantee that every audit rule runs.
- Harder to reproduce and compare quarterly audits.
- Greater risk of tool loops and incomplete reports.
- More difficult to secure against prompt injection in page content.

### Suitable when

- The user asks an open-ended research question after the standard audit.
- The agent investigates a specific finding using a restricted toolset.

### Verdict

Do not use this as the main audit engine. It could become an optional "investigate this issue" feature later.

## Approach 4: CrewAI Flow with optional specialist crews

### Shape

```text
CrewAI Flow
  |
  +-- crawl and extract methods       [normal code]
  +-- technical rule method           [normal code]
  +-- site analysis method            [normal code]
  +-- report crew or report agent      [LLM]
  `-- final validation method          [normal code]
```

CrewAI Flows use start/listen methods and shared state to connect workflow stages. Their documentation describes retrieving intermediate/final outputs, updating state between methods, plotting flows, and tracking aggregate LLM usage. See [CrewAI Flows](https://docs.crewai.com/en/concepts/flows).

### Possible specialist roles

- Technical SEO reviewer
- Content/AEO reviewer
- Internal-link reviewer
- Report editor

These roles should consume verified page and finding data. They should not independently crawl the same site or invent factual findings.

### Advantages

- Clear mental model for role-based AI collaboration.
- Flow layer can mix ordinary functions, direct LLM calls, and crews.
- Convenient for demonstrations centered on multiple specialists.
- Shared state and usage metrics are built into the flow model.

### Disadvantages

- Multi-agent roles can duplicate work and increase cost.
- Role descriptions can hide weak data contracts.
- More nondeterminism if several agents independently prioritize findings.
- Less natural than a deterministic graph for a mostly fixed audit pipeline.

### Suitable when

- Multi-agent collaboration is itself a product requirement.
- We want separate expert review passes after the deterministic audit.
- A mentor, course, or demonstration specifically expects CrewAI.

### Verdict

A valid second choice. If selected, use a **CrewAI Flow** as the orchestrator and introduce crews only for subjective analysis or report review.

## Approach 5: PydanticAI with typed agents and Pydantic Graph

### Shape

```text
Typed Python graph
  |
  +-- deterministic crawl nodes
  +-- deterministic audit nodes
  +-- typed report agent
  `-- validated report output model
```

PydanticAI emphasizes typed dependencies and validated model outputs. Its documentation presents a progression from single-agent workflows through delegation and programmatic hand-offs to graph-based control for complex cases. Pydantic Graph is an async graph/state-machine library whose nodes and edges are defined with Python type hints. See [PydanticAI multi-agent applications](https://pydantic.dev/docs/ai/guides/multi-agent-applications/) and [Pydantic Graph](https://pydantic.dev/docs/ai/graph/graph/).

### Advantages

- Strong Python typing and validation.
- Natural fit with our Pydantic page, finding, and report models.
- Provider flexibility.
- Structured outputs and usage limits are central concepts.
- Domain models can remain explicit and testable.

### Disadvantages

- Smaller mindshare than the LangChain ecosystem.
- Graph features introduce advanced generic/type concepts.
- We still need a worker/runtime strategy for long-running web audits.
- Fewer team members may already know it.

### Suitable when

- Type safety and validated outputs are the highest priorities.
- The team prefers normal typed Python over framework-specific agent abstractions.
- We want a lighter agent layer but are comfortable assembling more infrastructure.

### Verdict

The strongest alternative to LangGraph for this project. It is especially attractive for the report-generation boundary because the LLM output must conform to strict finding and recommendation schemas.

## Approach 6: Temporal plus an LLM framework

### Shape

```text
Temporal Workflow
  |
  +-- crawl Activity
  +-- extraction Activity
  +-- audit Activity
  +-- LLM reporting Activity
  +-- approval signal
  `-- re-audit Activity
```

Temporal separates workflows, activities, and workers and provides primitives for timeouts, cancellation, schedules, child workflows, message passing, and versioning. Its Python SDK also documents integrations with LangGraph and other agent frameworks. See the [Temporal Python SDK guide](https://docs.temporal.io/develop/python).

### Advantages

- Excellent durability and recovery for long-running processes.
- Strong support for retries, cancellation, timeouts, and external signals.
- Good future fit for human approvals and multi-stage implementation work.
- Workflow state can survive service restarts and long pauses.

### Disadvantages

- Highest operational and conceptual overhead.
- Requires Temporal infrastructure or a managed service.
- Too much for a 50-page read-only audit prototype.
- Workflow determinism rules require careful engineering.

### Suitable when

- Audits become large, long-running, and business-critical.
- The product applies fixes and waits hours or days for human approval.
- Many workers and customers run concurrently.

### Verdict

Do not use for the first MVP. Keep it as a later production option if durable multi-stage workflows become central to the business.

## Recommended architecture for our MVP

Use a **hybrid LangGraph workflow** with normal Python domain modules and one or two narrow LangChain LLM calls.

```text
Browser
  |
  v
FastAPI
  |
  +-- creates Audit row
  +-- returns audit_id immediately
  `-- exposes status/report endpoints
            |
            v
Single audit worker
            |
            v
LangGraph workflow
  |
  +-- validate_scope        normal Python
  +-- discover_urls         normal Python
  +-- crawl_pages           normal Python
  +-- extract_page_data     normal Python
  +-- run_page_rules        normal Python
  +-- analyze_site          normal Python
  +-- score_findings        normal Python
  +-- generate_report       LangChain + LLM structured output
  +-- validate_report       normal Python
  `-- save_report           normal Python
            |
            v
Supabase Postgres
```

### Why this is the best balance

- It visibly automates the complete process.
- It gives us a proper agent/workflow architecture to demonstrate.
- It keeps SEO facts deterministic.
- It supports progress updates and future branching.
- It gives us a clean path to pause for approval later.
- It avoids pretending that every calculation needs an AI agent.
- It lets the crawler and rules survive even if we replace LangChain later.

## Proposed graph state

Do not place every HTML document into workflow state. Persist large artifacts separately.

```python
class AuditState(TypedDict):
    audit_id: str
    requested_url: str
    normalized_origin: str | None
    business_context: dict
    important_urls: list[str]
    current_stage: str
    discovered_count: int
    crawled_count: int
    page_ids: list[str]
    finding_ids: list[str]
    warnings: list[str]
    report_id: str | None
    error: str | None
```

## Proposed routing

```text
validate_scope
  |-- unsafe/invalid ------------> fail_audit
  `-- valid ---------------------> discover_urls

discover_urls
  |-- nothing crawlable ---------> produce_limited_report
  `-- URLs found ----------------> crawl_pages

crawl_pages
  |-- widespread failure --------> produce_limited_report
  `-- usable pages --------------> extract_and_audit

extract_and_audit
  `------------------------------> generate_report

generate_report
  |-- invalid structured output -> retry once
  |-- repeated model failure ----> deterministic_fallback_report
  `-- valid ---------------------> save_report
```

## LLM boundaries

### Good LLM tasks

- Explain why a verified finding matters.
- Merge repetitive findings without losing affected URLs.
- Adapt priorities to supplied business context.
- Draft a title, description, heading, schema block, or content outline.
- Produce an executive summary from structured findings.
- Review report language for unsupported certainty.

### Bad LLM tasks

- Decide whether a URL returned 200 or 404.
- Count tags or links from untrusted page text.
- Decide whether robots.txt technically blocks a URL.
- Calculate duplicate-title counts.
- Invent missing evidence.
- Freely select arbitrary URLs to crawl outside the validated scope.
- Directly modify a live website.

## Background execution decision

LangGraph orchestrates steps but the web API should not hold an HTTP request open for the entire audit.

For the first MVP:

1. FastAPI inserts an `Audit(status="queued")` row.
2. A single worker process claims queued audits.
3. The worker invokes the LangGraph workflow using the audit ID.
4. Every stage updates audit progress in Supabase Postgres.
5. The frontend polls a status endpoint.
6. Failed audits remain inspectable and can be retried.

This avoids Redis and Celery during the earliest phase. Move to a real task queue when we need multiple distributed workers or stronger delivery semantics.

## Framework-neutral module boundary

The most important implementation rule is that LangGraph nodes should call framework-neutral services:

```python
async def crawl_site(request: CrawlRequest) -> CrawlResult: ...

def extract_page(response: PageResponse) -> PageRecord: ...

def run_page_rules(page: PageRecord) -> list[Finding]: ...

def analyze_site(pages: list[PageRecord]) -> list[Finding]: ...

def score_findings(
    findings: list[Finding],
    context: BusinessContext,
) -> list[ScoredFinding]: ...

async def write_report(input: ReportInput) -> AuditReport: ...
```

This preserves our ability to move from LangGraph to plain Python, CrewAI, PydanticAI, or Temporal without rewriting the crawler and audit logic.

## Suggested decision

Decision status: **adopted for the first MVP implementation on 2026-08-28.**

Use this for the MVP:

- **Workflow orchestration:** LangGraph Graph API
- **LLM integration:** selected LangChain model integration with structured output
- **Crawler and extraction:** framework-neutral Python
- **Audit rules and scoring:** framework-neutral Python
- **API:** FastAPI
- **MVP storage:** Supabase Postgres
- **MVP execution:** one separate audit worker
- **Browser rendering:** Playwright only when selected
- **UI progress:** database-backed polling initially
- **Future production queue:** add only when concurrency requires it

Do not use initially:

- a free-form agent controlling the crawl;
- several agents repeating the same analysis;
- automatic production-site changes;
- Temporal infrastructure;
- Redis/Celery before a single worker becomes insufficient; or
- an LLM-only audit with no deterministic evidence layer.

## When to reconsider

Revisit the framework choice when one of these becomes true:

- audits regularly exceed hundreds or thousands of pages;
- many audits must run concurrently;
- workflows must survive long outages or multi-day pauses;
- users approve, edit, and reject generated site changes;
- different specialist agents demonstrably improve report quality;
- model-provider portability becomes commercially important; or
- framework upgrades create more maintenance than value.

## Current recommendation in one sentence

Use LangGraph to automate and observe the audit stages, use LangChain only for tightly scoped LLM work, and keep crawling, evidence collection, SEO rules, scoring, and storage as ordinary testable Python.
