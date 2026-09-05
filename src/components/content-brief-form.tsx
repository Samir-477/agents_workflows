"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ArrowIcon } from "@/components/icons";
import { createContentBrief } from "@/lib/content-brief-api";

const examples = [
  ["remote team onboarding checklist", "HR managers at 20–100 person startups"],
  ["email marketing for dentists", "Dental practice managers new to email marketing"],
  ["commercial lease guide", "First-time independent retail tenants"],
];

function lines(value: string) { return value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean); }

export function ContentBriefForm() {
  const router = useRouter();
  const [keyword, setKeyword] = useState("");
  const [audience, setAudience] = useState("");
  const [secondary, setSecondary] = useState("");
  const [angle, setAngle] = useState("");
  const [goal, setGoal] = useState("");
  const [product, setProduct] = useState("");
  const [urls, setUrls] = useState("");
  const [notes, setNotes] = useState("");
  const [mode, setMode] = useState<"new" | "rewrite">("new");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSubmitting(true);
    try {
      const response = await createContentBrief({
        target_keyword: keyword, audience, secondary_keywords: lines(secondary),
        angle: angle || undefined, business_goal: goal || undefined,
        product_context: product || undefined, existing_urls: lines(urls),
        source_notes: notes || undefined, content_mode: mode,
      });
      router.push(`/agents/content-brief/runs/${response.generation.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The brief could not be started.");
      setSubmitting(false);
    }
  }

  return <form onSubmit={submit} className="rounded-[24px] border border-[#deddd9] bg-white p-6 shadow-[0_20px_60px_rgba(26,26,36,0.07)] sm:p-7">
    <label htmlFor="brief-keyword" className="text-sm font-semibold">Target keyword</label>
    <input id="brief-keyword" required minLength={2} maxLength={300} value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="remote team onboarding checklist" className="mt-2 h-13 w-full rounded-xl border border-[#d9d8d4] px-4 outline-none focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
    <label htmlFor="brief-audience" className="mt-4 block text-sm font-semibold">Audience</label>
    <input id="brief-audience" required minLength={2} maxLength={800} value={audience} onChange={(event) => setAudience(event.target.value)} placeholder="HR managers at growing startups" className="mt-2 h-13 w-full rounded-xl border border-[#d9d8d4] px-4 outline-none focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
    <details className="mt-4 rounded-xl border border-[#e4e2dd] bg-[#faf9f7] p-4"><summary className="cursor-pointer text-sm font-semibold">Add angle, goals, pages, or source notes</summary><div className="mt-4 grid gap-4">
      <label className="text-xs font-semibold">Content mode<select value={mode} onChange={(event) => setMode(event.target.value as "new" | "rewrite")} className="mt-1.5 h-11 w-full rounded-lg border border-[#d9d8d4] bg-white px-3 font-normal"><option value="new">New article</option><option value="rewrite">Rewrite existing article</option></select></label>
      <label className="text-xs font-semibold">Secondary keywords, one per line<textarea value={secondary} onChange={(event) => setSecondary(event.target.value)} rows={3} className="mt-1.5 w-full rounded-lg border border-[#d9d8d4] bg-white p-3 font-normal" /></label>
      <label className="text-xs font-semibold">Angle or editorial point of view<textarea value={angle} onChange={(event) => setAngle(event.target.value)} rows={2} className="mt-1.5 w-full rounded-lg border border-[#d9d8d4] bg-white p-3 font-normal" /></label>
      <label className="text-xs font-semibold">Business goal<textarea value={goal} onChange={(event) => setGoal(event.target.value)} rows={2} placeholder="Lead readers toward a template download" className="mt-1.5 w-full rounded-lg border border-[#d9d8d4] bg-white p-3 font-normal" /></label>
      <label className="text-xs font-semibold">Product or service context<textarea value={product} onChange={(event) => setProduct(event.target.value)} rows={2} className="mt-1.5 w-full rounded-lg border border-[#d9d8d4] bg-white p-3 font-normal" /></label>
      <label className="text-xs font-semibold">Existing page URLs, one per line<textarea value={urls} onChange={(event) => setUrls(event.target.value)} rows={3} placeholder="https://example.com/hr-guide" className="mt-1.5 w-full rounded-lg border border-[#d9d8d4] bg-white p-3 font-normal" /></label>
      <label className="text-xs font-semibold">Trusted source notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} placeholder="Facts, constraints, research excerpts, or claims the writer may use" className="mt-1.5 w-full rounded-lg border border-[#d9d8d4] bg-white p-3 font-normal" /></label>
    </div></details>
    {error ? <p role="alert" className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
    <button type="submit" disabled={submitting || keyword.trim().length < 2 || audience.trim().length < 2} className="mt-4 flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] px-5 font-semibold text-white shadow-[0_9px_24px_rgba(255,87,56,0.18)] hover:bg-[#e9482b] disabled:opacity-55">{submitting ? "Preparing your run…" : "Brief my article"}{!submitting ? <ArrowIcon className="h-5 w-5" /> : null}</button>
    <div className="mt-5"><p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#85848b]">Try an example</p><div className="mt-3 space-y-2">{examples.map(([itemKeyword, itemAudience]) => <button key={itemKeyword} type="button" onClick={() => { setKeyword(itemKeyword); setAudience(itemAudience); }} className="block w-full truncate rounded-full border border-[#dfded9] bg-[#f8f7f4] px-4 py-2 text-left text-sm text-[#5e5d66] hover:border-[#bdb7ff] hover:bg-[#f3f1ff]">{itemKeyword}</button>)}</div></div>
  </form>;
}
