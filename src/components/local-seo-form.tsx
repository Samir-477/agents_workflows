"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ArrowIcon } from "@/components/icons";
import { localApi, type LocalRun } from "@/lib/local-seo-api";

const examples = [
  "Emergency plumber serving Austin and Travis County from one base. Services: plumbing. Hours: 24/7. Licensed and insured. No public office in either area. Leave missing business name, phone and local job evidence for me to add.",
  "Family dental clinic with physical offices in Aurora, Lakewood and Arvada. Services: family dentistry. Draft one page per office. Ask me to confirm each address, phone, opening hours, dentist details and local proof.",
  "Landscaping company serving Naperville. Services: landscaping. Focus on commercial contracts. Leave business name, phone, coverage boundaries and two local client references for confirmation.",
];

export function LocalSEOForm() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [urls, setUrls] = useState("");
  const [maps, setMaps] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const run = await localApi<LocalRun>("", "POST", {
        prompt,
        existing_urls: urls.split(/\r?\n/).map((line) => line.trim()).filter(Boolean),
        lookup_maps: maps,
      });
      router.push(`/agents/local-seo/runs/${run.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The run could not be started.");
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="rounded-[24px] border border-[#deddd9] bg-white p-6 shadow-[0_20px_60px_rgba(26,26,36,0.07)] sm:p-7"
    >
      <label htmlFor="local-brief" className="sr-only">
        Your business, services and areas
      </label>
      <textarea
        id="local-brief"
        required
        minLength={20}
        maxLength={12000}
        rows={6}
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        placeholder="Business name, services, real locations or coverage, phone, hours and local evidence…"
        className="min-h-40 w-full resize-y rounded-2xl border border-[#d9d8d4] px-5 py-4 text-[16px] leading-7 outline-none transition placeholder:text-[#9c9ba3] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10"
      />

      <details className="group mt-4 rounded-xl border border-[#e4e2de] bg-[#fcfbf9]">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3 text-sm font-semibold text-[#393a43]">
          <span>Optional links and listing references</span>
          <span className="text-xs font-normal text-[#777680] group-open:hidden">Add details +</span>
          <span className="hidden text-xs font-normal text-[#777680] group-open:inline">Close -</span>
        </summary>
        <div className="space-y-4 border-t border-[#e8e6e2] p-4">
          <div>
            <label htmlFor="local-urls" className="text-xs font-semibold text-[#34343d]">
              Existing page URLs <span className="font-normal text-[#85848b]">- one per line</span>
            </label>
            <textarea
              id="local-urls"
              rows={3}
              value={urls}
              onChange={(event) => setUrls(event.target.value)}
              placeholder="https://your-site.com/service-areas"
              className="mt-2 min-h-20 w-full resize-y rounded-xl border border-[#d9d8d4] bg-white px-4 py-3 text-sm leading-5 outline-none placeholder:text-[#a1a0a7] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10"
            />
          </div>
          <label className="flex items-start gap-2.5 text-sm leading-6 text-[#44454e]">
            <input
              type="checkbox"
              checked={maps}
              onChange={(event) => setMaps(event.target.checked)}
              className="mt-0.5 h-4 w-4 accent-[#5a4df4]"
            />
            Check OpenStreetMap for a public listing that matches a named physical branch. Keyless open-data lookup; references only.
          </label>
        </div>
      </details>

      {error ? (
        <p role="alert" className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={submitting || prompt.trim().length < 20}
        className="mt-4 flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] px-5 text-[16px] font-semibold text-white shadow-[0_9px_24px_rgba(255,87,56,0.18)] transition hover:bg-[#e9482b] disabled:cursor-not-allowed disabled:opacity-55"
      >
        {submitting ? "Creating run…" : "Generate my local pages"}
        {!submitting ? <ArrowIcon className="h-5 w-5" /> : null}
      </button>

      <div className="mt-6">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#85848b]">
          Try an example
        </p>
        <div className="mt-3 space-y-2.5">
          {examples.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setPrompt(example)}
              className="block w-full truncate rounded-full border border-[#dfded9] bg-[#f8f7f4] px-4 py-2.5 text-left text-sm text-[#5e5d66] transition hover:border-[#bdb7ff] hover:bg-[#f3f1ff] hover:text-[#4b3fca]"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </form>
  );
}
