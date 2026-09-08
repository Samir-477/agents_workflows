# Mentor feedback audit and implementation checklist

Audit date: 2026-09-07. Status: initial audit complete; implementation checklist open.

Source: the supplied 14-page `C:/Users/HP/Downloads/feedback.pdf`, compared with the current working tree, including existing uncommitted work. This document records our findings and proposed implementation sequence, not claims about Dual7's private implementation. The mentor's examples are illustrative, not measured results from this application.

## Verdict

Eight independently persisted agents exist. The two recommended additions, SERP & Competitor Analysis and SEO Content Optimizer, do not exist. Shared history and API registration are present, but they are not cross-agent orchestration. The mentor's connected SEO Copilot, consolidated action plan, and human-verified evaluation framework are still missing.

The existing foundation is useful: structured models, deterministic validation, bounded AI repair, persistence, visible limitations, and specialized result screens. Passing software tests does not establish the accuracy or usefulness of live SEO recommendations.

## Verified baseline

- [x] Read the mentor feedback and durable project context.
- [x] Review all eight agents' workflows, validation/analysis boundaries, API composition, persistence patterns, and result presentation code.
- [x] Confirm both additional agents are absent from backend packages, registered APIs, and frontend catalogue.
- [x] Confirm `SERPER_API_KEY` is nonempty in `.env`, without printing it.
- [x] Verify the key with one live request to `https://google.serper.dev/search`: HTTP 200, nine organic results, no PAA or related-search entries for this response. The initial sandbox request could not connect; the permitted network retry succeeded.
- [x] Run `python -m pytest backend/tests -q`: 90 tests passed; dependency deprecation warnings only.
- [x] Run `npm.cmd run lint`: passed.
- [x] Run `npx.cmd tsc --noEmit`: passed.
- [x] Run `npm.cmd run build`: passed, including generated agent routes.
- [x] Reproduce schema availability substring bug and empty-alt/malformed-JSON-LD extraction behavior using small in-memory inputs.
- [ ] Inspect rendered results on desktop and mobile. Browser runtime discovery returned no available browser; this audit reviews presentation source, not screenshots or interactions.
- [ ] Run a live representative sample through every model-backed agent and inspect the saved outputs. Existing tests largely use fake providers/crawlers and memory repositories. The Serper check does not validate Groq, Supabase, or deployment credentials.

No application implementation was changed during this audit. Existing user changes were preserved. No migrations or deployments were run.

## Mentor requirement mapping

| Requirement | Current implementation | Assessment / remaining work |
| --- | --- | --- |
| SEO Audit | URL validation, bounded HTTP crawl, metadata/indexability/content rules, deterministic priorities, narrative fallback, persistence and PDF | Partial against the full recommendation. Needs stronger extraction, category/page scores, and coverage-aware reporting. |
| Metadata Generator | Prompt parsing, four titles and three descriptions, counts, claims checks, similarity checks, repairs and search previews | Implemented within its prompt-first scope. No automatic existing-page input or expert-rated metadata benchmark. |
| Schema Generator | Model interpretation, deterministic JSON-LD compiler, property/claim validation, draft/readiness states and copyable script | Implemented within prompt-first scope. Availability grounding defect and no verified live-page validation. |
| Keyword Cluster | Supplied keyword list, deduplication, model grouping, intent safeguards, complete input coverage, pillar/link plans | Partial: clusters supplied keywords; does not discover keywords from a seed or use observed SERPs. |
| Content Brief | Assignment-based strategy, H2/H3 outline, coverage, FAQs, grounded URLs, validation and bounded repair | Partial: no live competitor input or measured topic coverage. `rewrite` is a brief mode, not an existing-page optimizer. |
| Internal Linking | Crawl graph, weak anchors, orphan candidates, topical matches, placement excerpts and deterministic scores | Implemented with limitations. Navigation links can suppress missing contextual-link opportunities. No expert validity benchmark. |
| Local SEO | Up to three area drafts, supplied business facts, branch/service-area distinction, duplicate checks, review tasks, edits and JSON export | Implemented with limitations. Edit revalidation loses some source context; no human-scored local benchmark. |
| AI Visibility | On-site discoverability, machine readability, entity clarity and citability heuristics, bot policies | Material scope gap: does not query answer systems or observe actual mentions/citations/competitors. Existing limitations correctly acknowledge this. |
| SERP & Competitor Analysis | No implementation | Missing; high priority. |
| SEO Content Optimizer | No implementation | Missing; high priority. |
| One connected workflow | Shared API composition and history only | Missing project/run coordinator, shared snapshots, dependencies and automatic evidence handoffs. |
| SEO health and category scores | One SEO score plus separate AI-readiness dimensions | Partial. No unified technical/on-page/content/linking/schema/local scorecard; numbers are uncalibrated project heuristics. |
| Top opportunities and final action plan | SEO-only prioritized findings and up to five quick wins | Partial. No consolidated top ten, common Critical/High/Medium/Low priorities, effort/impact estimates or task tracking. |
| Evaluation framework | 90 passing software tests and a local-SEO smoke helper | Missing 50-100 page / 5-10 website human-reviewed benchmark, per-agent quality metrics and integrated evaluation. |
| Monitoring/backlinks and other future agents | Not implemented | Correctly deferred by the mentor; do not add them to this MVP checklist. |

