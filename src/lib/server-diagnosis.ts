import { cookies, headers } from "next/headers";

import type { Diagnosis, HistoryPage } from "@/lib/diagnosis-api";

async function diagnosisFetch<T>(path: string): Promise<T | null> {
  try {
    const requestHeaders = await headers();
    const cookieStore = await cookies();
    const host = requestHeaders.get("x-forwarded-host") || requestHeaders.get("host");
    if (!host) return null;
    const protocol = requestHeaders.get("x-forwarded-proto") ||
      (host.startsWith("localhost") || host.startsWith("127.0.0.1") ? "http" : "https");
    const response = await fetch(`${protocol}://${host}/api/diagnoses${path}`, {
      cache: "no-store",
      headers: { cookie: cookieStore.toString() },
    });
    if (!response.ok) return null;
    return await response.json() as T;
  } catch {
    return null;
  }
}

export function loadDiagnosis(id: string) {
  return diagnosisFetch<Diagnosis>(`/${encodeURIComponent(id)}`);
}

export function loadDiagnosisHistory(page = 1) {
  return diagnosisFetch<HistoryPage>(`?page=${page}&page_size=10`);
}
