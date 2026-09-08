# Sterling Holidays real-site evaluation — 2026-09-08

## Purpose

This is the first real-site case for the mentor-requested evaluation programme. It
tests whether the current agents complete on production HTML, retain inspectable
evidence, avoid claiming complete-site coverage, and produce recommendations that
survive manual review. One site is not enough to establish accuracy across the MVP.

Target: <https://www.sterlingholidays.com/>

## Completed runs

| Agent | Run ID | Scope | Result |
| --- | --- | --- | --- |
| SEO/AEO Audit | `f4bc4176-152a-4ab3-b8eb-8dcca4c7d723` | 20-page representative sample | Complete; score 68; 9 grouped findings |
| AI Visibility Readiness | `13edfdc3-9a67-4977-b15f-d528c8857fa7` | 10-page representative sample | Complete; readiness score 93; 3 findings |
| Internal Linking | `fba5007c-8895-4f11-970a-2244e67d5e1f` | 15-page representative sample | Complete; 182 observed edges, 15 contextual edges, 4 retained opportunities |

The page counts overlap and must not be presented as 45 unique reviewed pages.

## Findings checked against independent evidence

| Finding | Agent result | Review status | Evidence |
| --- | --- | --- | --- |
| `/resorts-hotels/corbett` returns 404 | Critical | Confirmed | Independent HTTP retrieval also returned 404. The current resorts listing links to a different Jim Corbett property URL. |
| Homepage WebPage JSON-LD is malformed | Important | Confirmed | Block 2 fails JSON parsing with an invalid control character at line 7, column 208. |
| Resorts listing WebPage JSON-LD is malformed | Important | Confirmed | Block 2 fails JSON parsing with an invalid control character at line 7, column 196. |
| Kodaikanal Lake WebPage JSON-LD is malformed | Important | Confirmed | Block 2 fails JSON parsing with an invalid control character at line 7, column 199. |
| Missing/generic image alternatives | Minor | Needs human review | Attribute state is observed reliably, but each image still needs an informative/decorative decision. |
| Multiple H1 on the Kanha page | Minor | Needs rendered-page review | Two source H1 elements were observed; template visibility and intended hierarchy should be checked in a browser. |
| Long titles/descriptions | Minor | Plausible heuristic | Length is factual; actual truncation varies by query, device and rendered width. |

## Product defects found and corrected by this case

1. **Double response decompression.** The crawler decoded a compressed stream and
   reconstructed it while retaining `Content-Encoding`, which caused a second decode
   and failed the first Sterling run. Decoded transport headers are now removed, and
   a bounded identity-encoding fallback handles genuinely mislabeled responses.
2. **Inconsistent JSON-LD scoring.** SEO Audit reported malformed JSON-LD, while AI
   Visibility still awarded 100 for machine readability. AI Visibility now consumes
   the shared parse diagnostics. The repeated Sterling run changed from 97 overall /
   100 machine readability to 93 overall / 84 machine readability.
3. **Template-inflated link similarity.** Repeated resort and navigation vocabulary
   caused unrelated destinations to appear strongly related. Corpus-wide boilerplate
   terms are now excluded from similarity, placement overlap is required, and
   contextual confidence is more conservative. The repeated run retained 4 of the
   original 10 suggestions; each has a source section and excerpt, with one high and
   three medium-confidence relationships.

## Current useful observations

- The sampled link graph is dominated by a site-wide template: all 182 possible
  sampled page pairs were linked, while only 15 observed edges were contextual.
- The strongest retained contextual suggestion connects the Karwar and Goa coastal
  resort pages from a Konkan Coast section. The other three suggestions remain
  editorial-review items rather than automatic implementation tasks.
- The sampled pages expose substantial visible copy and several schema types.
- Declared robots rules allowed GPTBot, ChatGPT-User, PerplexityBot and ClaudeBot at
  the audited path at test time. This is a policy observation, not proof of retrieval,
  indexing, mention or citation by any answer product.

## Inputs required before testing the remaining agents

The remaining agents were subsequently exercised using explicitly labelled
evaluation fixtures and public facts. See the
[full ten-agent report](STERLING_HOLIDAYS_FULL_AGENT_REPORT_2026-09-08.md).

The following still must be supplied before treating those outputs as an approved
client strategy rather than an evaluation:

- the primary target keyword and audience for the homepage;
- one priority resort URL with its target keyword and audience;
- approved business facts for a local-page test;
- the expected purpose of metadata, brief and optimization outputs; and
- a human reviewer verdict for each candidate finding/recommendation.

With those inputs, run the chain `SERP research -> content brief -> content optimizer
-> metadata/schema`, retaining run IDs as provenance. Keyword clustering needs an
approved keyword set rather than keywords scraped from site copy.

## How this fits the mentor implementation plan

This case proves the mechanics of real-site execution and has already produced three
useful regression fixes. It starts, but does not complete, the requested benchmark.
Completion still requires 50-100 genuinely reviewed pages across 5-10 varied sites,
issue-level precision/recall, recommendation-validity labels, false-positive and
false-negative review, browser/mobile checks, and full-pipeline handoff evaluation.