## Concrete quality findings

### Q01 - Incorrect support for stock availability (high)

`backend/src/schema_generator/validation.py`, `_fact_is_supported`, tests availability using substring matches. `available` appears inside `unavailable`. Reproduction: `InStock` is accepted from the source sentence `This product is unavailable.` This can validate a fact opposite to the supplied brief.

Acceptance: contextual, negation-aware availability matching; regression cases for unavailable, not available, out of stock, in stock, and preorder. Ambiguous evidence must stay a review issue.

### Q02 - No-score presentation is misleading (high)

`src/components/audit-run.tsx:79` replaces a missing score with zero for its status and color. The number renders as a dash while the label says `Needs work`. The AI-readiness analysis also produces numerical zeroes when no pages were inspectable; no evidence should be distinct from measured poor readiness.

Acceptance: explicit `Not assessed` state, neutral styling, explanation and next action. Missing categories must not silently become zero or 100 or enter a composite denominator.

### Q03 - Crawl evidence is insufficient for competitor/content optimization (high)

`backend/src/seo_audit/extractor.py` retains H1/H2 arrays and clipped section excerpts, but not a complete ordered H1/H2/H3 structure or external-link observations. Invalid JSON-LD is discarded, leaving only schema type names. HTTP `X-Robots-Tag`, redirect-chain evidence and full body evidence are not represented in `PageRecord`.

Acceptance: versioned, bounded evidence records with heading levels/order, meaningful main text, internal/external links, JSON-LD parse diagnostics, relevant HTTP directives, timestamps and truncation flags. Never derive competitor word counts or headings from search snippets.

### Q04 - Crawl scope and budgets need hardening before reuse (high)

`backend/src/seo_audit/crawler.py` fetches the first page before loading robots rules. `_fetch` validates public network destinations, but later page redirects are not constrained to the settled audit origin. Responses are downloaded before body-size checks; sitemap expansion can add many requests. Query URLs are excluded, reducing coverage. These are implementation observations; not all have an adversarial integration reproduction yet.

Acceptance: policy-aware fetch ordering, explicit redirect scope, bounded response bytes and total stage time, truthful discovery/coverage accounting, and tests for blocked paths, off-origin redirects and partial inventories. Preserve useful representative sampling and existing URL safety checks.

### Q05 - Incorrect provenance can survive brief validation (high)

`backend/src/content_brief/validation.py:108` flags unsupported `provided` coverage labels and requests repair, but its sanitized draft does not correct those labels. A failed/ineffective repair can leave them displayed as supplied facts. FAQ provenance lacks the same support check. A structural quality score is not topic-coverage accuracy.

Acceptance: deterministically correct invalid labels, link observed SERP claims to retained source IDs, validate FAQs too, and preserve warning/review status after failed repairs.

### Q06 - Existing navigation links hide contextual gaps (medium)

`backend/src/internal_linking/analysis.py:171` and `:196` exclude a pair whenever it appears in all observed edges, even if it occurs only in navigation. The workflow warns about template-heavy linking, but can offer no concrete contextual placements for those pairs. The empty-result explanation also infers absence of orphan/anchor problems from an empty recommendation list; those are different facts.

