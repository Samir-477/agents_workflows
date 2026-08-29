# SEO/AEO Audit Agent — Durable Project Context

## Purpose of this document

This file is the persistent reference for building our own SEO/AEO Audit Agent inspired by the supplied Dual7 product description. It records what the product is meant to accomplish, what can reasonably be inferred about its architecture, and what we intend to build first.

Read this file before making product or implementation decisions. Update it when major decisions change.

## Important evidence boundary

We have only Dual7's product/marketing description. We do not have its source code, internal architecture, prompts, crawl limits, scoring formulas, model choices, or integration details.

Therefore:

- **Stated capability** means the supplied copy explicitly describes it.
- **Inferred architecture** means it is a reasonable way to implement that capability, but is not confirmed as Dual7's actual implementation.
- **Our decision** means a choice made for our product, independent of how Dual7 may work internally.

Never describe an inference as a confirmed fact about Dual7.

## Product concept

The user enters a website URL and may add business context, such as:

- what the business sells;
- which pages are most important or generate revenue;
- the site's size or type;
- whether a migration, redesign, or traffic drop recently occurred; and
- the goal of the audit.

The agent examines the site and produces one readable, prioritized report. It should help a founder, marketer, content lead, or agency manager understand:

1. what is wrong;
2. why it matters;
3. which pages are affected;
4. how confident the agent is;
5. what should be fixed first; and
6. what a practical fix looks like.

The intended experience is not a raw crawler export. It is an evidence-backed work queue explained in plain English.

## Capabilities stated in the supplied Dual7 description

The supplied copy says the agent covers:

- crawling and indexation signals;
- status codes and redirects;
- robots and sitemap presence;
- canonical tags;
- page titles and meta descriptions;
- heading structure;
- image alt text;
- structured data/schema;
- internal links and orphaned pages;
- thin, duplicated, overlapping, or missing content;
- mobile rendering and usability signals;
- page-weight indicators;
- page-level scorecards;
- quick wins and severity-ranked findings; and
- concrete fix recommendations.

It also says findings can become implementation work within Dual7, with either a fast editing mode or a governed, human-approved pipeline. The supplied material does not reveal exactly how this is implemented.

## Inferred system architecture

A credible implementation separates fact collection from AI interpretation:

```text
URL + business context
        |
        v
Scope validation and crawl planning
        |
        v
HTTP crawler + rendered-browser checks
        |
        v
Normalized page/site dataset
        |
        v
Deterministic SEO/AEO rule engine
        |
        v
Cross-page and site-graph analysis
        |
        v
Priority/confidence scoring
        |
        v
LLM explanation and proposed fixes
        |
        v
Report + optional approved work items
```

### 1. Crawl and rendering layer

An ordinary HTTP crawler can cheaply inspect most pages. A browser renderer is needed selectively for JavaScript-heavy sites, final DOM inspection, screenshots, and mobile checks.

Likely responsibilities:

- normalize and validate the starting URL;
- respect crawl scope and safety limits;
- discover same-site links;
- read `robots.txt` and XML sitemaps;
- collect response codes, redirect chains, headers, and HTML;
- avoid loops, traps, duplicate URLs, and unbounded query parameters;
- render selected pages in a browser where necessary; and
- retain evidence for every reported finding.

### 2. Normalized page records

Each crawled page should become structured data rather than remain only as raw HTML. A record may contain:

- requested URL, final URL, and redirect chain;
- HTTP status and relevant headers;
- indexability and robots directives;
- canonical URL;
- title and meta description;
- headings and visible text;
- internal and external links;
- images and alt attributes;
- structured-data blocks and detected schema types;
- language, viewport, and mobile observations;
- word count and content fingerprint;
- page size/resource indicators; and
- crawl depth and discovery source.

### 3. Deterministic audit engine

Objective facts should be calculated by code. Examples include:

