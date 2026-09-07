"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ArrowIcon } from "@/components/icons";
import { createSerpRun, getSerperStatus } from "@/lib/serp-competitor-api";

export function SerpCompetitorForm() {
  const router = useRouter();
  const [keyword, setKeyword] = useState("");
  const [country, setCountry] = useState("in");
  const [language, setLanguage] = useState("en");
  const [inspect, setInspect] = useState(5);
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getSerperStatus()
      .then((status) => {
        if (active) setConfigured(status.configured);
      })
      .catch(() => {
        if (active) setConfigured(null);
      });
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const run = await createSerpRun({
        target_keyword: keyword,
        country,
        language,
        result_limit: 10,
        inspect_limit: inspect,
      });
      router.push(`/agents/serp-competitor/runs/${run.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The analysis could not start.");
      setBusy(false);
    }
  }

  const statusLabel = configured === true
    ? "Serper connected"
    : configured === false
      ? "Serper setup required"
      : "Provider status unavailable";

  return (
    <form onSubmit={submit} className="rounded-[24px] border border-[#deddd9] bg-white p-6 shadow-[0_20px_60px_rgba(26,26,36,.07)] sm:p-7">
      <div className="flex items-center justify-between gap-4">
        <label htmlFor="serp-keyword" className="text-sm font-semibold">Target keyword</label>
        <span className="inline-flex items-center gap-2 text-xs text-[#777680]">
          <span aria-hidden="true" className={`h-2 w-2 rounded-full ${configured === true ? "bg-[#2d8b62]" : configured === false ? "bg-[#c9422d]" : "bg-[#aaa8a1]"}`} />
          {statusLabel}
        </span>
      </div>
      <input id="serp-keyword" required minLength={2} maxLength={300} value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="best CRM software for small business" className="mt-3 h-16 w-full rounded-2xl border border-[#d9d8d4] px-5 outline-none focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
      <div className="mt-4 grid grid-cols-3 gap-3">
        <label className="text-xs font-semibold">Country<input required aria-label="Two-letter country code" pattern="[A-Za-z]{2}" maxLength={2} value={country} onChange={(event) => setCountry(event.target.value)} className="mt-2 h-11 w-full rounded-xl border px-3 font-normal uppercase" /></label>
        <label className="text-xs font-semibold">Language<input required aria-label="Two-letter language code" pattern="[A-Za-z]{2}" maxLength={2} value={language} onChange={(event) => setLanguage(event.target.value)} className="mt-2 h-11 w-full rounded-xl border px-3 font-normal" /></label>
        <label className="text-xs font-semibold">Inspect pages<input type="number" min={0} max={10} value={inspect} onChange={(event) => setInspect(Number(event.target.value))} className="mt-2 h-11 w-full rounded-xl border px-3 font-normal" /></label>
      </div>
      <p className="mt-4 text-xs leading-5 text-[#777680]">The result preserves a timestamped Google SERP sample. Optional questions and related searches remain empty when the provider returns none.</p>
      {error ? <p role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      <button disabled={busy || configured === false} className="mt-5 flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">
        {busy ? "Starting research…" : "Analyze the SERP"}
        {!busy ? <ArrowIcon className="h-5 w-5" /> : null}
      </button>
    </form>
  );
}
