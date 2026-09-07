const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
const BASE = process.env.NODE_ENV === "production"
  ? "/api/agents/content-optimizer"
  : configured && /^https?:\/\//i.test(configured)
    ? configured.replace(/\/$/, "").replace(/\/api\/agents\/seo-audit$/, "/api/agents/content-optimizer")
    : "http://127.0.0.1:8000/api/agents/content-optimizer";

export interface OptimizerEvidence { id:string; label:string; observed:string; source_url:string|null; source_type:"page"|"supplied_text"|"serp"|"brief" }
export interface OptimizerAssessment { key:string; label:string; status:"good"|"review"|"not_assessed"; summary:string; evidence_ids:string[] }
export interface OptimizerAction { id:string; priority:"critical"|"high"|"medium"|"low"; category:string; issue:string; affected_section:string; observed_text:string; proposed_action:string; confidence:"high"|"medium"|"low"; effort:"small"|"medium"|"large"; impact_rationale:string; evidence_ids:string[] }
export interface ContentOptimizerResult { run_id:string; source_mode:"url"|"text"; source_url:string|null; target_keyword:string; audience:string; word_count:number; overall_score:number|null; assessed_checks:number; total_checks:number; assessments:OptimizerAssessment[]; actions:OptimizerAction[]; evidence:OptimizerEvidence[]; research_run_id:string|null; content_brief_id:string|null; warnings:string[]; limitations:string[]; generated_at:string }
export interface ContentOptimizerRequest { content_url?:string; content_text?:string; page_title?:string; meta_description?:string; target_keyword:string; secondary_keywords:string[]; audience:string; research_run_id?:string; content_brief_id?:string }
export interface ContentOptimizerRun { id:string; request:ContentOptimizerRequest; status:"queued"|"running"|"complete"|"failed"; stage:string; progress:number; result:ContentOptimizerResult|null; error:string|null }

async function request<T>(path:string, init?:RequestInit):Promise<T>{
  const response=await fetch(`${BASE}${path}`,{...init,cache:"no-store",headers:{"Content-Type":"application/json",...init?.headers}});
  if(!response.ok){const body=await response.json().catch(()=>null) as {detail?:string}|null;throw new Error(body?.detail||`Request failed with HTTP ${response.status}`)}
  if(response.status===204)return undefined as T;
  return response.json() as Promise<T>;
}
export const createContentOptimizerRun=(body:ContentOptimizerRequest)=>request<ContentOptimizerRun>("/runs",{method:"POST",body:JSON.stringify(body)});
export const getContentOptimizerRun=(id:string)=>request<ContentOptimizerRun>(`/runs/${id}`);
export const processContentOptimizerRun=(id:string)=>request<ContentOptimizerRun>(`/runs/${id}/process`,{method:"POST"});
export const retryContentOptimizerRun=(id:string)=>request<ContentOptimizerRun>(`/runs/${id}/retry`,{method:"POST"});
export const deleteContentOptimizerRun=(id:string)=>request<void>(`/runs/${id}`,{method:"DELETE"});
