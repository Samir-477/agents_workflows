"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ArrowIcon } from "@/components/icons";
import { createAudit } from "@/lib/api";

const examples = [
  "https://books.toscrape.com/",
  "https://example.com/",
  "https://quotes.toscrape.com/",
];

export function AuditForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);
    const importantUrls = String(form.get("important_urls") ?? "")
      .split(/[\n,]/)
      .map((value) => value.trim())
      .filter(Boolean);

    try {
      const response = await createAudit({
        url,
        business_description: String(form.get("business_description") ?? "") || undefined,
        audit_reason: String(form.get("audit_reason") ?? "") || undefined,
        important_urls: importantUrls,
        crawl_limit: Number(form.get("crawl_limit") ?? 20),
      });
      router.push(`/agents/seo-audit/runs/${response.audit.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The audit could not be submitted. Check the backend connection.");
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-[22px] border border-[#deddd9] bg-white p-6 shadow-[0_20px_60px_rgba(26,26,36,0.07)]">
      <label htmlFor="url" className="sr-only">Website URL</label>
      <input
        id="url"
        name="url"
        type="url"
        required
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        placeholder="https://your-website.com"
        className="h-14 w-full rounded-xl border border-[#d9d8d4] px-4 text-[16px] outline-none transition placeholder:text-[#9c9ba3] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10"
      />

      <details className="group mt-4 rounded-xl border border-[#e4e2de] bg-[#fcfbf9]">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3 text-sm font-semibold text-[#393a43]">
          <span>Optional audit context</span>
          <span className="text-xs font-normal text-[#777680] group-open:hidden">Add details +</span>
          <span className="hidden text-xs font-normal text-[#777680] group-open:inline">Close -</span>
        </summary>
        <div className="space-y-4 border-t border-[#e8e6e2] p-4">
          <div>
            <label htmlFor="business_description" className="text-xs font-semibold text-[#34343d]">What does the business do?</label>
            <textarea id="business_description" name="business_description" rows={2} placeholder="Online store selling handmade furniture…" className="mt-2 min-h-20 w-full resize-y rounded-xl border border-[#d9d8d4] bg-white px-4 py-3 text-sm leading-5 outline-none placeholder:text-[#a1a0a7] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
          </div>
          <div>
            <label htmlFor="important_urls" className="text-xs font-semibold text-[#34343d]">Important page URLs <span className="font-normal text-[#85848b]">- one per line</span></label>
            <textarea id="important_urls" name="important_urls" rows={2} placeholder="https://your-website.com/pricing" className="mt-2 min-h-20 w-full resize-y rounded-xl border border-[#d9d8d4] bg-white px-4 py-3 text-sm leading-5 outline-none placeholder:text-[#a1a0a7] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
          </div>
          <div className="grid gap-4 sm:grid-cols-[1fr_110px]">
            <div>
              <label htmlFor="audit_reason" className="text-xs font-semibold text-[#34343d]">Why are you auditing?</label>
              <input id="audit_reason" name="audit_reason" type="text" placeholder="Traffic dropped after a redesign" className="mt-2 h-11 w-full rounded-xl border border-[#d9d8d4] bg-white px-4 text-sm outline-none placeholder:text-[#a1a0a7] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
            </div>
            <div>
              <label htmlFor="crawl_limit" className="text-xs font-semibold text-[#34343d]">Page limit</label>
              <input id="crawl_limit" name="crawl_limit" type="number" min={1} max={100} defaultValue={20} required className="mt-2 h-11 w-full rounded-xl border border-[#d9d8d4] bg-white px-3 text-sm outline-none focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
            </div>
          </div>
        </div>
      </details>

      {error ? <p role="alert" className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

      <button type="submit" disabled={isSubmitting} className="mt-4 flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] px-5 font-semibold text-white shadow-[0_9px_24px_rgba(255,87,56,0.18)] transition hover:bg-[#e9482b] disabled:cursor-wait disabled:opacity-70">
        {isSubmitting ? "Starting audit…" : "Start website audit"}
        {!isSubmitting ? <ArrowIcon className="h-5 w-5" /> : null}
      </button>

      <div className="mt-5">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-[#85848b]">Try an example</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {examples.map((example) => (
            <button key={example} type="button" onClick={() => setUrl(example)} className="max-w-full truncate rounded-full border border-[#dfded9] bg-[#f8f7f4] px-3 py-2 text-left text-xs text-[#5e5d66] transition hover:border-[#bdb7ff] hover:bg-[#f3f1ff] hover:text-[#4b3fca]">
              {example}
            </button>
          ))}
        </div>
      </div>
    </form>
  );
}
