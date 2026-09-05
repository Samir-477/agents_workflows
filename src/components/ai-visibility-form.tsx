"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowIcon, PlusIcon } from "@/components/icons";
import { createVisibilityAudit } from "@/lib/ai-visibility-api";

export function AIVisibilityForm() {
  const router = useRouter();
  const [url, setUrl] = useState(""); const [business, setBusiness] = useState(""); const [product, setProduct] = useState("");
  const [goal, setGoal] = useState(""); const [important, setImportant] = useState(""); const [limit, setLimit] = useState(10);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); setBusy(true); setError(""); try {
    const response = await createVisibilityAudit({ url, business_name: business || undefined, product_name: product || undefined, audit_goal: goal || undefined, important_urls: important.split(/\r?\n/).filter(Boolean), crawl_limit: limit });
    router.push(`/agents/ai-visibility/runs/${response.audit.id}`);
  } catch (caught) { setError(caught instanceof Error ? caught.message : "The audit could not start."); setBusy(false); } }
  return <form onSubmit={submit} className="rounded-[24px] border border-[#deddd9] bg-white p-6 shadow-[0_20px_60px_rgba(26,26,36,0.07)] sm:p-7">
    <label htmlFor="visibility-url" className="text-sm font-semibold">Public website URL</label>
    <input id="visibility-url" type="url" required value={url} onChange={e => setUrl(e.target.value)} placeholder="https://your-website.com" className="mt-3 h-16 w-full rounded-2xl border border-[#d9d8d4] px-5 outline-none focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
    <details className="group mt-4 rounded-2xl border border-[#dfdedb]"><summary className="flex cursor-pointer list-none items-center justify-between px-5 py-4 font-semibold">Optional entity context <PlusIcon className="h-4 w-4 transition group-open:rotate-45" /></summary><div className="grid gap-4 border-t border-[#eceae6] p-5 sm:grid-cols-2">
      <label className="text-sm font-semibold">Business name<input value={business} onChange={e=>setBusiness(e.target.value)} className="mt-2 h-11 w-full rounded-xl border px-3 font-normal" /></label>
      <label className="text-sm font-semibold">Product name<input value={product} onChange={e=>setProduct(e.target.value)} className="mt-2 h-11 w-full rounded-xl border px-3 font-normal" /></label>
      <label className="text-sm font-semibold sm:col-span-2">Important URLs, one per line<textarea value={important} onChange={e=>setImportant(e.target.value)} rows={3} className="mt-2 w-full rounded-xl border p-3 font-normal" /></label>
      <label className="text-sm font-semibold">Audit goal<input value={goal} onChange={e=>setGoal(e.target.value)} className="mt-2 h-11 w-full rounded-xl border px-3 font-normal" /></label>
      <label className="text-sm font-semibold">Page limit<input type="number" min={1} max={100} value={limit} onChange={e=>setLimit(Number(e.target.value))} className="mt-2 h-11 w-full rounded-xl border px-3 font-normal" /></label>
    </div></details>
    {error ? <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
    <button disabled={busy} className="mt-4 flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] font-semibold text-white disabled:opacity-50">{busy ? "Starting audit…" : "Run AI visibility audit"}{!busy ? <ArrowIcon className="h-5 w-5" /> : null}</button>
    <div className="mt-5"><p className="font-mono text-[11px] uppercase tracking-[.2em] text-[#85848b]">Try an example</p><button type="button" onClick={()=>setUrl("https://books.toscrape.com/")} className="mt-2 rounded-full border bg-[#f8f7f4] px-3 py-2 text-xs text-[#5e5d66]">https://books.toscrape.com/</button></div>
  </form>;
}
