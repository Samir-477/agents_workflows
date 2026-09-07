"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowIcon } from "@/components/icons";
import { createContentOptimizerRun } from "@/lib/content-optimizer-api";

export function ContentOptimizerForm(){
  const router=useRouter();
  const [mode,setMode]=useState<"url"|"text">("url"),[source,setSource]=useState(""),[keyword,setKeyword]=useState(""),[secondary,setSecondary]=useState(""),[audience,setAudience]=useState(""),[research,setResearch]=useState(""),[brief,setBrief]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState("");
  async function submit(event:FormEvent){event.preventDefault();setBusy(true);setError("");try{const run=await createContentOptimizerRun({...(mode==="url"?{content_url:source}:{content_text:source}),target_keyword:keyword,secondary_keywords:secondary.split(",").map(item=>item.trim()).filter(Boolean),audience,...(research?{research_run_id:research}:{}),...(brief?{content_brief_id:brief}:{})});router.push(`/agents/content-optimizer/runs/${run.id}`)}catch(caught){setError(caught instanceof Error?caught.message:"Optimization could not start.");setBusy(false)}}
  return <form onSubmit={submit} className="rounded-[24px] border border-[#deddd9] bg-white p-6 shadow-[0_20px_60px_rgba(26,26,36,.07)] sm:p-7">
    <fieldset><legend className="text-sm font-semibold">Content source</legend><div className="mt-2 grid grid-cols-2 gap-2 rounded-xl bg-[#f3f1ed] p-1">{(["url","text"] as const).map(item=><button key={item} type="button" onClick={()=>{setMode(item);setSource("")}} className={`rounded-lg px-3 py-2 text-sm font-semibold capitalize ${mode===item?"bg-white shadow-sm":"text-[#686871]"}`}>{item}</button>)}</div></fieldset>
    <label htmlFor="optimizer-source" className="mt-4 block text-sm font-semibold">{mode==="url"?"Page URL":"Existing content"}</label>
    {mode==="url"?<input id="optimizer-source" type="url" required value={source} onChange={event=>setSource(event.target.value)} placeholder="https://example.com/page" className="mt-2 h-12 w-full rounded-xl border px-4"/>:<textarea id="optimizer-source" required minLength={50} maxLength={100000} rows={8} value={source} onChange={event=>setSource(event.target.value)} placeholder="Paste the content or a Markdown outline…" className="mt-2 w-full rounded-xl border p-4"/>}
    <div className="mt-4 grid gap-3 sm:grid-cols-2"><label className="text-sm font-semibold">Primary keyword<input required minLength={2} value={keyword} onChange={event=>setKeyword(event.target.value)} className="mt-2 h-12 w-full rounded-xl border px-4"/></label><label className="text-sm font-semibold">Audience<input required minLength={2} value={audience} onChange={event=>setAudience(event.target.value)} className="mt-2 h-12 w-full rounded-xl border px-4"/></label></div>
    <label className="mt-4 block text-sm font-semibold">Secondary keywords <span className="font-normal text-[#85848b]">(comma separated)</span><input value={secondary} onChange={event=>setSecondary(event.target.value)} className="mt-2 h-12 w-full rounded-xl border px-4"/></label>
    <details className="mt-4 rounded-xl border bg-[#faf9f6] p-4"><summary className="cursor-pointer text-sm font-semibold">Attach saved research or brief</summary><div className="mt-3 grid gap-3 sm:grid-cols-2"><label className="text-xs font-semibold">SERP run ID<input value={research} onChange={event=>setResearch(event.target.value)} className="mt-2 h-11 w-full rounded-lg border bg-white px-3 font-normal"/></label><label className="text-xs font-semibold">Content brief ID<input value={brief} onChange={event=>setBrief(event.target.value)} className="mt-2 h-11 w-full rounded-lg border bg-white px-3 font-normal"/></label></div></details>
    <p className="mt-4 text-xs leading-5 text-[#777680]">For plain text, metadata, link, image, schema and freshness checks are shown as not assessed.</p>
    {error?<p role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>:null}
    <button disabled={busy} className="mt-5 flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] font-semibold text-white disabled:opacity-50">{busy?"Starting…":"Optimize content"}{!busy?<ArrowIcon className="h-5 w-5"/>:null}</button>
  </form>
}
