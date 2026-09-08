const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
const localApiRoot = configuredApiUrl && /^https?:\/\//i.test(configuredApiUrl)
  ? configuredApiUrl.replace(/\/$/, "").replace(/\/api\/agents\/seo-audit$/, "/api")
  : "http://127.0.0.1:8000/api";
const BASE = (process.env.NODE_ENV === "production" ? "/api" : localApiRoot) + "/agents/local-seo/generations";

export interface LocalCopy {
  title: string;
  meta_description: string;
  headline: string;
  introduction: string;
  sections: { heading: string; body: string }[];
  faqs: { question: string; answer: string }[];
  call_to_action: string;
}

export interface LocalPage {
  area: string;
  kind: string;
  suggested_slug: string;
  content: LocalCopy;
  business_details: Record<string, string>;
  json_ld: Record<string, unknown>;
  title_characters: number;
  description_characters: number;
  call_url: string | null;
  directions_url: string | null;
  existing_link_candidates: string[];
  proposed_sibling_slugs: string[];
  review_tasks: string[];
}

export interface LocalRun {
  id: string;
  status: "queued" | "running" | "complete" | "failed";
  stage: string;
  progress: number;
  error: string | null;
  result: {
    pages: LocalPage[];
    warnings: string[];
    limitations: string[];
    maps_candidates: { place_id: string; area: string; maps_url: string; name?: string }[];
  } | null;
}

export async function localApi<T>(path = "", method = "GET", body?: unknown): Promise<T> {
  const response = await fetch(BASE + path, {
    method, cache: "no-store",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(typeof data?.detail === "string" ? data.detail : `Request failed (${response.status}). Check the input and try again.`);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

export const deleteLocalRun = (id: string) => localApi<void>(`/${id}`, "DELETE");
