const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

function localBase(): string {
  if (configuredApiUrl && /^https?:\/\//i.test(configuredApiUrl)) {
    return configuredApiUrl.replace(/\/$/, "").replace(/\/api\/agents\/seo-audit$/, "/api/agents/internal-linking");
  }
  return "http://127.0.0.1:8000/api/agents/internal-linking";
}

const API_BASE_URL = process.env.NODE_ENV === "production" ? "/api/agents/internal-linking" : localBase();

export type InternalLinkStatus = "queued" | "running" | "complete" | "failed";
export type InternalLinkStage = "queued" | "validating" | "crawling" | "mapping" | "analyzing" | "refining" | "validating_results" | "complete" | "failed";
export type RecommendationType = "orphan" | "orphan_candidate" | "underlinked_important" | "contextual_gap" | "weak_anchor";

export interface InternalLinkRecommendation {
  id: string; recommendation_type: RecommendationType; priority_score: number;
  priority_tier: "critical" | "important" | "opportunity"; confidence: "high" | "medium" | "low";
  source_url: string; source_title: string; target_url: string; target_title: string;
  current_anchor: string | null; anchor_options: string[]; placement_heading: string | null;
  placement_snippet: string | null; placement_note: string; reasoning: string;
  evidence: string[]; score_factors: string[];
}

export interface PageLinkSummary {
  url: string; title: string; depth: number; page_role: string; inbound_sources: number;
  contextual_inbound_sources: number; outbound_targets: number; contextual_outbound_targets: number;
  important: boolean; orphan_status: "confirmed" | "candidate" | "not_orphan";
}

export interface InternalLinkResult {
  audit_id: string; requested_url: string; normalized_origin: string; pages_crawled: number;
  discovered_url_count: number; coverage_complete: boolean; observed_edge_count: number;
  contextual_edge_count: number; confirmed_orphan_count: number; orphan_candidate_count: number;
  weak_anchor_count: number; recommendations: InternalLinkRecommendation[]; pages: PageLinkSummary[];
  warnings: string[]; limitations: string[]; generated_with_llm: boolean; generated_at: string;
}

export interface InternalLinkRecord {
  id: string; requested_url: string; normalized_origin: string | null;
  business_description: string | null; audit_goal: string | null; important_urls: string[];
  crawl_limit: number; status: InternalLinkStatus; stage: InternalLinkStage; progress: number;
  result: InternalLinkResult | null; warnings: string[]; error: string | null;
  created_at: string; updated_at: string;
}

export interface InternalLinkResponse { audit: InternalLinkRecord; result_available: boolean; }
export interface InternalLinkCreateInput { url: string; business_description?: string; audit_goal?: string; important_urls?: string[]; crawl_limit?: number; }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, cache: "no-store", headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string | { msg?: string }[] } | null;
    const detail = Array.isArray(payload?.detail) ? payload.detail.map((item) => item.msg).filter(Boolean).join(" ") : payload?.detail;
    throw new Error(detail || `Request failed with HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const createInternalLinkAudit = (input: InternalLinkCreateInput) => request<InternalLinkResponse>("/audits", { method: "POST", body: JSON.stringify(input) });
export const getInternalLinkAudit = (id: string) => request<InternalLinkResponse>(`/audits/${id}`);
export const processInternalLinkAudit = (id: string) => request<InternalLinkResponse>(`/audits/${id}/process`, { method: "POST" });
export const getInternalLinkResult = (id: string) => request<InternalLinkResult>(`/audits/${id}/result`);
export const retryInternalLinkAudit = (id: string) => request<InternalLinkResponse>(`/audits/${id}/retry`, { method: "POST" });
export const deleteInternalLinkAudit = (id: string) => request<void>(`/audits/${id}`, { method: "DELETE" });