Acceptance: distinguish contextual and navigation edges, propose relevant body links when helpful, and derive empty-state explanations from actual diagnostic counts and candidate rejection reasons.

### Q07 - Local edit validation loses the original prompt (medium)

The initial local workflow passes `request.prompt` to `finalize`. The edit endpoint at `backend/src/local_seo/api.py:72` does not. A claim supported in the original brief can be flagged after an edit. Its warning-preservation filter searches for `Maps`, although current lookup messages also use OpenStreetMap/listing wording.

Acceptance: preserve original source text and typed enrichment warnings during edit revalidation, while refreshing copy-related warnings.

### Q08 - Image-alt results conflate missing and intentionally empty (medium)

An image with `alt=""` is counted in `images_missing_alt`. The rule presents this with high confidence even though its recommendation acknowledges decorative images can be empty.

Acceptance: distinguish absent, empty and placeholder values; empty alt becomes a contextual review signal rather than a definite error. Include informative/decorative benchmark examples.

### Q09 - Reliability differs across agents (high before orchestration)

Per-run database claims exist, but most agents have no stale-running recovery comparable to Local SEO. A process interrupted after claiming can remain running, while retry accepts only completed/failed states. Many workflows store raw exception strings, unlike the redacted local workflow. Local drafting allows 220 seconds plus three optional 25-second lookups, leaving only five seconds inside the configured 300-second function maximum before other overhead.

Acceptance: shared safe error classification, bounded stage budgets, persisted attempts/heartbeat, lease-aware recovery, race-safe retries and idempotent stage completion. A multi-agent run must use multiple bounded invocations rather than a single 300-second request.

### Q10 - Scores and quick wins do not yet form a management plan (high)

`backend/src/seo_audit/reporting.py` deducts 15/7/2 once per rule. Quick wins are up to five finding-derived strings, selected without an effort model. Severity vocabularies differ across agents. The result has no common category score, action status, ownership, dependencies, or estimated impact/effort fields.

Acceptance: explainable versioned scoring, explicit applicable/assessed coverage, common action schema and deduplicated priorities. Impact must be a qualitative estimate with rationale, not fabricated traffic/revenue uplift. Retain raw evidence and specialist detail.

### Q11 - Result presentation is useful but fragmented (medium)

Source review found good foundations: metadata search previews, schema script and entity cards, brief outlines/FAQs, internal-link placements, AI-readiness evidence, local draft preview and editing, and SEO PDF downloads. Export/copy options differ, reports are long, and there is no project-level executive view, consistent score explanation, task status or next-stage action. Some URLs are truncated/plain text, and clipboard operations lack a visible failure path.

Acceptance: a common summary/action/evidence hierarchy; readable URLs, accessible copy/export feedback, filtering and progressive disclosure; tested loading, empty, failed, partial, review and complete states. Desktop/mobile visual review remains mandatory before calling this finished.

### Q12 - Documentation and production boundaries need reconciliation (medium)

`docs/IMPLEMENTATION_STATUS.md` still describes an August 31 / 30-test baseline and says sitemap indexes are not expanded, while the current crawler follows a bounded child level. `PROJECT_CONTEXT.md` includes historical scope decisions that must be distinguished from the new target. Authentication is a demo cookie protecting frontend workspace routes, not production API/workspace authorization.

Acceptance: current status docs, migration and deployment instructions, explicit demo limitations, and API/workspace access controls before a multi-user production release. Do not treat this audit as authorization to publish or change customer sites.

## Ordered implementation checklist

Checked items mean verified completion, not merely a created file. Keep IDs stable and add validation evidence as work finishes.

### Phase 1 - Trustworthy evidence and regression coverage

- [x] F01 Fix Q01 schema availability grounding and add focused regression cases.
- [x] F02 Fix Q02 missing/partial score states across API, UI, history and exports.
- [x] F03 Fix Q05 brief/FAQ provenance, including unsuccessful repair behavior.
- [x] F04 Fix Q07 local edit grounding and enrichment-warning preservation.
- [x] F05 Correct Q06 contextual linking and fact-based empty explanations.
- [x] F06 Extend shared extraction and fix Q08 alt classification; migrate persisted records compatibly.
- [ ] F07 Harden Q04 crawler scope/response/time limits and Q09 shared run recovery/error handling.

