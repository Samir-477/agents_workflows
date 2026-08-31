const rawMetadataApiUrl = process.env.NEXT_PUBLIC_META_API_URL?.trim();
const rawAuditApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

function localMetadataBase(): string {
  if (rawMetadataApiUrl && /^https?:\/\//i.test(rawMetadataApiUrl)) {
    return rawMetadataApiUrl.replace(/\/$/, "");
  }
  if (rawAuditApiUrl && /^https?:\/\//i.test(rawAuditApiUrl)) {
    return rawAuditApiUrl
      .replace(/\/$/, "")
      .replace(/\/api\/agents\/seo-audit$/, "/api/agents/meta-title-description");
  }
  return "http://127.0.0.1:8000/api/agents/meta-title-description";
}

const API_BASE_URL =
  process.env.NODE_ENV === "production"
    ? "/api/agents/meta-title-description"
    : localMetadataBase();

export type GenerationStatus = "queued" | "running" | "complete" | "failed";
export type GenerationStage =
  | "queued"
  | "parsing"
  | "generating"
  | "validating"
  | "deduplicating"
  | "recommending"
  | "complete"
  | "failed";

export interface ParsedPageBrief {
  page_key: string;
  page_name: string;
  page_type: string;
  topic: string;
  primary_keyword: string | null;
  keyword_source: "provided" | "inferred" | "not_supplied";
  secondary_terms: string[];
  audience: string | null;
  search_intent: string;
  brand: string | null;
  language: string;
  verified_facts: string[];
  missing_context: string[];
}

export interface ParsedGenerationBrief {
  pages: ParsedPageBrief[];
  shared_brand_guidance: string | null;
  warnings: string[];
}

export interface MetadataOption {
  id: string;
  text: string;
  character_count: number;
  length_status: "short" | "good" | "long";
  intent: string;
  angle: string;
  rationale: string;
  score: number;
  recommended: boolean;
  issues: string[];
}

export interface PageMetadataResult {
  page_key: string;
  page_name: string;
  page_type: string;
  search_intent: string;
  primary_keyword: string | null;
  keyword_source: "provided" | "inferred" | "not_supplied";
  titles: MetadataOption[];
  descriptions: MetadataOption[];
  recommended_title_id: string;
  recommended_description_id: string;
  brand_guidance: string;
  warnings: string[];
}

export interface MetadataGenerationResult {
  generation_id: string;
  pages: PageMetadataResult[];
  batch_warnings: string[];
  generated_at: string;
}

export interface MetadataGenerationRecord {
  id: string;
  prompt: string;
  status: GenerationStatus;
  stage: GenerationStage;
  progress: number;
  parsed_brief: ParsedGenerationBrief | null;
  result: MetadataGenerationResult | null;
  warnings: string[];
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface MetadataGenerationResponse {
  generation: MetadataGenerationRecord;
  result_available: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? `Request failed with HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function createMetadataGeneration(
  prompt: string,
): Promise<MetadataGenerationResponse> {
  return request<MetadataGenerationResponse>("/generations", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export function getMetadataGeneration(
  generationId: string,
): Promise<MetadataGenerationResponse> {
  return request<MetadataGenerationResponse>(`/generations/${generationId}`);
}

export function processMetadataGeneration(
  generationId: string,
): Promise<MetadataGenerationResponse> {
  return request<MetadataGenerationResponse>(`/generations/${generationId}/process`, {
    method: "POST",
  });
}

export function getMetadataResult(
  generationId: string,
): Promise<MetadataGenerationResult> {
  return request<MetadataGenerationResult>(`/generations/${generationId}/result`);
}

export function retryMetadataGeneration(
  generationId: string,
): Promise<MetadataGenerationResponse> {
  return request<MetadataGenerationResponse>(`/generations/${generationId}/retry`, {
    method: "POST",
  });
}

export function deleteMetadataGeneration(generationId: string): Promise<void> {
  return request<void>(`/generations/${generationId}`, { method: "DELETE" });
}
