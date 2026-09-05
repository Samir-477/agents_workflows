const HISTORY_API_BASE =
  process.env.NODE_ENV === "production" ? "/api" : "http://127.0.0.1:8000/api";

export type AgentFilter = "all" | "seo-audit" | "meta-title-description" | "schema-markup" | "keyword-cluster" | "internal-linking" | "content-brief" | "ai-visibility";

export interface AgentRunSummary {
  id: string;
  agent_slug: Exclude<AgentFilter, "all">;
  agent_name: string;
  title: string;
  detail: string;
  status: string;
  stage: string;
  progress: number;
  result_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentRunHistoryResponse {
  items: AgentRunSummary[];
  total: number;
  limit: number;
  offset: number;
}

export async function getAgentRunHistory(
  page: number,
  limit: number,
  query: string,
  agent: AgentFilter,
): Promise<AgentRunHistoryResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String((page - 1) * limit),
    agent,
  });
  if (query.trim()) params.set("query", query.trim());
  const response = await fetch(`${HISTORY_API_BASE}/agent-runs?${params}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Unable to load run history (HTTP ${response.status}).`);
  }
  return response.json() as Promise<AgentRunHistoryResponse>;
}
