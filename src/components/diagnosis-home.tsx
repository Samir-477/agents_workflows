"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { agents } from "@/data/agents";
import { diagnosisRequest, type Diagnosis } from "@/lib/diagnosis-api";

const dependencies:Record<string,string[]>={
  keyword_cluster:["serp_competitor"],
  content_brief:["serp_competitor","keyword_cluster"],
  content_optimizer:["serp_competitor","keyword_cluster","content_brief"],
};

const activeAgents=agents.filter(agent=>agent.status==="active"&&agent.diagnosisId);
const groups=(["SEO","AEO","GEO"] as const).map(engine=>({category:`${engine} Engine`,items:activeAgents.filter(agent=>agent.engine===engine)})).filter(group=>group.items.length);

function withDependencies(values:Set<string>) {
  const expanded=new Set(values);
  let changed=true;
  while(changed){changed=false;for(const id of [...expanded])for(const dependency of dependencies[id]||[])if(!expanded.has(dependency)){expanded.add(dependency);changed=true;}}
  return expanded;
}

export function DiagnosisHome() {
  const router=useRouter();
  const [selected,setSelected]=useState(()=>new Set(activeAgents.map(agent=>agent.diagnosisId!)));
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);

  function toggle(id:string) {
    setSelected(current=>{
      if(!current.has(id)) return withDependencies(new Set([...current,id]));
      const next=new Set(current); next.delete(id);
      let changed=true;
      while(changed){changed=false;for(const candidate of [...next])if((dependencies[candidate]||[]).some(required=>!next.has(required))){next.delete(candidate);changed=true;}}
      return next;
    });
  }

  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if(!selected.size){setError("Select at least one agent.");return;}
    setBusy(true);setError("");
    const data=new FormData(event.currentTarget);
    try {
      const run=await diagnosisRequest<Diagnosis>("",{page_url:data.get("url"),audience:"",business_goal:"",page_limit:8,country:"in",language:"en",model_provider:"configured",run_mode:"diagnosis",selected_agents:[...selected]});
      router.push(`/diagnosis/${run.id}`);
    } catch(caught){setError(caught instanceof Error?caught.message:"Unable to start this run.");setBusy(false);}
  }

  return <main className="min-h-[calc(100vh-68px)] bg-[#f8fafb] px-5 py-12 sm:px-7"><div className="mx-auto max-w-[920px]"><p className="text-[11px] font-semibold uppercase tracking-[.22em] text-[#7a8286]">New run</p><h1 className="mt-4 text-4xl font-semibold tracking-[-.045em] text-[#121719]">Analyse a URL</h1><p className="mt-3 max-w-3xl text-base leading-7 text-[#70787c]">Point the suite at a resort page. Pick one specialist or run the complete diagnosis—the results are grouped into one saved management report.</p>
    <form onSubmit={submit} className="mt-9 space-y-6"><section className="rounded-[22px] border border-[#dde2e0] bg-white p-6 shadow-[0_10px_30px_rgba(22,31,27,.06)]"><label htmlFor="diagnosis-url" className="text-[13px] font-semibold text-[#272c2e]">Page URL</label><input id="diagnosis-url" name="url" type="url" required maxLength={2048} placeholder="https://www.sterlingholidays.com/resorts-hotels/regalia-agra" className="mt-2.5 h-13 w-full rounded-full border border-[#dce1df] bg-white px-4 text-sm shadow-sm outline-none transition placeholder:text-[#92999c] focus:border-[#07814d] focus:ring-4 focus:ring-[#07814d]/10"/></section>
      <section className="overflow-hidden rounded-[22px] border border-[#dde2e0] bg-white shadow-[0_10px_30px_rgba(22,31,27,.06)]"><header className="flex items-center justify-between border-b border-[#e4e7e6] px-6 py-5"><div><h2 className="text-base font-semibold">Agents</h2><p className="mt-1 text-xs text-[#71797d]">{selected.size} of {activeAgents.length} selected</p></div><button type="button" onClick={()=>setSelected(selected.size?new Set():new Set(activeAgents.map(agent=>agent.diagnosisId!)))} className="text-xs font-medium text-[#26302c] hover:text-[#007846]">{selected.size?"Clear all":"Select all"}</button></header>
        {groups.map(group=><div key={group.category} className="border-b border-[#e4e7e6] px-5 py-6 last:border-b-0 sm:px-6"><p className="mb-4 text-[11px] font-semibold uppercase tracking-[.18em] text-[#7b8387]">{group.category}</p><div className="grid gap-1 sm:grid-cols-2">{group.items.map(agent=>{const id=agent.diagnosisId!;const checked=selected.has(id);return <button key={id} type="button" role="checkbox" aria-checked={checked} onClick={()=>toggle(id)} className={`flex min-h-17 items-start gap-3 rounded-[18px] px-3.5 py-3 text-left transition ${checked?"bg-[#f0f2f1]":"hover:bg-[#f8faf9]"}`}><span className={`mt-0.5 grid h-4.5 w-4.5 shrink-0 place-items-center rounded-full border text-[10px] ${checked?"border-[#007846] bg-[#007846] text-white":"border-[#2c9a6c] text-transparent"}`}>✓</span><span><b className="block text-sm text-[#1b2022]">{agent.name}</b><span className="mt-1 block text-xs leading-5 text-[#778084]">{agent.description}</span></span></button>;})}</div></div>)}
      </section>
      <div className="flex flex-wrap items-center justify-between gap-5"><p className="max-w-xl text-xs leading-5 text-[#747c80]">Evidence capture and report assembly run automatically. Selecting Content Brief or Content Optimizer also selects the research tasks they require.</p><button disabled={busy||!selected.size} className="flex min-w-40 items-center justify-center gap-3 rounded-full bg-[#007846] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00683d] disabled:cursor-not-allowed disabled:opacity-50">{busy&&<span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"/>}{busy?"Starting…":`Run ${selected.size} agent${selected.size===1?"":"s"}`}</button></div>{error&&<p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
    </form>
  </div>{busy&&<div className="fixed inset-0 z-50 grid place-items-center bg-[#0b1510]/55 px-5 backdrop-blur-sm" role="status"><div className="w-full max-w-sm rounded-[24px] bg-white p-8 text-center shadow-2xl"><span className="mx-auto block h-8 w-8 animate-spin rounded-full border-[3px] border-[#bed8ca] border-t-[#007846]"/><h2 className="mt-5 text-xl font-semibold">Creating your run</h2><p className="mt-2 text-sm leading-6 text-[#747c80]">Saving the URL and preparing {selected.size} selected specialists.</p></div></div>}</main>;
}
