const SETTINGS_API_BASE =
  process.env.NODE_ENV === "production"
    ? "/api/settings"
    : "http://localhost:8000/api/settings";

export type ProviderName = "groq";

export interface ModelOption {
  id: string;
  label: string;
  release_tier: "production" | "preview";
}

export interface ProviderKeyStatus {
  provider: ProviderName;
  label: string;
  configured: boolean;
  source: "database" | "environment" | "not_configured";
  masked_key: string | null;
  updated_at: string | null;
}

export interface ProviderSettingsResponse {
  providers: ProviderKeyStatus[];
  active_provider: string | null;
  active_model: string | null;
  model_source: "database" | "environment";
  model_options: ModelOption[];
}

async function request<T>(path = "", init?: RequestInit): Promise<T> {
  const response = await fetch(`${SETTINGS_API_BASE}${path}`, {
    ...init,
    cache: "no-store",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? `Request failed with HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getProviderSettings(): Promise<ProviderSettingsResponse> {
  return request<ProviderSettingsResponse>("/providers");
}

export function saveProviderKey(
  provider: ProviderName,
  apiKey: string,
): Promise<ProviderSettingsResponse> {
  return request<ProviderSettingsResponse>(`/providers/${provider}`, {
    method: "PUT",
    body: JSON.stringify({ api_key: apiKey }),
  });
}

export function deleteProviderKey(
  provider: ProviderName,
): Promise<ProviderSettingsResponse> {
  return request<ProviderSettingsResponse>(`/providers/${provider}`, {
    method: "DELETE",
  });
}

export function saveModelSelection(model: string): Promise<ProviderSettingsResponse> {
  return request<ProviderSettingsResponse>("/model", {
    method: "PUT",
    body: JSON.stringify({ model }),
  });
}
