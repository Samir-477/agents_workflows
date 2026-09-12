export type DetailPair = [title: string, description: string];

export interface AgentDetail {
  discipline: string;
  tier: "Core" | "Advanced";
  tags: string[];
  introduction: string;
  method: DetailPair[];
  coverage: DetailPair[];
  weighting: DetailPair[];
  output: string[];
  questions: DetailPair[];
  pairWith: string[];
}

export const agentDetails: Record<string, AgentDetail> = {
  "seo-audit": {
    discipline: "SEO · Website health", tier: "Core", tags: ["Crawl", "Indexing", "On-page"],
    introduction: "This agent captures a controlled page sample, checks the technical and on-page signals present in that evidence, and turns verified problems into an ordered fix list.",
    method: [["Capture the page", "Fetch the requested URL and a bounded set of supporting pages."], ["Apply deterministic checks", "Inspect status, directives, canonicals, headings, images, metadata and structured data."], ["Prioritize verified issues", "Rank retained findings by severity, confidence and affected pages."]],
    coverage: [["Crawl and access", "HTTP status, redirects, robots directives and reachable links."], ["Indexing", "Canonical signals, meta robots and conflicting page instructions."], ["Page structure", "Titles, descriptions, headings, image alternatives and content depth."], ["Machine-readable data", "JSON-LD parsing, declared entities and visible-page agreement."]],
    weighting: [["Blocking access", "Pages that cannot be fetched or indexed receive the highest priority."], ["Evidence breadth", "Repeated issues across the captured sample carry more weight."], ["Confidence", "Direct observations outrank inferred opportunities."]],
    output: ["Prioritized issue list", "Affected URLs", "Evidence excerpts", "Recommended fixes"],
    questions: [["Does this replace a full-site crawl?", "No. It deeply reviews the selected URL and a controlled supporting sample."], ["Does it render JavaScript?", "The current diagnosis uses captured server HTML; browser rendering remains a stated limitation."]],
    pairWith: ["meta-title-description", "schema-markup", "internal-linking"],
  },
  "ai-visibility": {
    discipline: "AEO · AI readiness", tier: "Advanced", tags: ["Citability", "Entities", "Access"],
    introduction: "This agent checks whether search and answer systems can access, interpret and confidently cite the resort page using observable page and crawler signals.",
    method: [["Inspect machine access", "Review crawler directives and page availability."], ["Measure answer readiness", "Check entity clarity, question coverage and extractable facts."], ["Separate facts from gaps", "Report supported readiness issues while labelling untested assistant behaviour."]],
    coverage: [["Crawler access", "Robots and page directives affecting retrieval."], ["Entity clarity", "Property, brand and destination signals."], ["Answer structure", "Headings, concise answers, FAQs and structured content."], ["Citation support", "Specific, attributable facts that can be quoted safely."]],
    weighting: [["Access barriers", "Blocked retrieval outweighs copy improvements."], ["Identity consistency", "Conflicting property details reduce confidence."], ["Evidence specificity", "Concrete facts outrank generic promotional claims."]],
    output: ["Readiness assessment", "Crawler-policy evidence", "Entity gaps", "Citation improvements"],
    questions: [["Does this test every AI assistant?", "No. It evaluates page readiness and public access signals, not every model's live answer."], ["Can it guarantee citations?", "No. It can improve eligibility and clarity, but citation decisions belong to each platform."]],
    pairWith: ["schema-markup", "content-brief", "seo-audit"],
  },
  "internal-linking": {
    discipline: "SEO · Site architecture", tier: "Advanced", tags: ["Links", "Anchors", "Navigation"],
    introduction: "This agent maps observed internal links and proposes relevant page-to-page connections with a source, target, placement and reviewable anchor suggestion.",
    method: [["Build the link graph", "Record internal links and where they appear in the captured sample."], ["Find useful gaps", "Compare page topics and existing navigation paths."], ["Propose placements", "Return source-backed link opportunities without inventing pages."]],
    coverage: [["Inbound discovery", "Pages with weak contextual entry paths."], ["Outbound usefulness", "Relevant destinations readers cannot easily reach."], ["Anchor quality", "Generic, repeated or unclear anchor wording."], ["Placement", "Links inside main content versus repeated templates."]],
    weighting: [["Customer relevance", "Links must help the reader continue a related journey."], ["Existing connectivity", "Isolated or weakly linked pages receive more attention."], ["Placement strength", "Contextual links carry more value than repeated navigation links."]],
    output: ["Source and target URLs", "Anchor options", "Placement guidance", "Link evidence"],
    questions: [["Will every suggested link be published?", "No. Content and SEO should approve relevance and wording first."], ["Does it measure the whole site?", "Only the captured page sample; wider architecture requires a larger crawl."]],
    pairWith: ["keyword-cluster", "content-optimizer", "seo-audit"],
  },
  "serp-competitor": {
    discipline: "SEO · Search landscape", tier: "Advanced", tags: ["SERP", "Competitors", "Intent"],
    introduction: "This agent captures a timestamped Google result sample through Serper and compares the visible result set with pages the crawler can inspect.",
    method: [["Derive the query", "Use the verified resort identity to prepare a relevant search phrase."], ["Capture the result sample", "Store positions, titles, domains and URLs returned for the configured market."], ["Compare visible patterns", "Summarize intent and inspected competitor-page structure with explicit limits."]],
    coverage: [["Brand presence", "Whether Sterling appears in the captured branded result sample."], ["Competing domains", "Resorts, marketplaces and publishers visible in the sample."], ["Result messaging", "Recurring title language and customer intent."], ["Inspected pages", "Headings, questions and schema only where fetching succeeds."]],
    weighting: [["Observed position", "Higher visible results receive more attention in the snapshot."], ["Domain relevance", "Direct resort alternatives differ from travel marketplaces."], ["Inspection confidence", "Fetched page evidence outranks snippet-only inference."]],
    output: ["Timestamped SERP sample", "Visible competitor domains", "Intent summary", "Source URLs"],
    questions: [["Is one search a ranking report?", "No. Rankings vary by time, place and device; the output is a documented sample."], ["Where does the data come from?", "The diagnosis uses the configured Serper API and labels that source in the evidence."]],
    pairWith: ["keyword-cluster", "content-brief", "content-optimizer"],
  },
  "keyword-cluster": {
    discipline: "SEO · Search themes", tier: "Core", tags: ["Keywords", "Themes", "Structure"],
    introduction: "This agent organizes the verified resort query and captured search language into practical themes for page planning and navigation.",
    method: [["Collect grounded terms", "Use the resort identity, page copy and saved SERP research."], ["Group related intent", "Cluster semantically related phrases and remove unrelated property terms."], ["Map page roles", "Suggest which themes belong on the resort page or supporting content."]],
    coverage: [["Core resort intent", "Property, destination and stay-related language."], ["Amenity themes", "Facilities and experiences supported by the page."], ["Local discovery", "Destination questions and nearby-interest themes."], ["Page separation", "Topics that need distinct supporting content."]],
    weighting: [["Identity match", "Terms must describe the selected property and destination."], ["Observed support", "Page and SERP evidence outrank model-only suggestions."], ["Intent separation", "Distinct customer needs should not be forced into one cluster."]],
    output: ["Theme clusters", "Pillar recommendations", "Page-role mapping", "Internal-link direction"],
    questions: [["Does this include search volume?", "No live volume dataset is queried in the current diagnosis."], ["Are all phrases publication-ready?", "No. They are planning inputs that require SEO review."]],
    pairWith: ["serp-competitor", "content-brief", "internal-linking"],
  },
  "meta-title-description": {
    discipline: "SEO · Search snippets", tier: "Core", tags: ["Titles", "Descriptions", "Intent"],
    introduction: "This agent measures the current title and description, identifies supported problems, and drafts review-labelled alternatives from captured page facts.",
    method: [["Read current metadata", "Extract title, description and page identity from the saved HTML."], ["Validate the fields", "Check presence, length, duplication within the sample and identity alignment."], ["Draft alternatives", "Generate options using only supported property facts and label them for review."]],
    coverage: [["Title presence", "Missing, empty or structurally weak title elements."], ["Description presence", "Missing or unusable description fields."], ["Length", "Measured characters shown as guidance, not a ranking rule."], ["Identity alignment", "Property and destination clarity across metadata and page evidence."]],
    weighting: [["Missing fields", "Absence receives higher priority than a minor length concern."], ["Identity conflict", "Wrong property naming is treated as a direct fault."], ["Draft safety", "Unsupported claims prevent an option from being recommended."]],
    output: ["Current metadata measurements", "Validated issues", "Draft title options", "Draft descriptions"],
    questions: [["Will Google use the suggested text?", "Google may rewrite snippets; the agent improves clarity but cannot control display."], ["Are length ranges guarantees?", "No. Search results use rendered width and query context."]],
    pairWith: ["seo-audit", "content-optimizer", "serp-competitor"],
  },
  "schema-markup": {
    discipline: "AEO · Structured data", tier: "Core", tags: ["JSON-LD", "Entities", "Validation"],
    introduction: "This agent parses existing JSON-LD, checks it against visible resort facts and prepares review-labelled structured-data corrections when evidence supports them.",
    method: [["Parse every block", "Read JSON-LD scripts and retain parser errors with code excerpts."], ["Compare entities", "Check names, URLs and declared types against visible page identity."], ["Prepare safe fixes", "Suggest markup from observed facts while flagging fields that need confirmation."]],
    coverage: [["Syntax", "Invalid JSON and unreadable structured-data blocks."], ["Entity identity", "Property names, brand and canonical URL agreement."], ["Type suitability", "Whether declared types fit the visible page."], ["Fact support", "Markup claims that cannot be confirmed from page content."]],
    weighting: [["Parse failure", "Unreadable JSON-LD is a direct technical fault."], ["Identity mismatch", "A different property name receives high priority."], ["Visible agreement", "Supported fields outrank optional enrichment."]],
    output: ["JSON-LD validation", "Identity comparison", "Code excerpts", "Review-ready schema draft"],
    questions: [["Does valid schema guarantee a rich result?", "No. Eligibility and display remain search-engine decisions."], ["Will the agent invent missing facts?", "No. Unconfirmed values stay omitted or explicitly marked for review."]],
    pairWith: ["ai-visibility", "seo-audit", "local-seo"],
  },
  "content-brief": {
    discipline: "Content · Planning", tier: "Advanced", tags: ["Brief", "Outline", "Evidence"],
    introduction: "This agent turns the selected resort page, verified identity, search themes and SERP research into a structured improvement brief for a writer.",
    method: [["Assemble the evidence", "Reuse captured copy, research and keyword themes from the same session."], ["Design the brief", "Define intent, sections, questions, entities and internal-link opportunities."], ["Validate the handoff", "Score completeness and expose missing evidence before a writer receives it."]],
    coverage: [["Audience and intent", "The customer need the page should answer."], ["Section plan", "Recommended headings and purpose for each section."], ["Questions and entities", "Topics supported by page and search evidence."], ["Editorial controls", "Claims, missing facts and review requirements."]],
    weighting: [["Evidence completeness", "Unsupported sections reduce handoff readiness."], ["Intent alignment", "The brief must serve the resort-page task."], ["Identity safety", "Stale or conflicting property inputs reject the output."]],
    output: ["Writer-ready outline", "Questions to answer", "Evidence notes", "Handoff quality state"],
    questions: [["Does this publish content?", "No. It creates a reviewable plan for Content and Resort Operations."], ["Why are research agents added?", "The brief depends on grounded search themes, so required upstream agents run automatically."]],
    pairWith: ["serp-competitor", "keyword-cluster", "content-optimizer"],
  },
  "local-seo": {
    discipline: "SEO · Local discovery", tier: "Core", tags: ["Location", "Business details", "FAQs"],
    introduction: "This agent checks whether the resort page clearly and consistently communicates the location and business details customers and local search systems need.",
    method: [["Resolve the property", "Confirm resort, brand and destination from corroborating page signals."], ["Extract local facts", "Inspect address, phone, map, destination and local-question content."], ["Separate gaps from drafts", "Report missing or conflicting facts and label suggested copy for review."]],
    coverage: [["Property identity", "Consistent resort and destination naming."], ["Contact details", "Observable address and phone information."], ["Local context", "Destination descriptions and nearby-interest information."], ["Local questions", "Practical customer questions the page can answer."]],
    weighting: [["Identity conflict", "Wrong property information receives immediate attention."], ["Booker usefulness", "Missing practical details outrank optional copy expansion."], ["Verification", "Unconfirmed local facts cannot become findings or published copy."]],
    output: ["Local information assessment", "Missing-detail list", "Draft FAQs", "Human review checklist"],
    questions: [["Does this update Google Business Profile?", "No. It evaluates the website page and proposes actions."], ["Are nearby attractions verified?", "Only facts observed in the supplied evidence are treated as confirmed."]],
    pairWith: ["schema-markup", "meta-title-description", "content-brief"],
  },
  "content-optimizer": {
    discipline: "Content · Page quality", tier: "Advanced", tags: ["Intent", "Structure", "Actions"],
    introduction: "This agent reviews the existing resort content against its intended customer task, the saved research and the content brief, then produces evidence-linked improvements.",
    method: [["Assess the current page", "Measure structure, topic support and answer usefulness from captured copy."], ["Compare grounded inputs", "Use the verified query, clusters and brief created in the same session."], ["Build the action plan", "Prioritize concrete edits and retain the evidence behind each recommendation."]],
    coverage: [["Intent fit", "Whether the page helps the expected resort researcher."], ["Topic coverage", "Supported themes that are missing or under-explained."], ["Structure", "Headings, answer flow and usable content sections."], ["Evidence quality", "Specific property facts versus unsupported promotional language."]],
    weighting: [["Customer impact", "Gaps blocking comparison or booking research receive more weight."], ["Source support", "Captured facts and saved research outrank inferred ideas."], ["Actionability", "Specific, verifiable edits rank above broad advice."]],
    output: ["Page-quality assessment", "Prioritized content actions", "Evidence references", "Suggested wording for review"],
    questions: [["Will it rewrite the whole page?", "It proposes targeted improvements; publishing remains an editorial decision."], ["Why do other agents run with it?", "The optimizer requires search research, themes and a brief, which are added automatically."]],
    pairWith: ["content-brief", "keyword-cluster", "internal-linking"],
  },
};