### Phase 2 - SERP & Competitor Analysis Agent

- [x] S01 Add server-only Serper configuration, secret-safe status reporting and `.env.example` documentation. Never expose the key through `NEXT_PUBLIC_*` or stored results.
- [x] S02 Implement a bounded Serper client with timeouts, bounded retries, input normalization and explicit missing-key/quota/empty/malformed response states. Cache snapshots by query, country, language and freshness to avoid duplicate calls.
- [x] S03 Persist query, locale, timestamp, organic rank/title/URL/snippet, and optional PAA/related/answer-box evidence. Empty optional sections must stay empty, not be invented.
- [x] S04 Safely inspect up to ten observed competitor pages within budgets; show successful/blocked/truncated coverage. Derive depth, headings and schema from fetched pages, with source references.
- [x] S05 Generate grounded intent/topic patterns, gaps and recommendations; distinguish observations from interpretations. Link every competitor claim to the exact page or SERP snapshot.
- [x] S06 Add persisted create/process/result/retry/delete lifecycle, migration, catalogue entry, history and a readable result screen with comparison table and source evidence.
- [x] S07 Verify mocked failure cases, blocked/private target cases, persistence/reopen behavior and a small live search run.

Serper supplies Google search evidence, as shown by the [provider's response examples](https://serper.dev/). This integration must not be presented as measured mentions across independent AI answer systems.

### Phase 3 - SEO Content Optimizer Agent

- [x] O01 Accept URL or supplied existing content, primary/secondary keywords, audience and optional existing research snapshot. Plain text input must mark unavailable HTML checks as not assessed.
- [x] O02 Analyze intent alignment, keyword usage/repetition, H1/H2/H3 structure, content depth, missing topics/entities, readability, snippet/FAQ opportunities, internal/external links, images/alt, metadata, schema and freshness evidence. Use contextual heuristics rather than universal keyword-density/word-count targets.
- [x] O03 Return prioritized, evidence-backed recommendations with affected section, observed text, proposed action, confidence, effort and qualitative impact. Optional rewritten sections require side-by-side original/proposal and source/factual review checks.
- [x] O04 Reuse SERP research and supplied briefs without inventing competitors, facts, freshness dates, links or traffic outcomes. External-data failure should yield a clearly limited content-only result when possible.
- [x] O05 Add complete persisted lifecycle, migration, catalogue/history, result view and useful copy/export.
- [x] O06 Test URL/text input, missing evidence, keyword-stuffing false positives, malicious page content, ungrounded rewrites, provider failures and saved-result reopening.

### Phase 4 - Connect the existing agents

- [ ] P01 Define a persisted project/run with URL, business facts, selected keywords, locale, shared crawl/research IDs and per-stage readiness/status.
- [ ] P02 Feed discovered/supplied keywords to clustering, observed SERPs to briefs, and the selected brief/research to optimization. Preserve provenance instead of passing anonymous text blobs.
- [ ] P03 Feed verified page facts to metadata/schema and shared crawl data to linking/readiness; avoid recrawling unchanged pages separately.
- [ ] P04 Execute dependent stages through bounded resumable invocations. Persist partial outputs and allow retrying only failed stages without repurchasing successful research.
- [ ] P05 Make local expansion conditional on supplied local business facts; missing context should request the needed information or visibly skip that stage.
- [ ] P06 Provide clear next-stage actions from specialist results and a project progress view. Add integrated tests for data handoffs, duplicate process requests, interruption and partial provider failure.

### Phase 5 - Consolidated action plan and presentation

- [ ] U01 Define one action model: priority (Critical/High/Medium/Low), category, issue/opportunity, affected URLs/sections, evidence/source IDs, confidence, impact rationale, estimated effort, dependencies and status.
- [ ] U02 Deduplicate overlapping specialist findings, preserve contributing evidence, and select the top ten opportunities deterministically.
- [ ] U03 Add explained category scores and overall coverage. Keep on-site AI readiness separate from measured off-site visibility; mark local SEO not applicable where appropriate.
- [ ] U04 Present executive summary, top actions and scorecard first; expose detailed evidence, comparisons and proposed edits on demand. Include filtering and task status updates.
- [ ] U05 Make report/PDF/JSON exports agree with saved data and include scope, dates, methodology and limitations. Support readable copy actions and visible failures.
- [ ] U06 Verify desktop/mobile layouts, long content/URLs, keyboard navigation and all result states in a working browser; render and inspect exported PDFs.

### Phase 6 - Actual AI visibility measurement

- [ ] A01 Keep current readiness checks explicitly labelled and design a separate observation schema: question, provider/system, model/mode when known, locale, time, raw answer, brand mention, position definition, citation URLs and competitors.
- [ ] A02 Add supported answer-provider adapters or a clearly labelled import flow for recorded answers. Provider unavailability must be `not tested`, never `brand absent`. API output must not be misrepresented as the provider's consumer-app answer.
- [ ] A03 Evaluate 20-50 questions across multiple supported systems using retained answers and human-verified mention/citation labels. Do not close this item with synthetic answers or Google SERPs alone.

### Phase 7 - Evaluation and delivery evidence

- [ ] E01 Build a versioned benchmark format and executable evaluation runner. Store case IDs, source/date, page snapshot, expected findings/topics, expert ratings and review provenance.
- [ ] E02 Start with deliberately flawed and clean fixtures; add 50-100 pages from 5-10 varied websites with genuine human verification. Synthetic fixtures are not a substitute for the mentor's real-site benchmark.
- [ ] E03 Measure issue-level precision/recall, link recommendation validity, topic coverage, keyword intent/grouping quality and metadata/local/optimizer output quality. Publish denominators and false positives/negatives, not just a composite score.
- [ ] E04 Include approximately 50 human-reviewed metadata examples and the multi-system AI observation set. Select quality thresholds from reviewed baselines rather than inventing success figures.
- [ ] E05 Evaluate the full website-to-action-plan workflow, including evidence survival, conflicting recommendations, repeatability, partial failures, latency and provider cost.
- [ ] E06 Run focused regression checks, full backend suite, lint, TypeScript and production build; perform browser/PDF verification and live persisted smoke tests.
- [ ] E07 Update durable context/status/deployment docs with actual completed scope and verification. Apply required migrations and verify deployed behavior as a distinct tracked delivery step.

## Dependencies and honest completion boundaries

The supplied Serper key is working. Credentials or captured observations for additional answer systems, real-site benchmark selection, and actual human SEO ratings are not established by this audit. Continue implementing adapters, schemas, fixtures, and evaluation tooling independently, but leave provider-specific/live/human-review items open until evidence exists.

Do not add the mentor's deferred backlink, monitoring, content-refresh, image-agent, technical-fix, sitemap-agent, GBP or reporting-agent catalogue entries merely to increase the agent count. Existing report improvements and stronger sitemap extraction belong inside the ten-agent MVP.

The first implementation batch is Phase 1 plus the shared evidence contracts needed by Phase 2. Then deliver SERP research, content optimization, the connected action plan, and measured quality in that order. Browser and expert evaluation are completion checks, not optional polish.

## Implementation evidence — 2026-09-07

- F01-F06 are covered by focused regressions in `test_schema_generator.py`,
  `test_ai_visibility.py`, `test_content_brief.py`, `test_local_seo.py`,
  `test_internal_linking.py` and `test_new_audit_rules.py`.
- S01-S07 are implemented under `backend/src/serp_competitor`, with server-only
  configuration, provider-state reporting, bounded retries, fresh snapshot reuse,
  retained answer-box/PAA/related evidence, inspected-page coverage and source URLs.
- O01-O06 are implemented under `backend/src/content_optimizer`. URL and text modes,
  optional SERP/brief handoffs, excluded unassessed checks, source-linked actions,
  hostile-content handling and persistence/reopen behavior have automated coverage.
- Current automated result: 126 backend tests pass; ESLint, TypeScript and the Next.js
  production build pass. All ten local result routes return HTTP 200, but a connected
  interactive browser was unavailable, so rendered desktop/mobile review remains open.
- All ten agents now have persisted runs for the Sterling Holidays case. The
  [full report](evaluations/STERLING_HOLIDAYS_FULL_AGENT_REPORT_2026-09-08.md)
  records run IDs, outputs, ratings, two new live-site defects and their regression
  fixes. One site does not satisfy the multi-site or human-review denominator
  required by E02-E05.