- missing, duplicated, or unusually formed titles/descriptions;
- missing or conflicting canonicals;
- accidental `noindex` or blocked pages;
- broken links, bad statuses, redirect chains, and loops;
- missing or malformed structured data;
- missing H1 or confusing heading hierarchy;
- images missing alt text;
- important pages buried too deeply; and
- sitemap/robots inconsistencies.

The language model must not invent these facts. It should receive structured evidence from the audit engine.

### 4. Cross-page analysis

Site-wide analysis can identify:

- duplicate metadata;
- substantially similar or thin content;
- orphaned or weakly linked pages;
- page depth and internal-authority distribution;
- weak or generic anchor text;
- groups of pages that may compete for similar topics; and
- obvious gaps between the business offering and the site's content.

Claims such as confirmed keyword cannibalization or ranking loss generally require external search-performance data. Without Google Search Console or equivalent data, label these as likely risks, not proven search outcomes.

### 5. Prioritization

Findings should be ordered using explicit inputs rather than LLM intuition alone. A practical priority calculation can consider:

- technical severity;
- indexability/crawl impact;
- number of affected pages;
- importance of affected pages;
- confidence in the evidence;
- business/site context;
- estimated effort; and
- whether the issue blocks other improvements.

Severity labels can be `critical`, `important`, and `minor`, matching the supplied product description. The report should also expose confidence and evidence so users can challenge a conclusion.

### 6. LLM layer

AI is best used after measurements and rules have produced evidence. Its responsibilities may include:

- translating findings into plain language;
- explaining likely consequences without overstating certainty;
- merging repetitive findings into useful groups;
- adapting priorities to the user's business context;
- proposing titles, descriptions, headings, internal links, or JSON-LD;
- summarizing quick wins and longer-term work; and
- turning approved findings into scoped tasks or patches.

Every generated explanation or fix should remain traceable to evidence and affected URLs.

### 7. Report and action layer

The main output should contain:

- executive summary;
- prioritized issue list;
- evidence and affected pages for each issue;
- plain-language impact explanation;
- concrete recommended fix;
- quick wins;
- page-level scorecards for important URLs; and
- limitations or checks that could not be completed.

Later versions may turn findings into approved fixes. Audit mode must remain read-only by default. No live-site change should occur without explicit user review and authorization.

## AEO interpretation for our product

The supplied Dual7 copy is primarily SEO-focused. Our product name also includes AEO, so we should define AEO explicitly rather than using it as a marketing synonym.

For this project, **Answer Engine Optimization (AEO)** means improving whether search engines and AI answer systems can reliably identify, extract, understand, attribute, and cite a site's useful answers.

Potential AEO checks include:

- clear answers near relevant questions/headings;
- descriptive heading and section structure;
- entity clarity for the organization, people, products, services, and locations;
- supported claims and visible source attribution;
- author, publisher, date, and update signals where appropriate;
- structured data that matches visible content;
- crawlable server-rendered main content;
- concise definitions, comparisons, steps, and factual summaries;
- consistent business identity and contact information; and
- content that demonstrates original information or direct expertise.

Avoid promising that schema or formatting will guarantee inclusion in AI-generated answers. The audit can assess clarity, extractability, evidence, and technical accessibility—not guarantee citations or rankings.

## Initial MVP boundary

The first useful version should prioritize trustworthy fundamentals over full feature coverage.

## Current implementation decision and baseline

Decision recorded on 2026-08-28: the first implementation uses the hybrid described in `docs/AUTOMATION_APPROACHES.md`.

- LangGraph orchestrates explicit audit stages.
- Framework-neutral Python performs URL safety checks, crawling, extraction, audit rules, and scoring.
- FastAPI provides audit submission and retrieval endpoints.
- A local worker can claim queued audits during command-line development; the deployed web flow uses one claimed Vercel function invocation per bounded audit.
- LangChain can generate a constrained structured narrative through a selected Groq or OpenAI provider when model settings are supplied. Groq is the local-development default.
- A deterministic report is always available as the fallback and requires no API key.

