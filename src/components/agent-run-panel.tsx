"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import type { AgentDefinition } from "@/data/agents";
import { diagnosisRequest, type Diagnosis } from "@/lib/diagnosis-api";

export function AgentRunPanel({ agent }: { agent: AgentDefinition }) {
  const router=useRouter();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!agent.diagnosisId) return;
    const data=new FormData(event.currentTarget);
    setBusy(true); setError("");
    try {
      const run=await diagnosisRequest<Diagnosis>("",{
        page_url:data.get("url"), audience:"", business_goal:"",
        page_limit:Number(data.get("page_limit")), country:"in", language:"en",
        model_provider:"configured", run_mode:"individual", selected_agents:[agent.diagnosisId],
      });
      router.push(`/diagnosis/${run.id}`);
    } catch(caught) { setError(caught instanceof Error?caught.message:"Unable to start this agent."); setBusy(false); }
  }
  return <aside className="lg:sticky lg:top-[92px]">
    <form onSubmit={submit} className="rounded-[22px] border border-[#dde2e0] bg-white p-6 shadow-[0_14px_34px_rgba(22,31,27,.07)]">
      <p className="text-[11px] font-semibold uppercase tracking-[.2em] text-[#7a8286]">Run this agent only</p><h2 className="mt-3 text-xl font-semibold tracking-[-.03em]">Configure the run</h2><p className="mt-2 text-[13px] leading-5 text-[#747c80]">Enter the page this {agent.name} should inspect. No other specialist will run.</p>
      <label htmlFor="agent-url" className="mt-6 block text-[13px] font-semibold">Page URL <span className="text-red-600">*</span></label><input id="agent-url" name="url" type="url" required maxLength={2048} placeholder="https://www.sterlingholidays.com/resorts-hotels/..." className="mt-2.5 h-12 w-full rounded-full border border-[#dce1df] px-4 text-[13px] shadow-sm outline-none focus:border-[#07814d] focus:ring-4 focus:ring-[#07814d]/10"/>
      <label htmlFor="page-limit" className="mt-6 block text-[13px] font-semibold">Evidence scope</label><select id="page-limit" name="page_limit" defaultValue="8" className="mt-2.5 h-12 w-full rounded-full border border-[#dce1df] bg-white px-4 text-[13px] shadow-sm outline-none focus:border-[#07814d] focus:ring-4 focus:ring-[#07814d]/10"><option value="1">Selected page only</option><option value="8">Page + supporting sample</option><option value="20">Expanded supporting sample</option></select>
      <p className="mt-5 rounded-2xl bg-[#f2f5f3] px-4 py-3 text-xs leading-5 text-[#68716d]">This standalone run uses the page evidence directly. Use New Run when you want supporting specialists and a combined diagnosis.</p>
      {error&&<p role="alert" className="mt-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      <button disabled={busy} className="mt-6 flex h-12 w-full items-center justify-center gap-3 rounded-full bg-[#007846] text-sm font-semibold text-white transition hover:bg-[#00683d] disabled:opacity-60">{busy&&<span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"/>}{busy?"Starting…":"Run agent"}</button><p className="mt-4 text-center text-[11px] text-[#858d90]">Runs are saved under Sessions.</p>
    </form>
  </aside>;
}
