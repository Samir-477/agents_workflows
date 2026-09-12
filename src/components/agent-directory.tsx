"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { agents, type AgentDefinition, type AgentEngine } from "@/data/agents";

type EngineFilter = "All engines" | AgentEngine;

const engineMeta: Record<AgentEngine,{question:string;description:string;stages:string[];dot:string}> = {
  SEO:{question:"How do we get this page found?",description:"Search visibility across crawlability, on-page depth, demand, internal links and experience.",stages:["Crawl","Content","Demand","Links","Experience"],dot:"bg-[#2f6ee5]"},
  AEO:{question:"How do we make this page the answer?",description:"Answer readiness: the questions people ask, whether you answer them clearly, and whether machines can extract the answer.",stages:["Questions","Answer coverage","Gaps","FAQ","Structured answers","Opportunities"],dot:"bg-[#7c3aed]"},
  GEO:{question:"How do we get AI to mention, recommend and cite this page?",description:"AI visibility across prompts, mentions, citations, entity clarity and the authority models need before recommending you.",stages:["Prompts","Visibility","Mentions","Citations","Authority","Opportunities"],dot:"bg-[#087849]"},
};

function AgentCell({agent}:{agent:AgentDefinition}) {
  const active=agent.status==="active";
  const body=<><div className="flex items-start justify-between gap-5"><h3 className="text-[17px] font-semibold tracking-[-.025em] text-[#101617]">{agent.name}</h3><span className="shrink-0 text-[10px] font-medium uppercase tracking-[.14em] text-[#737d81]">{active?agent.tier:"Planned"}</span></div><p className="mt-2 text-sm leading-6 text-[#687277]">{agent.description}</p><p className="mt-4 border-l-2 border-[#dfe4e2] pl-3 text-[13px] leading-5 text-[#7a8387]">{agent.focus}</p><div className="mt-5 flex items-center justify-between text-xs"><span className="text-[#747e82]">{active?"Runnable evidence-backed workflow":"Pipeline not yet available"}</span>{active?<span className="font-medium text-[#087849]">Open →</span>:null}</div></>;
  const classes="block min-h-[220px] bg-white px-7 py-7 transition sm:px-8 "+(active?"hover:bg-[#eaf1ed]":"");
  return active?<Link href={`/agents/${agent.slug}`} className={classes}>{body}</Link>:<article className={classes}>{body}</article>;
}

export function AgentDirectory() {
  const [query,setQuery]=useState("");
  const [engine,setEngine]=useState<EngineFilter>("All engines");
  const filtered=useMemo(()=>agents.filter(agent=>{
    const needle=query.trim().toLowerCase();
    const matchesQuery=!needle||`${agent.name} ${agent.description} ${agent.focus} ${agent.engine}`.toLowerCase().includes(needle);
    return matchesQuery&&(engine==="All engines"||agent.engine===engine);
  }),[query,engine]);
  const shownEngines=(Object.keys(engineMeta) as AgentEngine[]).filter(name=>filtered.some(agent=>agent.engine===name));
  return <section className="border-t border-[#e2e6e4] bg-[#f8fafb] py-12 sm:py-14"><div className="mx-auto max-w-[1240px] px-5 sm:px-7">
    <div className="flex flex-col gap-4 md:flex-row"><label className="sr-only" htmlFor="agent-search">Search agents</label><input id="agent-search" type="search" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Search 26 agents" className="h-12 w-full rounded-full border border-[#dce1df] bg-white px-5 text-sm shadow-sm outline-none focus:border-[#138154] focus:ring-4 focus:ring-[#138154]/10 md:max-w-[360px]"/><div className="inline-flex w-fit rounded-full border border-[#dce1df] bg-white p-1">{(["All engines","SEO","AEO","GEO"] as EngineFilter[]).map(item=><button key={item} type="button" onClick={()=>setEngine(item)} className={`rounded-full px-5 py-2 text-xs transition ${engine===item?"bg-[#f0f2f1] font-semibold text-[#151a1c]":"text-[#737c80] hover:text-[#151a1c]"}`}>{item}</button>)}</div></div>
    <p className="sr-only" aria-live="polite">{filtered.length} agents shown</p>
    {shownEngines.length?<div className="mt-10 space-y-8">{shownEngines.map(name=>{const meta=engineMeta[name];const items=filtered.filter(agent=>agent.engine===name);return <section key={name} className="overflow-hidden rounded-[24px] border border-[#dce1df] bg-white shadow-[0_12px_34px_rgba(24,33,29,.06)]"><header className="px-7 py-8 sm:px-8"><div className="flex items-center gap-3"><span className={`h-2.5 w-2.5 rounded-full ${meta.dot}`}/><h2 className="text-2xl font-semibold tracking-[-.04em]">{name} Engine</h2><span className="rounded-full bg-[#f1f3f2] px-3 py-1 text-[11px] font-semibold">{agents.filter(agent=>agent.engine===name).length} agents</span></div><p className="mt-5 text-lg font-medium tracking-[-.02em]">“{meta.question}”</p><p className="mt-2 max-w-3xl text-sm leading-6 text-[#697277]">{meta.description}</p><div className="mt-6 flex flex-wrap items-center gap-2">{meta.stages.map((stage,index)=><span key={stage} className="contents"><span className="rounded-full border border-[#dfe4e2] px-3 py-1.5 text-[11px] text-[#747d81]">{stage}</span>{index<meta.stages.length-1?<span className="text-[#c3c9c6]">›</span>:null}</span>)}</div></header><div className="grid border-t border-[#dfe3e1] md:grid-cols-2">{items.map((agent,index)=><div key={agent.slug} className={`${index>1?"border-t":""} ${index%2===1?"md:border-l":""} ${index===1?"border-t md:border-t-0":""} border-[#dfe3e1]`}><AgentCell agent={agent}/></div>)}</div></section>})}</div>:<div className="mt-10 rounded-[22px] border border-dashed border-[#d5dbd8] bg-white px-6 py-16 text-center text-sm text-[#737c80]">No agents match this search.</div>}
  </div></section>;
}