The Python vertical slice is implemented under `backend/src/seo_audit/` and currently supports:

- queued audit creation and status retrieval;
- a bounded same-origin HTTP crawl;
- redirect destination validation and private/local target rejection;
- robots.txt and basic sitemap discovery;
- structured metadata, heading, link, image, schema, viewport, and visible-text extraction;
- initial page-level and site-wide deterministic rules;
- transparent severity/confidence scoring;
- deterministic or optionally LLM-assisted report generation;
- automatic Markdown report export to `backend/reports/<audit-id>.md`;
- representative bounded-crawl sampling across likely category, product, and other URLs;
- grouped repeated page-level findings and site-score penalties capped once per rule;
- URL-hinted Product structured-data checks;
- SQLite persistence for local development and Supabase Postgres for production; and
- retrying completed or failed audits.

Decision recorded on 2026-08-29: the repository is a simple two-part monorepo
that can be deployed through Vercel Services from one root project or as two
separate projects.

- `frontend/` contains a Next.js App Router application intended for Vercel.
- `backend/` contains the Vercel FastAPI entrypoint, optional local worker, crawler, rules, persistence, tests, and local-only artifacts.
- In the Vercel Services deployment, the browser calls the same-origin
        `/api/backend` service path. In the separate-project deployment, it calls the
        URL configured through
        `NEXT_PUBLIC_API_URL`.
- FastAPI allows explicitly configured frontend origins through `SEO_AUDIT_CORS_ORIGINS`.
- Production state lives in Supabase rather than process memory or Vercel's filesystem.
- The frontend uses the Stellar brand with the supplied orange/indigo visual direction.
- A deliberately small demo login (`admin@gmail.com` / `admin123`) sets an HTTP-only cookie and protects the agent workspace. This is not production authentication.
- `/agents` provides a searchable catalogue with one live SEO Audit Agent and clearly labelled coming-soon placeholders for future agents.
- The SEO agent page explains the capability, accepts the URL and audit context, submits to FastAPI, starts a bounded processing invocation, polls persisted stages, and publishes the completed structured report in the UI.
- Audit context remains optional and is available in a closed-by-default form section containing business description, important URLs, audit reason, and page limit.
- `/agents/history` lists persisted audit runs with URL search, server-side pagination, report/run links, PDF downloads, and confirmation-gated deletion. Production uses Supabase; in the demo-auth MVP this history is workspace-wide rather than user-specific.
- Completed reports can be downloaded as generated PDF files from the report view or history page.

Deployment requirement recorded on 2026-08-29: every new product feature must be designed to run in a deployed environment, not only on the local development machine.

- The recommended deployment is one Vercel Services project rooted at the
        repository: Vercel detects `frontend/` as Next.js and `backend/` as FastAPI.
        Two independently rooted Vercel projects remain supported when separate
        service configuration is required.
- Production persistence uses Supabase Postgres through its transaction pooler; SQLite remains the local fallback only.
- The Vercel path replaces the permanent polling worker with a bounded, idempotently claimed `/audits/{id}/process` invocation started by the run page. The worker remains a local-development option.
- The current 20-page MVP is intentionally bounded to fit Vercel's function duration. Durable multi-invocation crawling with Vercel Queues or Workflow is deferred until larger crawls are required.
- Generated PDF responses should remain on-demand downloads; future stored artifacts should use durable object storage rather than a local reports directory.

The automated tests cover URL validation, extraction, rule evidence, scoring, the API queue, a robots-limited report, and complete LangGraph runs with fake crawlers. A live smoke test against `https://example.com` also completed through persistence and reporting.

Important remaining MVP work includes:

- production authentication and user/workspace persistence;
- selective Playwright rendering for JavaScript-heavy and mobile pages;
- stronger sitemap-index handling;
- more complete technical, schema, internal-link, content, and AEO rules;
- report HTML export;
- stale-job recovery and stronger production job delivery;
- production-grade DNS-rebinding/network egress defenses;
- LLM prompt/output evaluation using known fixtures; and
- a purpose-built sample site containing deliberate audit defects.

