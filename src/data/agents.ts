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
  { slug:"schema-markup", diagnosisId:"schema_markup", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Schema & Structured Answers", description:"Structured data that matches visible content and page entities.", focus:"Generates validated JSON-LD with assumptions and review guidance.", status:"active", accent:"orange" },
  { slug:"question-discovery", diagnosisId:"question_discovery", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Question Discovery Agent", description:"Evidence-backed questions customers ask while choosing and planning a resort stay.", focus:"Discovers, classifies and hands off resort questions to SEO, AEO and GEO without inventing demand.", status:"active", accent:"indigo" },
  { slug:"answer-gap", diagnosisId:"answer_gap", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Answer Gap Agent", description:"Verifies whether observed customer questions receive direct, complete and extractable answers.", focus:"Maps each observed question to retained page evidence and routes verified gaps to Answer Optimization.", status:"active", accent:"indigo" },
  { slug:"answer-optimization", diagnosisId:"answer_optimization", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Answer Optimization Agent", description:"Drafts grounded, direct 40-60 word answers for the gaps Answer Gap verifies, or a fact-gathering action when the page has nothing to draft from.", focus:"Turns a verified answer gap into a reviewable draft without inventing a fact the page never stated.", status:"active", accent:"indigo" },
  { slug:"faq-intelligence", diagnosisId:"faq_intelligence", category:"AEO Engine", engine:"AEO", tier:"Core", name:"FAQ Intelligence Agent", description:"Audits coverage across ten standard resort FAQ categories and traces coverage to observed questions from validated answers.", focus:"Answers 'which guest questions does this page actually cover' rather than any single question in isolation.", status:"active", accent:"indigo" },
  { slug:"question-intent", diagnosisId:"question_intent", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Question Intent Agent", description:"Separates journey stage, query intent and topic, then sequences verified gaps with a transparent delivery heuristic.", focus:"Shows how observed questions map to Discover, Evaluate, Plan, Book and Manage, then routes each stage to the right specialist.", status:"active", accent:"indigo" },
  { slug:"answer-structure", diagnosisId:"answer_structure", category:"AEO Engine", engine:"AEO", tier:"Core", name:"Answer Structure Agent", description:"Tests whether retained answers are concise, self-contained and placed under useful headings.", focus:"Separates formatting and extractability weaknesses from missing-answer problems.", status:"active", accent:"indigo" },
  { slug:"aeo-opportunity", diagnosisId:"aeo_opportunity", category:"AEO Engine", engine:"AEO", tier:"Advanced", name:"AEO Opportunity Agent", description:"Turns verified AEO evidence into one deduplicated delivery queue.", focus:"Combines answer gaps, structure, FAQ coverage and journey stage without inventing demand or business impact.", status:"active", accent:"orange" },

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
