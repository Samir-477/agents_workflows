export const diagnosisBase = "/api/diagnoses";

export const diagnosisAgents = ["seo_audit", "ai_visibility", "internal_linking", "serp_competitor", "keyword_cluster", "metadata", "schema_markup", "content_brief", "local_seo", "content_optimizer"];
export const diagnosisLabels: Record<string, string> = {
  capture: "Capture shared page evidence", seo_audit: "SEO/AEO Audit", ai_visibility: "AI Visibility", internal_linking: "Internal Linking", serp_competitor: "SERP & Competitor", keyword_cluster: "Keyword Clustering", metadata: "Metadata", schema_markup: "Schema Markup", content_brief: "Content Brief", local_seo: "Local SEO", content_optimizer: "Content Optimizer", report: "Assemble management report",
};
const AGENT_ROUTE_SLUG: Record<string, string> = {
  seo_audit: "seo-audit", ai_visibility: "ai-visibility", internal_linking: "internal-linking",
  serp_competitor: "serp-competitor", keyword_cluster: "keyword-cluster",
  metadata: "meta-title-description", schema_markup: "schema-markup",
  content_brief: "content-brief", local_seo: "local-seo", content_optimizer: "content-optimizer",
};
export function diagnosisAgentRunHref(agent: string, runId: string): string {
  return `/agents/${AGENT_ROUTE_SLUG[agent]}/runs/${runId}`;
}
export type Evidence = { id: string; title?: string; source_label?: string; source_kind?: string; source_url: string; observed: string; observed_value?: string; expected_value?: string | null; location?: string; excerpt?: string | null; fix_example?: string | null; fix_label?: string | null; presentation_kind?: "standard"|"json_parse_error"|"schema_identity_mismatch"|"metadata_length"|"image_alt"|"serp_sample"; captured_at: string; method: string; confidence?: string; support_type?: string; verification?: string; visual_url?: string | null; agent: string };
export type Finding = { id: string; title: string; observation: string; business_relevance: string; action: string; classification: string; classification_label?: string; priority: string; primary_agent: string; supporting_agents: string[]; evidence_ids: string[]; owner: string; completion_criteria: string };
export type EvidenceExplanation = { evidence_id: string; plain_language: string; example: string };
export type CaseManagement = { section_kind?: "finding" | "assessment"; source: string; issue_identified: string; finding_ids: string[]; evidence_ids: string[]; evidence_explanations: EvidenceExplanation[]; why_management_should_care: string; other_findings: string[]; recommended_actions: string[]; limitation: string };
export type Case = { agent: string; agent_label: string; heading: string; status: string; output_quality?: string; contribution_role?: "primary"|"supporting"|"assessment"; contribution_label?: string; run_id: string | null; finding_ids: string[]; observations: string[]; proposed_outputs: string[]; limitations: string[]; owner: string; urgency?: {label:string; timeframe:string}; management?: CaseManagement };
export type AgentScoreArea = { label: string; score: number; basis: string };
export type AgentMeasurement = { label: string; value: string; note: string };
export type AgentBenchmark = { label: string; observed: string; target: string; basis: string; evidence_id: string };
export type AgentAction = { finding_id: string | null; title: string; action: string; rationale: string; owner: string; priority: string; impact: string; effort: string; timeframe: string; steps: string[]; done_when: string };
export type AgentFix = { evidence_id: string; title: string; context: string; current: string; replacement: string; language: string };
export type AgentSuccessMetric = { metric: string; current: string; target: string; window: string; basis: string };
export type AgentTrace = { step: string; status: string; reference: string; detail: string; at: string };
export type AgentMethod = { title: string; description: string };
export type AgentReport = { agent: string; agent_label: string; heading: string; score: number; score_status: {label:string;tone:string}; score_basis: string; score_breakdown: AgentScoreArea[]; assessed_area_count: number; critical_count: number; warning_count: number; finding_count: number; executive_summary: string; management_relevance: string; measurements: AgentMeasurement[]; finding_ids: string[]; evidence_ids: string[]; benchmarks: AgentBenchmark[]; action_plan: AgentAction[]; fixes: AgentFix[]; success_metrics: AgentSuccessMetric[]; trace: AgentTrace[]; method: AgentMethod[]; limitations: string[]; output_quality: string };
export type SessionScore = { score: number; score_status: {label:string;tone:string}; agent_count: number; finding_count: number; critical_count: number; score_basis: string };
export type EngineScore = { engine:"SEO"|"AEO"|"GEO"; score:number; score_status:{label:string;tone:string}; agent_count:number; finding_count:number; critical_count:number; warning_count:number; weakest_agent:string; weakest_agent_label:string; strongest_agent:string; strongest_agent_label:string };
export type IntelligencePriority = { id:string; rank:number; finding_id:string|null; title:string; action:string; rationale:string; risk_if_delayed:string; agent:string; agent_label:string; engine:"SEO"|"AEO"|"GEO"; priority:string; impact:string; effort:string; timeframe:string; owner:string; done_when:string; priority_score:number; score_factors:{severity:number;impact:number;effort:number;engine_weakness:number} };
export type SessionIntelligence = { engine_scores:EngineScore[]; missing_engines:("SEO"|"AEO"|"GEO")[]; decision_summary:string; constraint:{engine:"SEO"|"AEO"|"GEO";score:number}|null; priorities:IntelligencePriority[]; quick_win_ids:string[]; risk_ids:string[]; delivery:{now:string[];next:string[];later:string[]}; method:string };
export type ManagementReport = { title: string; overview: string; page_url: string; research_query: string; identity?: {property_name:string; brand?:string|null; destination?:string|null; confidence:string; supporting_sources:string[]; rejected_candidates:{value:string;reason:string}[]; branded_query:string; generic_query?:string|null}; captured_at: string | null; generated_at: string; version: number; scope: string[]; findings: Finding[]; cases: Case[]; evidence: Record<string, Evidence>; agent_reports?: Record<string, AgentReport>; session_score?: SessionScore; session_intelligence?: SessionIntelligence; limitations: string[]; management_editor?: {status:string; source:string; model?:string; note?:string; edited_cases?:number; deterministic_cases?:number}; narrative: { source: string; text?: string; status?: string; note?: string } };
export type Diagnosis = { id: string; status: string; request: { page_url: string; audience: string; business_goal: string; page_limit: number; country: string; language: string; model_provider: string; run_mode: "diagnosis" | "individual"; selected_agents: string[] }; created_at: string; tasks: Record<string, { status: string; attempts: number; error: string | null; run_id: string | null; result: { reason?: string } }>; report: ManagementReport | null };
export type HistoryItem = { id: string; url: string; status: string; created_at: string; run_mode: "diagnosis" | "individual"; selected_agents: string[]; finding_count: number };
export type HistoryPage = { items: HistoryItem[]; page: number; page_size: number; total: number; total_pages: number };

export async function diagnosisRequest<T>(path: string, body?: unknown, method?: string): Promise<T> {
  const response = await fetch(`${diagnosisBase}${path}`, { method: method || (body ? "POST" : "GET"), credentials: "include", cache: "no-store", headers: { "Content-Type": "application/json" }, ...(body ? { body: JSON.stringify(body) } : {}) });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const detail = error?.detail;
    throw new Error(typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((e: {msg: string}) => e.msg).join("; ") : `Request failed (${response.status}). Please retry.`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
