# Sterling Holidays — full ten-agent evaluation

**Evaluation date:** 2026-09-08  
**Target:** <https://www.sterlingholidays.com/>  
**Priority page:** <https://www.sterlingholidays.com/resorts-hotels/kodaikanal-lake>

## Executive assessment

All ten active agents completed a persisted live-site run. The suite is useful as
an analyst's first-pass workbench with human review. It is not yet safe for
unsupervised client publishing. The strongest agents are the SEO Audit, Schema
Generator after the lodging-type correction, and SERP evidence capture. The main
quality gaps are heuristic scoring, partial crawl coverage, weak cross-agent
handoff into the Content Brief, and recommendations that still need editorial
judgement.

**Overall evaluation rating: 7.5/10.** The pipeline completed, retained evidence
and exposed important limitations. Two live-site failures were found and corrected
during this evaluation: a one-word content extraction error and missing
`LodgingBusiness` support.

## Evaluation inputs and boundaries

The keyword, audience and campaign goal below are evaluation fixtures, not a claim
about Sterling's approved SEO strategy:

- Target keyword: **resorts in Kodaikanal**
- Secondary phrases: **Kodaikanal lake resort**, **hotels near Kodaikanal lake**,
  and **family resort in Kodaikanal**
- Audience: travellers in India comparing a leisure stay near Kodai Lake
- Goal: help qualified visitors evaluate the property and proceed to direct booking
- Locale: India, English

Business facts came only from Sterling's public priority page: the property name,
address, phone, 6.5-acre size, 102 rooms, lake setting, and listed facilities.
Pricing, availability, opening hours, geo-coordinates and ratings were deliberately
withheld. The keyword-cluster seed list was assembled for this evaluation from
observed page topics; it contains no search-volume data and is not an approved
content plan.

## Run register

| Agent | Run ID | Live result | Quality rating |
| --- | --- | --- | --- |
| SEO/AEO Audit | `f4bc4176-152a-4ab3-b8eb-8dcca4c7d723` | Complete; 20 pages; score 68 | 8.5/10 |
| AI Visibility | `13edfdc3-9a67-4977-b15f-d528c8857fa7` | Complete; 10 pages; score 93 | 7.5/10 |
| Internal Linking | `fba5007c-8895-4f11-970a-2244e67d5e1f` | Complete; 15 pages; 4 retained opportunities | 7.5/10 |
| SERP & Competitor | `284e3706-b41d-452c-8126-c8de94a107cf` | Complete; 8 organic results; 2 of 5 competitor pages inspected | 7.5/10 |
| Content Brief | `4ddc2ebe-0fd1-4b31-b8e6-db60392f33ee` | Complete; 77; correctly withheld handoff | 6.5/10 |
| Keyword Clustering | `722541c4-e987-4df1-a592-0da14f8143fd` | Complete; 15 seeds; 4 clusters; 2 pillars | 7/10 |
| Metadata | `2308470f-e369-48b4-b718-d6f0a26eb3e7` | Complete; 4 titles and 3 descriptions | 7/10 |
| Schema Markup | `c1ab6697-cf68-4b42-87ee-a41d9a9343e0` | Complete; valid `LodgingBusiness` draft | 8/10 |
| Local SEO | `57147714-68df-41a1-a617-27d52c3171d7` | Complete; one needs-review page | 7/10 |
| Content Optimizer | `2358ef1a-af01-4600-b487-cfac3b7071b9` | Complete; 2,320 words; score 64 | 7.5/10 |

Page counts overlap and do not represent 45 unique pages.

## Agent findings

### 1. SEO/AEO Audit

The audit found one critical, three important and five grouped minor findings.
The strongest verified results were the live 404 at `/resorts-hotels/corbett` and
malformed JSON-LD on three sampled pages. Image alternatives, a multiple-H1 case,
and long metadata remain valid review queues, but require human or rendered-page
judgement. The crawl clearly states its 20-page limit and lack of browser rendering.

### 2. AI Visibility

The agent scored discoverability 100, machine readability 84, entity clarity 93
and citability 93. It correctly consumed the shared malformed JSON-LD evidence
after the earlier scoring correction. The overall 93 should be treated as a
documented heuristic, not proof of AI citations or recommendations. The entity-name
and Q&A opportunities are lower-confidence editorial prompts.

### 3. Internal Linking

The sampled graph contained 182 observed edges but only 15 contextual edges,
showing that a site-wide template dominates linking. Boilerplate filtering reduced
ten initial suggestions to four evidence-backed placements. The strongest is
Karwar to Goa Varca from the Konkan Coast section. The three medium-confidence
relationships still need editorial approval.

### 4. SERP & Competitor

Serper returned eight organic results for the India/English sample. The intent was
classified as mixed and the median observed word count across inspectable pages was
733. No People Also Ask or related-search entries were returned. Only two of five
selected competitor pages could be inspected, and the report states this limitation
rather than filling the missing evidence. Rankings remain a timestamped sample.

### 5. Content Brief

