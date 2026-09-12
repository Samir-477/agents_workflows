export type AgentStatus = "active" | "coming-soon";
export type AgentEngine = "SEO" | "AEO" | "GEO";
export type AgentTier = "Core" | "Advanced";

export interface AgentDefinition {
  slug: string;
  diagnosisId?: string;
  category: string;
  engine: AgentEngine;
  tier: AgentTier;
  name: string;
  description: string;
  focus: string;
  status: AgentStatus;
  accent: "orange" | "indigo";
}

export const agents: AgentDefinition[] = [
  { slug:"seo-audit", diagnosisId:"seo_audit", category:"SEO Engine", engine:"SEO", tier:"Core", name:"Technical SEO Auditor", description:"Crawlability, indexing, on-page signals and technical search health.", focus:"Returns a prioritized audit with source evidence and remediation steps.", status:"active", accent:"indigo" },
  { slug:"content-optimizer", diagnosisId:"content_optimizer", category:"SEO Engine", engine:"SEO", tier:"Core", name:"On-Page Content Agent", description:"Intent, structure, topical depth and evidence on the page.", focus:"Shows where the page satisfies its target intent and where content needs work.", status:"active", accent:"orange" },
  { slug:"keyword-cluster", diagnosisId:"keyword_cluster", category:"SEO Engine", engine:"SEO", tier:"Core", name:"Keyword & Search Theme Agent", description:"Semantic keyword groups, pillar opportunities and publishing order.", focus:"Turns supplied keyword research into clusters and an internal-link plan.", status:"active", accent:"indigo" },
  { slug:"serp-competitor", diagnosisId:"serp_competitor", category:"SEO Engine", engine:"SEO", tier:"Core", name:"SERP Competitor Agent", description:"Live result patterns and visible differences between ranking pages.", focus:"Compares source-backed SERP evidence without inventing competitor metrics.", status:"active", accent:"indigo" },
  { slug:"local-seo", diagnosisId:"local_seo", category:"SEO Engine", engine:"SEO", tier:"Core", name:"Local & Destination Agent", description:"Location relevance, business details, local FAQs and page coverage.", focus:"Builds grounded local-page guidance from the facts you provide.", status:"active", accent:"orange" },
  { slug:"internal-linking", diagnosisId:"internal_linking", category:"SEO Engine", engine:"SEO", tier:"Advanced", name:"Internal Link Architect", description:"Where internal authority flows and where relevant links are missing.", focus:"Identifies source pages, target pages and useful anchor opportunities.", status:"active", accent:"indigo" },
  { slug:"meta-title-description", diagnosisId:"metadata", category:"SEO Engine", engine:"SEO", tier:"Core", name:"Search Metadata Agent", description:"Measured, intent-matched title and description options.", focus:"Returns compliant variants with lengths, rationale and a recommendation.", status:"active", accent:"orange" },
  { slug:"content-brief", diagnosisId:"content_brief", category:"SEO Engine", engine:"SEO", tier:"Advanced", name:"Content Brief Agent", description:"Evidence-led page planning for a defined topic and audience.", focus:"Produces an executable outline, questions, entities and writing guidance.", status:"active", accent:"orange" },
  { slug:"performance-audit", category:"SEO Engine", engine:"SEO", tier:"Advanced", name:"Experience & Vitals Agent", description:"Field and lab performance signals for the page experience.", focus:"Planned workflow for performance evidence and prioritized fixes.", status:"coming-soon", accent:"orange" },
  { slug:"indexing-crawler-access", category:"SEO Engine", engine:"SEO", tier:"Core", name:"Indexing & Crawler Access", description:"Search crawler access, directives, canonicals and sitemap reachability.", focus:"Planned workflow for crawler access and indexability diagnostics.", status:"coming-soon", accent:"indigo" },

  { slug:"schema-markup", diagnosisId:"schema_markup", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Schema & Structured Answers", description:"Structured data that matches visible content and page entities.", focus:"Generates validated JSON-LD with assumptions and review guidance.", status:"active", accent:"orange" },
  { slug:"question-discovery", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Question Discovery Agent", description:"The questions people ask before choosing or using the offering.", focus:"Planned workflow for evidence-backed question discovery.", status:"coming-soon", accent:"indigo" },
  { slug:"answer-gap", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Answer Gap Agent", description:"Questions for which the page has no clear, direct answer.", focus:"Planned workflow for mapping missing answers to page sections.", status:"coming-soon", accent:"indigo" },
  { slug:"answer-optimization", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Answer Optimization Agent", description:"Direct, concise answers shaped for people and answer engines.", focus:"Planned workflow for revising supported content into answer-first blocks.", status:"coming-soon", accent:"orange" },
  { slug:"faq-intelligence", category:"AEO Engine", engine:"AEO", tier:"Core", name:"FAQ Intelligence Agent", description:"FAQ coverage, specificity and usefulness for the topic.", focus:"Planned workflow for scoring expected questions and answer quality.", status:"coming-soon", accent:"indigo" },
  { slug:"question-intent", category:"AEO Engine", engine:"AEO", tier:"Advanced", name:"Question Intent Agent", description:"What the asker needs to decide, compare, find or complete.", focus:"Planned workflow for classifying question intent and content fit.", status:"coming-soon", accent:"orange" },
  { slug:"answer-structure", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Answer Structure Agent", description:"Whether page answers are organized for reliable extraction.", focus:"Planned workflow for headings, lists, tables and answer-block structure.", status:"coming-soon", accent:"indigo" },
  { slug:"aeo-opportunity", category:"AEO Engine", engine:"AEO", tier:"Advanced", name:"AEO Opportunity Agent", description:"Turns answer gaps into a prioritized publishing plan.", focus:"Planned workflow for grouping opportunities by impact and effort.", status:"coming-soon", accent:"orange" },

  { slug:"ai-visibility", diagnosisId:"ai_visibility", category:"GEO Engine", engine:"GEO", tier:"Core", name:"AI Visibility Agent", description:"Public discoverability, machine readability, entity clarity and citability.", focus:"Audits whether public pages give answer engines enough support to cite them.", status:"active", accent:"indigo" },
  { slug:"ai-query-discovery", category:"GEO Engine", engine:"GEO", tier:"Core", name:"AI Query Discovery Agent", description:"The prompts people may use when asking assistants about the topic.", focus:"Planned workflow for grounded prompt and demand discovery.", status:"coming-soon", accent:"indigo" },
  { slug:"ai-mention", category:"GEO Engine", engine:"GEO", tier:"Core", name:"AI Mention Agent", description:"Where a brand or entity appears in generated answers and how it is framed.", focus:"Planned workflow for measuring supported mentions across answer samples.", status:"coming-soon", accent:"orange" },
  { slug:"citation-intelligence", category:"GEO Engine", engine:"GEO", tier:"Core", name:"Citation Intelligence Agent", description:"Which sources assistants cite for relevant answers.", focus:"Planned workflow for collecting citations and comparing source coverage.", status:"coming-soon", accent:"indigo" },
  { slug:"citation-gap", category:"GEO Engine", engine:"GEO", tier:"Advanced", name:"Citation Gap Agent", description:"Relevant sources and answers where competitors are cited and you are absent.", focus:"Planned workflow for evidence-backed citation-gap analysis.", status:"coming-soon", accent:"orange" },
  { slug:"entity-authority", category:"GEO Engine", engine:"GEO", tier:"Core", name:"Entity Authority Agent", description:"Whether machines can identify the organization, offering and relationships.", focus:"Planned workflow for entity consistency and corroboration checks.", status:"coming-soon", accent:"indigo" },
  { slug:"content-authority", category:"GEO Engine", engine:"GEO", tier:"Advanced", name:"Content Authority Agent", description:"The depth and support around topics the organization should own.", focus:"Planned workflow for authority coverage and supporting-content gaps.", status:"coming-soon", accent:"orange" },
  { slug:"geo-opportunity", category:"GEO Engine", engine:"GEO", tier:"Advanced", name:"GEO Opportunity Agent", description:"Turns AI visibility and citation gaps into a sequenced work plan.", focus:"Planned workflow for prioritizing content, entity and source actions.", status:"coming-soon", accent:"indigo" },
];

export const agentCategories = ["All agents", "SEO Engine", "AEO Engine", "GEO Engine"];

export function getAgent(slug: string): AgentDefinition | undefined {
  return agents.find((agent) => agent.slug === slug);
}
