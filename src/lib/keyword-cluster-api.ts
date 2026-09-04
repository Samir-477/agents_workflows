const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

function localBase(): string {
  if (configuredApiUrl && /^https?:\/\//i.test(configuredApiUrl)) {
    return configuredApiUrl
      .replace(/\/$/, "")
      .replace(/\/api\/agents\/seo-audit$/, "/api/agents/keyword-cluster");
  }
  return "http://127.0.0.1:8000/api/agents/keyword-cluster";
}

const API_BASE_URL = process.env.NODE_ENV === "production" ? "/api/agents/keyword-cluster" : localBase();

export type KeywordClusterStatus = "queued" | "running" | "complete" | "failed";
export type KeywordClusterStage = "queued" | "parsing" | "clustering" | "consolidating" | "planning" | "validating" | "complete" | "failed";
export type SearchIntent = "informational" | "commercial" | "transactional" | "navigational" | "mixed";

export interface KeywordItem { keyword: string; volume: number | null; }
export interface KeywordClusterItem {
  id: string; name: string; pillar_name: string; role: "pillar" | "supporting";
  intent: SearchIntent; primary_keyword: string; keywords: KeywordItem[]; reasoning: string;
  recommended_page_type: string; suggested_title: string; suggested_slug: string;
  build_priority: number; total_volume: number | null; confidence: "high" | "medium" | "low";
  priority_factors: string[];
}
export interface PillarPlan {
  name: string; primary_keyword: string; suggested_title: string; suggested_slug: string;
  cluster_ids: string[]; supporting_page_ids: string[]; intent: SearchIntent;
  build_priority: number; total_volume: number | null;
  recommendation_status: "established" | "candidate"; rationale: string;
}
export interface InternalLinkRecommendation {
  source_cluster_id: string; target_cluster_id: string; source_slug: string;
  target_slug: string; anchor_text: string; reason: string;
}
export interface KeywordClusterResult {
  generation_id: string; input_count: number; unique_keyword_count: number; duplicate_count: number;
  clusters: KeywordClusterItem[]; pillars: PillarPlan[]; internal_links: InternalLinkRecommendation[];
  strategy_summary: string; assumptions: string[]; warnings: string[]; generated_at: string;
}
export interface KeywordClusterRecord {
  id: string; raw_keywords: string; status: KeywordClusterStatus; stage: KeywordClusterStage;
  progress: number; parsed_keywords: KeywordItem[]; result: KeywordClusterResult | null;
  warnings: string[]; error: string | null; created_at: string; updated_at: string;
}
export interface KeywordClusterResponse { generation: KeywordClusterRecord; result_available: boolean; }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string | { msg?: string }[] } | null;
    const detail = Array.isArray(payload?.detail)
      ? payload.detail.map((item) => item.msg).filter(Boolean).join(" ")
      : payload?.detail;
    throw new Error(detail || `Request failed with HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const createKeywordClusterGeneration = (keywords: string) =>
  request<KeywordClusterResponse>("/generations", { method: "POST", body: JSON.stringify({ keywords }) });
export const getKeywordClusterGeneration = (id: string) => request<KeywordClusterResponse>(`/generations/${id}`);
export const processKeywordClusterGeneration = (id: string) => request<KeywordClusterResponse>(`/generations/${id}/process`, { method: "POST" });
export const getKeywordClusterResult = (id: string) => request<KeywordClusterResult>(`/generations/${id}/result`);
export const retryKeywordClusterGeneration = (id: string) => request<KeywordClusterResponse>(`/generations/${id}/retry`, { method: "POST" });
export const deleteKeywordClusterGeneration = (id: string) => request<void>(`/generations/${id}`, { method: "DELETE" });
