"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ArrowIcon, PlusIcon } from "@/components/icons";
import { createInternalLinkAudit } from "@/lib/internal-linking-api";

const examples = ["https://books.toscrape.com/", "https://example.com/", "https://quotes.toscrape.com/"];

export function InternalLinkingForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [business, setBusiness] = useState("");
  const [important, setImportant] = useState("");
  const [goal, setGoal] = useState("");
  const [limit, setLimit] = useState(20);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSubmitting(true);
    try {
      const response = await createInternalLinkAudit({
        url, business_description: business || undefined, audit_goal: goal || undefined,
        important_urls: important.split(/\r?\n/).map((item) => item.trim()).filter(Boolean), crawl_limit: limit,
      });
      router.push(`/agents/internal-linking/runs/${response.audit.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The audit could not be started.");
      setSubmitting(false);
    }
  }

  return <form onSubmit={submit} className="rounded-[24px] border border-[#deddd9] bg-white p-6 shadow-[0_20px_60px_rgba(26,26,36,0.07)] sm:p-7">
    <label htmlFor="link-site-url" className="text-sm font-semibold">Website URL</label>
    <input id="link-site-url" type="url" required value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://your-website.com" className="mt-3 h-16 w-full rounded-2xl border border-[#d9d8d4] px-5 text-[16px] outline-none placeholder:text-[#9c9ba3] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
    <details className="group mt-4 rounded-2xl border border-[#dfdedb]">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 font-semibold"><span>Optional audit context</span><span className="inline-flex items-center gap-1 text-sm font-normal text-[#777680]"><span className="group-open:hidden">Add details</span><span className="hidden group-open:inline">Hide details</span><PlusIcon className="h-4 w-4 transition group-open:rotate-45" /></span></summary>
      <div className="space-y-4 border-t border-[#eceae6] p-5">
        <label className="block text-sm font-semibold">What does the business do?<textarea value={business} onChange={(event) => setBusiness(event.target.value)} rows={3} className="mt-2 w-full rounded-xl border border-[#d9d8d4] p-3 font-normal outline-none focus:border-[#5a4df4]" /></label>
        <label className="block text-sm font-semibold">Important page URLs <span className="font-normal text-[#85848b]">— one per line</span><textarea value={important} onChange={(event) => setImportant(event.target.value)} rows={3} className="mt-2 w-full rounded-xl border border-[#d9d8d4] p-3 font-normal outline-none focus:border-[#5a4df4]" /></label>
        <div className="grid gap-4 sm:grid-cols-[1fr_110px]"><label className="block text-sm font-semibold">Why are you auditing?<input value={goal} onChange={(event) => setGoal(event.target.value)} className="mt-2 h-12 w-full rounded-xl border border-[#d9d8d4] px-3 font-normal outline-none focus:border-[#5a4df4]" /></label><label className="block text-sm font-semibold">Page limit<input type="number" min={2} max={100} value={limit} onChange={(event) => setLimit(Number(event.target.value))} className="mt-2 h-12 w-full rounded-xl border border-[#d9d8d4] px-3 font-normal outline-none focus:border-[#5a4df4]" /></label></div>
      </div>
    </details>
    {error ? <p role="alert" className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
    <button type="submit" disabled={submitting} className="mt-4 flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] px-5 font-semibold text-white shadow-[0_9px_24px_rgba(255,87,56,0.18)] hover:bg-[#e9482b] disabled:opacity-55">{submitting ? "Starting link audit…" : "Audit my links"}{!submitting ? <ArrowIcon className="h-5 w-5" /> : null}</button>
    <div className="mt-6"><p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#85848b]">Try an example</p><div className="mt-3 flex flex-wrap gap-2">{examples.map((example) => <button key={example} type="button" onClick={() => setUrl(example)} className="rounded-full border border-[#dfded9] bg-[#f8f7f4] px-3 py-2 text-xs text-[#5e5d66] hover:border-[#bdb7ff] hover:bg-[#f3f1ff]">{example}</button>)}</div></div>
  </form>;
}
