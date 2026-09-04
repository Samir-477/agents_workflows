"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ArrowIcon } from "@/components/icons";
import { createSchemaGeneration } from "@/lib/schema-api";

const examples = [
  "LocalBusiness schema for a bakery with two locations, with each shop's visible address and opening hours.",
  "Article schema for our engineering blog post, written by Maya Shah and published on 1 September 2026.",
  "Product schema for a handmade candle, £24, in stock, with those details visible on the product page.",
];

export function SchemaPromptForm() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSubmitting(true);
    try {
      const response = await createSchemaGeneration(prompt);
      router.push(`/agents/schema-markup/runs/${response.generation.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The schema request could not be started.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-[24px] border border-[#deddd9] bg-white p-6 shadow-[0_20px_60px_rgba(26,26,36,0.07)] sm:p-7">
      <label htmlFor="schema-prompt" className="sr-only">Describe the page and its visible facts</label>
      <textarea id="schema-prompt" required minLength={20} maxLength={20000} rows={3} value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="A dental clinic in Manchester with visible address, opening hours and booking details…" className="min-h-28 w-full resize-y rounded-2xl border border-[#d9d8d4] px-5 py-4 text-[17px] leading-7 outline-none transition placeholder:text-[#9c9ba3] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
      {error ? <p role="alert" className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
      <button type="submit" disabled={submitting || prompt.trim().length < 20} className="mt-4 flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] px-5 text-[16px] font-semibold text-white shadow-[0_9px_24px_rgba(255,87,56,0.18)] transition hover:bg-[#e9482b] disabled:cursor-not-allowed disabled:opacity-55">
        {submitting ? "Preparing your run…" : "Generate schema"}{!submitting ? <ArrowIcon className="h-5 w-5" /> : null}
      </button>
      <div className="mt-6"><p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#85848b]">Try an example</p>
        <div className="mt-3 space-y-2.5">{examples.map((example) => <button key={example} type="button" onClick={() => setPrompt(example)} className="block w-full truncate rounded-full border border-[#dfded9] bg-[#f8f7f4] px-4 py-2.5 text-left text-sm text-[#5e5d66] transition hover:border-[#bdb7ff] hover:bg-[#f3f1ff] hover:text-[#4b3fca]">{example}</button>)}</div>
      </div>
    </form>
  );
}
