const rawAuditApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

function localBase(): string {
  if (rawAuditApiUrl && /^https?:\/\//i.test(rawAuditApiUrl)) {
    return rawAuditApiUrl.replace(/\/$/, "").replace(/\/api\/agents\/seo-audit$/, "/api/agents/schema-markup");
  }
  return "http://127.0.0.1:8000/api/agents/schema-markup";
}

const API_BASE_URL = process.env.NODE_ENV === "production" ? "/api/agents/schema-markup" : localBase();

export type SchemaGenerationStatus = "queued" | "running" | "complete" | "failed";
export type SchemaGenerationStage = "queued" | "interpreting" | "compiling" | "validating" | "recommending" | "complete" | "failed";

export interface ValidationIssue { severity: "error" | "warning" | "note"; code: string; message: string; schema_type: string | null; }
export interface SchemaBlockResult {
  id: string; schema_type: string; name: string; json_ld: Record<string, unknown>;
  rationale: string; placement_scope: "page-specific" | "site-wide";
  placement_guidance: string; visible_evidence: string[]; missing_properties: string[]; issues: ValidationIssue[];
  publish_ready: boolean;
}
export interface SchemaGenerationResult {
  generation_id: string; page_name: string; page_url: string | null; page_type: string;
  script: string; graph: Record<string, unknown>; blocks: SchemaBlockResult[];
  warnings: string[]; validation_summary: string; publish_ready: boolean;
  blocking_issue_count: number; generated_at: string;
}
export interface SchemaGenerationRecord {
  id: string; prompt: string; status: SchemaGenerationStatus; stage: SchemaGenerationStage;
  progress: number; parsed_brief: unknown | null; result: SchemaGenerationResult | null;
  warnings: string[]; error: string | null; created_at: string; updated_at: string;
}
export interface SchemaGenerationResponse { generation: SchemaGenerationRecord; result_available: boolean; }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, cache: "no-store", headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed with HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const createSchemaGeneration = (prompt: string) => request<SchemaGenerationResponse>("/generations", { method: "POST", body: JSON.stringify({ prompt }) });
export const getSchemaGeneration = (id: string) => request<SchemaGenerationResponse>(`/generations/${id}`);
export const processSchemaGeneration = (id: string) => request<SchemaGenerationResponse>(`/generations/${id}/process`, { method: "POST" });
export const getSchemaResult = (id: string) => request<SchemaGenerationResult>(`/generations/${id}/result`);
export const retrySchemaGeneration = (id: string) => request<SchemaGenerationResponse>(`/generations/${id}/retry`, { method: "POST" });
export const deleteSchemaGeneration = (id: string) => request<void>(`/generations/${id}`, { method: "DELETE" });
