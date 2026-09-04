"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ArrowIcon } from "@/components/icons";
import { createKeywordClusterGeneration } from "@/lib/keyword-cluster-api";

const examples = [
  "crm for freelancers\nbest crm for freelancers\nfreelance client management software\ncrm pricing\nhow to choose a crm\ncrm for consultants",
  "accounting software for landlords, 1600\nbest landlord accounting software, 900\nhow to reconcile rent payments, 500\nquickbooks alternatives for landlords, 350\nrental property bookkeeping, 1200",
  "wedding photographer prices\nhow much does a wedding photographer cost\nwedding photography packages\nbest wedding photographer\nwedding photography pricing guide",
];

export function KeywordClusterForm() {
  const router = useRouter();
  const [keywords, setKeywords] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const lineCount = useMemo(() => keywords.split(/\r?\n/).filter((line) => line.trim()).length, [keywords]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await createKeywordClusterGeneration(keywords);
      router.push(`/agents/keyword-cluster/runs/${response.generation.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The clustering run could not be started.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-[24px] border border-[#deddd9] bg-white p-6 shadow-[0_20px_60px_rgba(26,26,36,0.07)] sm:p-7">
      <div className="flex items-center justify-between gap-3">
        <label htmlFor="keyword-list" className="text-sm font-semibold text-[#25262e]">Keyword list</label>
        <span className={`font-mono text-[11px] ${lineCount > 500 ? "text-red-600" : "text-[#85848b]"}`}>{lineCount}/500 rows</span>
      </div>
      <textarea
        id="keyword-list"
        required
        minLength={3}
        rows={8}
        value={keywords}
        onChange={(event) => setKeywords(event.target.value)}
        placeholder={"One keyword per line\ncrm for freelancers\nbest crm for freelancers\ncrm pricing, 1200"}
        className="mt-3 min-h-52 w-full resize-y rounded-2xl border border-[#d9d8d4] px-5 py-4 text-[16px] leading-7 outline-none transition placeholder:text-[#9c9ba3] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10"
      />
      <p className="mt-2 text-xs leading-5 text-[#7c7b84]">One keyword per line. Add an optional volume after a comma, tab or semicolon.</p>
      {error ? <p role="alert" className="mt-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
      <button type="submit" disabled={submitting || lineCount < 3 || lineCount > 500} className="mt-4 flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] px-5 text-[16px] font-semibold text-white shadow-[0_9px_24px_rgba(255,87,56,0.18)] transition hover:bg-[#e9482b] disabled:cursor-not-allowed disabled:opacity-55">
        {submitting ? "Preparing your plan…" : "Cluster my keywords"}{!submitting ? <ArrowIcon className="h-5 w-5" /> : null}
      </button>
      <div className="mt-6">
        <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#85848b]">Try an example</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {examples.map((example, index) => <button key={example} type="button" onClick={() => setKeywords(example)} className="rounded-full border border-[#dfded9] bg-[#f8f7f4] px-4 py-2 text-left text-xs text-[#5e5d66] transition hover:border-[#bdb7ff] hover:bg-[#f3f1ff] hover:text-[#4b3fca]">{["Freelancer CRM", "Landlord accounting", "Photography pricing"][index]}</button>)}
        </div>
      </div>
    </form>
  );
}