The brief scored 77 and correctly set `ready_for_handoff` to false. Validation found
weak title-keyword alignment and a blocking absence of the target topic in outline
headings. This is good refusal behavior, but the generation itself did not meet the
handoff bar. The brief also cannot reference a saved SERP run directly; research has
to be copied into source notes, so the intended SERP-to-brief provenance chain is
incomplete.

### 6. Keyword Clustering

Fifteen unique evaluation seeds became four coherent clusters and two pillars:
resort selection, Kodaikanal travel, hotels near the lake, and Sterling-branded
navigation. The output correctly leaves volume totals empty. The suggested
`/sterling-kodai-lake/` page could duplicate the existing priority URL, because this
agent accepts keyword rows but no existing URL inventory. Cannibalization review is
therefore mandatory.

### 7. Metadata

The agent preserved the provided keyword and facts and generated the promised four
titles and three descriptions. The recommended title was **“Book Sterling Kodai
Lake: Indoor & Outdoor Activities”** (score 90.4); the recommended description was
135 characters and explicitly flagged as shorter than the preferred range. The
chosen title does not contain the exact evaluation keyword and overweights
activities, while another option better describes the resort. Recommendation
scoring needs human review even though grounding and option presentation are good.

### 8. Schema Markup

The first run exposed that the allowed type list lacked the appropriate lodging
type and accepted `LocalBusiness` as publish-ready. The generator now supports and
prefers `LodgingBusiness` for hotels and resorts. The corrected run emitted grounded
name, address, telephone, room count and amenity evidence without inventing prices,
ratings, hours or coordinates. `url` and `geo` remain listed as missing recommended
properties. “Publish-ready draft” means this generated block passed local checks;
the live page's existing malformed JSON-LD still has to be repaired or replaced and
the final page validated.

### 9. Local SEO

The run retained all five deliberately missing facts as warnings and produced five
review tasks. It did not present the result as final: status is `needs_review`. The
schema now uses `LodgingBusiness` for the physical resort. Weak points are the
generic `/accommodation-kodaikanal-1` slug, a 163-character description, placeholder
FAQ answers, and small prose expansions such as “throughout the premises” that are
not literal supplied facts. The copy needs an editor before use.

### 10. Content Optimizer

The corrected run inspected 2,320 words and assessed 11 of 13 checks. It scored 64,
with good heading structure, depth, readability, metadata, links and structured
data. It flagged 14 images with missing alt attributes, absence of the exact target
phrase and incomplete exact-match topic coverage. Question coverage and freshness
were correctly left unassessed. Some SERP-derived topic prompts are token fragments,
so topic actions remain editorial candidates rather than direct instructions.

## Defects found and corrected during the full run

1. **Sparse semantic container selection:** the priority page contains a one-word
   `<main>` shell while substantial copy sits elsewhere in the body. The optimizer
   initially reported one word and a misleading score of 55. Extraction now chooses
   the largest semantic region and falls back to body text when it is too sparse.
   The live rerun found 2,320 words and scored 64.
2. **Missing resort schema type:** the schema generator's fixed type list lacked
   `LodgingBusiness`. Support, validation and compiler rules were added, and the
   live rerun emitted the correct type.
3. **Local resort subtype:** Local SEO previously emitted generic `LocalBusiness`
   for every physical branch. Accommodation and resort services now emit
   `LodgingBusiness`; other physical businesses retain `LocalBusiness`.

## Pipeline handoff assessment

The saved SERP run and Content Brief run were both attached to the Content Optimizer,
and their IDs are retained in its result. This proves persisted research-to-analysis
handoff. The Content Brief itself has no saved SERP run field, so the complete
`SERP -> brief -> optimizer -> metadata/schema` provenance chain is only partial.
Metadata and schema also consume a new prompt rather than a saved upstream artifact.
The next orchestration increment should add optional upstream run IDs and source
labels to the brief, metadata and schema requests.

## Report and UI presentation check

All ten saved result routes returned HTTP 200 from the local Next.js application.
The report components expose scores, findings, evidence, warnings, limitations,
recommendations and run-specific actions. SEO Audit offers PDF download; SERP,
Optimizer and Local SEO provide JSON export or copy flows. A connected interactive
browser was unavailable in this session, so desktop/mobile visual layout, focus
behavior and screenshot-level presentation remain unverified.

## Recommended Sterling work queue

1. Restore or redirect the confirmed Corbett 404.
2. Repair malformed JSON-LD on the affected templates and validate rendered output.
3. Review the 14 missing-alt cases on the priority page and the wider sampled image
   queue, separating informative from decorative images.
4. Confirm the target keyword and search intent with the campaign owner before
   changing page copy or metadata.
5. Rewrite the Content Brief until it passes its own handoff validation.
6. Review the four contextual-link suggestions and the keyword architecture for
   relevance and cannibalization.
7. Validate final `LodgingBusiness` markup on the rendered page after integration.

## Remaining evaluation limits

This report completes one live site across all ten agents. It does not complete the
mentor's wider benchmark requirement. That still needs 50–100 distinctly reviewed
pages across 5–10 varied sites, issue-level precision/recall, false-positive and
false-negative labels, recommendation-validity scoring, and rendered desktop/mobile
checks with human verdicts.