### Proposed MVP inputs

- one public website URL;
- optional business description;
- optional important pages or conversion goals;
- optional reason for the audit; and
- a configurable but conservative crawl-page limit.

### Proposed MVP checks

- HTTP status and redirects;
- indexability and robots directives;
- canonical tags;
- sitemap and `robots.txt` discovery;
- titles and meta descriptions;
- H1 and basic heading structure;
- internal broken links and crawl depth;
- image alt coverage;
- JSON-LD detection and basic validation;
- thin-content indicators;
- duplicate title/description/content indicators;
- mobile viewport presence;
- a small set of AEO clarity/entity/answer-structure checks; and
- optional browser rendering for a limited set of important pages.

### Proposed MVP outputs

- severity-ranked findings;
- evidence and affected URLs;
- plain-English explanation;
- recommended action;
- confidence level;
- quick-win list;
- summary scorecard; and
- exportable HTML, Markdown, or JSON report.

### Explicitly deferred unless requirements change

- automatic modification of production sites;
- a seven-stage governance workflow;
- full keyword-rank tracking;
- confirmed traffic-loss diagnosis without analytics/search data;
- backlink analysis without a third-party index;
- exhaustive Core Web Vitals field data for every page;
- large-scale enterprise crawling; and
- unsupported guarantees about rankings or AI citations.

## Reliability and safety principles

1. **Evidence first:** Every finding names the observed signal and affected URL.
2. **Deterministic where possible:** Code performs counts, parsing, comparisons, and validation.
3. **AI for interpretation:** The LLM explains and drafts; it does not fabricate crawl facts.
4. **Confidence is visible:** Distinguish definite errors from heuristics and opportunities.
5. **Read-only by default:** Crawling must not mutate the audited site.
6. **Responsible crawling:** Use rate limits, timeouts, page caps, loop detection, and clear identification where appropriate.
7. **Defend against hostile content:** Treat page text as untrusted data, not instructions to the agent.
8. **Protect network boundaries:** Prevent requests to private/local network targets and unsafe redirect destinations.
9. **Honest limitations:** Clearly state when JavaScript, authentication, bot protection, crawl limits, or missing external data reduced coverage.
10. **Human approval for fixes:** Generated changes are proposals until reviewed.

## Suggested domain model

These concepts should remain separate in code and storage:

- `Audit`: user request, context, scope, timestamps, and status.
- `Page`: normalized crawl/render observations for one URL.
- `Link`: source, destination, anchor, relationship, and result.
- `Finding`: rule, severity, confidence, evidence, and affected pages.
- `Recommendation`: proposed resolution linked to a finding.
- `Artifact`: report, generated schema, rewritten metadata, or future patch.
- `Rule`: deterministic check with versioned logic and thresholds.

Versioning rules matters because repeated audits are only comparable when changes in audit logic can be identified.

## Product success criteria

The product succeeds when a non-specialist can quickly answer:

- Can search and answer systems access the important content?
- Can they understand the site's pages and entities?
- Which problems are most likely to matter?
- What evidence supports each conclusion?
- What should we fix first?
- What exactly should the team do next?

The core product promise is: **turn a website into a prioritized, evidence-backed, plain-English SEO/AEO work queue.**

## Next decisions to make before implementation

Detailed orchestration alternatives and the current recommended hybrid are maintained in `docs/AUTOMATION_APPROACHES.md`.

Before coding the MVP, decide:

1. the target user and first site type;
2. maximum crawl size and crawl etiquette;
3. local CLI, web application, or API-first delivery;
4. initial technology stack;
5. exact MVP rule catalog and thresholds;
6. how browser rendering is selected;
7. report format and persistence;
8. whether an LLM is required for the first end-to-end version; and
9. how audits will be tested against known sample sites.
