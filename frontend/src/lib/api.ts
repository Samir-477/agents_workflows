const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  (process.env.NODE_ENV === "production" ? "/api/backend" : "http://127.0.0.1:8000");

export type AuditStatus = "queued" | "running" | "complete" | "failed";

export interface CreateAuditInput {
  url: string;
  business_description?: string;
  audit_reason?: string;
  important_urls?: string[];
  crawl_limit?: number;
}

export interface AuditRecord {
  id: string;
  requested_url: string;
  business_description: string | null;
  audit_reason: string | null;
  important_urls: string[];
  crawl_limit: number;
  status: AuditStatus;
  stage: string;
  progress: number;
  warnings: string[];
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditResponse {
  audit: AuditRecord;
  pages_crawled: number;
  findings_count: number;
  report_available: boolean;
}

export interface AuditHistoryResponse {
  items: AuditResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditFinding {
  rule_id: string;
  title: string;
  severity: "critical" | "important" | "minor";
  confidence: "high" | "medium" | "low";
  score: number;
  affected_urls: string[];
  evidence: string;
  why_it_matters: string;
  recommendation: string;
}

export interface AuditReport {
  audit_id: string;
  requested_url: string;
  executive_summary: string;
  site_score: number | null;
  pages_crawled: number;
  severity_counts: Record<string, number>;
  quick_wins: string[];
  findings: AuditFinding[];
  limitations: string[];
  generated_with_llm: boolean;
  generated_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
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

export function createAudit(input: CreateAuditInput): Promise<AuditResponse> {
  return request<AuditResponse>("/audits", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getAuditHistory(page = 1, limit = 10, query = ""): Promise<AuditHistoryResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String((page - 1) * limit),
  });
  if (query.trim()) params.set("query", query.trim());
  return request<AuditHistoryResponse>(`/audits?${params.toString()}`);
}

export function deleteAudit(auditId: string): Promise<void> {
  return request<void>(`/audits/${auditId}`, { method: "DELETE" });
}

export function getAudit(auditId: string): Promise<AuditResponse> {
  return request<AuditResponse>(`/audits/${auditId}`);
}

export function processAudit(auditId: string): Promise<AuditResponse> {
  return request<AuditResponse>(`/audits/${auditId}/process`, { method: "POST" });
}

export function getAuditReport(auditId: string): Promise<AuditReport> {
  return request<AuditReport>(`/audits/${auditId}/report`);
}

export function retryAudit(auditId: string): Promise<AuditResponse> {
  return request<AuditResponse>(`/audits/${auditId}/retry`, { method: "POST" });
}

export function getAuditPdfUrl(auditId: string): string {
  return `${API_BASE_URL}/audits/${auditId}/report.pdf`;
}
