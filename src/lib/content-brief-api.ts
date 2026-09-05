const rawApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

function localBase(): string {
  if (rawApiUrl && /^https?:\/\//i.test(rawApiUrl)) {
    return rawApiUrl.replace(/\/$/, "").replace(/\/api\/agents\/seo-audit$/, "/api/agents/content-brief");
  }
  return "http://127.0.0.1:8000/api/agents/content-brief";
}

const API_BASE_URL = process.env.NODE_ENV === "production" ? "/api/agents/content-brief" : localBase();

export interface ContentBriefCreate {
  target_keyword: string;
  audience: string;
  secondary_keywords: string[];
  angle?: string;
  business_goal?: string;
  product_context?: string;
  existing_urls: string[];
  source_notes?: string;
  content_mode: "new" | "rewrite";
}

export interface OutlineSection { heading_level: "H2" | "H3"; heading: string; purpose: string; talking_points: string[]; questions_answered: string[]; suggested_words: number; }
export interface CoverageItem { name: string; item_type: "topic" | "entity" | "concept" | "standard" | "tool"; why_include: string; source: "provided" | "inferred"; }
export interface FAQItem { question: string; answer_guidance: string; source: "provided" | "inferred"; }
export interface BriefLink { target_url: string; anchor_direction: string; placement_heading: string; reason: string; }
export interface ConversionNote { call_to_action: string; placement_heading: string; rationale: string; }
export interface ContentBriefDraft {
  suggested_title: string; search_intent: string; intent_confidence: "high" | "medium" | "low";
  intent_rationale: string; reader_job: string; recommended_format: string; tone_and_voice: string[];
  target_word_count_min: number; target_word_count_max: number; introduction_guidance: string;
  outline: OutlineSection[]; coverage: CoverageItem[]; faqs: FAQItem[]; internal_links: BriefLink[];
  conversion_notes: ConversionNote[]; assumptions: string[]; writer_checks: string[];
}
export interface BriefIssue { severity: "error" | "warning" | "note"; code: string; message: string; }
export interface ContentBriefResult {
  generation_id: string; target_keyword: string; audience: string; content_mode: "new" | "rewrite";
  brief: ContentBriefDraft; quality_score: number; ready_for_handoff: boolean; issues: BriefIssue[];
  warnings: string[]; evidence_limitations: string[]; generated_at: string;
}
export interface ContentBriefRecord {
  id: string; request: ContentBriefCreate; status: "queued" | "running" | "complete" | "failed";
  stage: string; progress: number; draft: ContentBriefDraft | null; result: ContentBriefResult | null;
  warnings: string[]; error: string | null; created_at: string; updated_at: string;
}
export interface ContentBriefResponse { generation: ContentBriefRecord; result_available: boolean; }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, cache: "no-store", headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string | Array<{ msg?: string }> } | null;
    const detail = Array.isArray(payload?.detail) ? payload.detail.map((item) => item.msg).filter(Boolean).join(" ") : payload?.detail;
    throw new Error(detail || `Request failed with HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const createContentBrief = (payload: ContentBriefCreate) => request<ContentBriefResponse>("/generations", { method: "POST", body: JSON.stringify(payload) });
export const getContentBrief = (id: string) => request<ContentBriefResponse>(`/generations/${id}`);
export const processContentBrief = (id: string) => request<ContentBriefResponse>(`/generations/${id}/process`, { method: "POST" });
export const getContentBriefResult = (id: string) => request<ContentBriefResult>(`/generations/${id}/result`);
export const retryContentBrief = (id: string) => request<ContentBriefResponse>(`/generations/${id}/retry`, { method: "POST" });
export const deleteContentBrief = (id: string) => request<void>(`/generations/${id}`, { method: "DELETE" });
