const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
function localBase() {
  if (configured && /^https?:\/\//i.test(configured)) return configured.replace(/\/$/, "").replace(/\/api\/agents\/seo-audit$/, "/api/agents/ai-visibility");
  return "http://127.0.0.1:8000/api/agents/ai-visibility";
}
const BASE = process.env.NODE_ENV === "production" ? "/api/agents/ai-visibility" : localBase();

export interface DimensionScore { dimension: string; score: number; summary: string; deductions: string[] }
export interface BotPolicy { user_agent: string; status: "allowed" | "blocked" | "not_declared"; evidence: string }
export interface VisibilityFinding { id: string; dimension: string; severity: "critical" | "important" | "opportunity"; confidence: string; title: string; observation: string; why_it_matters: string; recommendation: string; affected_urls: string[]; evidence: string[]; priority_score: number }
export interface PageVisibility { url: string; title: string; score: number; word_count: number; schema_types: string[]; question_sections: number; findings: number }
export interface VisibilityResult { audit_id: string; requested_url: string; normalized_origin: string; pages_crawled: number; discovered_url_count: number; coverage_complete: boolean; overall_score: number; dimensions: DimensionScore[]; bot_policies: BotPolicy[]; findings: VisibilityFinding[]; pages: PageVisibility[]; methodology: string; warnings: string[]; limitations: string[]; generated_at: string }
export interface VisibilityRecord { id: string; requested_url: string; normalized_origin: string | null; business_name: string | null; product_name: string | null; audit_goal: string | null; important_urls: string[]; crawl_limit: number; status: "queued" | "running" | "complete" | "failed"; stage: string; progress: number; result: VisibilityResult | null; warnings: string[]; error: string | null; created_at: string; updated_at: string }
export interface VisibilityResponse { audit: VisibilityRecord; result_available: boolean }
export interface VisibilityInput { url: string; business_name?: string; product_name?: string; audit_goal?: string; important_urls?: string[]; crawl_limit?: number }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { ...init, cache: "no-store", headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) { const body = await response.json().catch(() => null) as {detail?: string} | null; throw new Error(body?.detail || `Request failed with HTTP ${response.status}`); }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export const createVisibilityAudit = (body: VisibilityInput) => request<VisibilityResponse>("/audits", { method: "POST", body: JSON.stringify(body) });
export const getVisibilityAudit = (id: string) => request<VisibilityResponse>(`/audits/${id}`);
export const processVisibilityAudit = (id: string) => request<VisibilityResponse>(`/audits/${id}/process`, { method: "POST" });
export const retryVisibilityAudit = (id: string) => request<VisibilityResponse>(`/audits/${id}/retry`, { method: "POST" });
export const deleteVisibilityAudit = (id: string) => request<void>(`/audits/${id}`, { method: "DELETE" });
