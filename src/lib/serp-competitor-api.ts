const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
const BASE = process.env.NODE_ENV === "production"
  ? "/api/agents/serp-competitor"
  : configured && /^https?:\/\//i.test(configured)
    ? configured.replace(/\/$/, "").replace(/\/api\/agents\/seo-audit$/, "/api/agents/serp-competitor")
    : "http://127.0.0.1:8000/api/agents/serp-competitor";

export interface SerpItem { position:number; title:string; url:string; snippet:string; domain:string }
export interface CompetitorEvidence { position:number; url:string; title:string; fetched:boolean; word_count:number|null; headings:string[]; schema_types:string[]; fetch_note:string|null }
export interface PatternEvidence { label:string; count:number; source_urls:string[] }
export interface SerpResult { run_id:string; target_keyword:string; country:string; language:string; observed_at:string; search_intent:string; intent_rationale:string; organic_results:SerpItem[]; questions:{question:string;source_url:string|null}[]; related_searches:string[]; answer_box:{title:string|null;answer:string;source_url:string|null}|null; competitors:CompetitorEvidence[]; common_headings:PatternEvidence[]; common_schema:PatternEvidence[]; topic_patterns:PatternEvidence[]; median_word_count:number|null; recommendations:string[]; warnings:string[]; limitations:string[]; snapshot_source_run_id:string|null }
export interface SerpRun { id:string; request:{target_keyword:string;country:string;language:string;result_limit:number;inspect_limit:number}; status:"queued"|"running"|"complete"|"failed"; stage:string; progress:number; result:SerpResult|null; error:string|null }

async function request<T>(path:string, init?:RequestInit):Promise<T>{
  const response=await fetch(`${BASE}${path}`,{...init,cache:"no-store",headers:{"Content-Type":"application/json",...init?.headers}});
  if(!response.ok){const body=await response.json().catch(()=>null) as {detail?:string}|null;throw new Error(body?.detail||`Request failed with HTTP ${response.status}`)}
  if(response.status===204)return undefined as T;
  return response.json() as Promise<T>;
}
export const createSerpRun=(body:{target_keyword:string;country:string;language:string;result_limit:number;inspect_limit:number})=>request<SerpRun>("/runs",{method:"POST",body:JSON.stringify(body)});
export const getSerpRun=(id:string)=>request<SerpRun>(`/runs/${id}`);
export const processSerpRun=(id:string)=>request<SerpRun>(`/runs/${id}/process`,{method:"POST"});
export const retrySerpRun=(id:string)=>request<SerpRun>(`/runs/${id}/retry`,{method:"POST"});
export const deleteSerpRun=(id:string)=>request<void>(`/runs/${id}`,{method:"DELETE"});
export const getSerperStatus=()=>request<{configured:boolean;provider:string}>("/status");
