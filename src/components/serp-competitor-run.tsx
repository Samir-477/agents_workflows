"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import {
  getSerpRun,
  processSerpRun,
  retrySerpRun,
  type PatternEvidence,
  type SerpRun,
} from "@/lib/serp-competitor-api";

function Progress({ run }: { run: SerpRun | null }) {
  return (
    <div className="mx-auto max-w-3xl rounded-[24px] border bg-white p-8">
      <p className="font-mono text-xs uppercase tracking-[.18em] text-[#5549dd]">SERP research in progress</p>
      <h1 className="mt-3 text-3xl font-semibold capitalize">{run?.stage.replaceAll("_", " ") || "Loading"}</h1>
      <div className="mt-6 h-2 rounded-full bg-[#efeee9]">
        <div className="h-full rounded-full bg-gradient-to-r from-[#5a4df4] to-[#ff5738]" style={{ width: `${Math.max(2, run?.progress || 0)}%` }} />
      </div>
      <p className="mt-4 text-sm text-[#777680]">{run?.request.target_keyword}</p>
    </div>
  );
}

function PatternList({ items, empty }: { items: PatternEvidence[]; empty: string }) {
  if (!items.length) return <p className="mt-3 text-sm text-[#686871]">{empty}</p>;
  return (
    <ul className="mt-4 space-y-3">
      {items.map((item) => (
        <li key={item.label} className="rounded-xl bg-[#faf9f6] p-3">
          <div><strong>{item.label}</strong><span className="ml-2 text-sm text-[#777680]">{item.count} result(s)</span></div>
          <details className="mt-2 text-xs text-[#686871]">
            <summary className="cursor-pointer font-semibold text-[#5549dd]">View supporting sources</summary>
            <ul className="mt-2 space-y-1">
              {item.source_urls.map((url) => <li key={url}><a href={url} target="_blank" rel="noreferrer" className="break-all underline underline-offset-2">{url}</a></li>)}
            </ul>
          </details>
        </li>
      ))}
    </ul>
  );
}

function Results({ run }: { run: SerpRun }) {
  const result = run.result!;
  const [copyState, setCopyState] = useState("Copy JSON");

  async function copyJson() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      setCopyState("Copied");
    } catch {
      setCopyState("Copy failed");
    }
  }

  function downloadJson() {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = `serp-research-${run.id}.json`;
    anchor.click();
    URL.revokeObjectURL(href);
  }

  return (
    <div>
      <header className="flex flex-wrap justify-between gap-5 border-b pb-7">
        <div>
          <p className="font-mono text-xs uppercase tracking-[.2em] text-[#4b3fca]">Research captured {new Date(result.observed_at).toLocaleString()}</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-.045em]">{result.target_keyword}</h1>
          <p className="mt-3 text-[#686871]"><strong className="capitalize">{result.search_intent}</strong> · {result.intent_rationale}</p>
          {result.snapshot_source_run_id ? <p className="mt-2 text-xs text-[#777680]">Reused a fresh saved snapshot from run {result.snapshot_source_run_id}.</p> : null}
        </div>
        <div className="flex h-fit flex-wrap gap-2">
          <button type="button" onClick={copyJson} className="rounded-xl border border-[#d9d6cf] bg-white px-4 py-3 text-sm font-semibold">{copyState}</button>
          <button type="button" onClick={downloadJson} className="rounded-xl border border-[#d9d6cf] bg-white px-4 py-3 text-sm font-semibold">Download JSON</button>
          <Link href="/agents/serp-competitor" className="rounded-xl bg-[#171820] px-4 py-3 text-sm font-semibold text-white">Research another keyword</Link>
        </div>
      </header>

      <section className="mt-7 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border bg-white p-5"><strong className="text-3xl">{result.organic_results.length}</strong><p className="mt-1 text-sm text-[#777680]">organic results</p></div>
        <div className="rounded-2xl border bg-white p-5"><strong className="text-3xl">{result.competitors.filter((item) => item.fetched).length}</strong><p className="mt-1 text-sm text-[#777680]">pages inspected</p></div>
        <div className="rounded-2xl border bg-white p-5"><strong className="text-3xl">{result.median_word_count ?? "—"}</strong><p className="mt-1 text-sm text-[#777680]">median observed words</p></div>
      </section>

      {result.warnings.length ? <section className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-5"><h2 className="font-semibold text-amber-900">Coverage notes</h2><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">{result.warnings.map((item) => <li key={item}>{item}</li>)}</ul></section> : null}

      {result.answer_box ? <section className="mt-6 rounded-2xl border border-[#d9d5ff] bg-[#f5f3ff] p-5"><p className="font-mono text-xs uppercase tracking-wide text-[#5549dd]">Observed answer box</p>{result.answer_box.title ? <h2 className="mt-2 text-xl font-semibold">{result.answer_box.title}</h2> : null}<p className="mt-2 text-sm leading-6 text-[#4e4d58]">{result.answer_box.answer}</p>{result.answer_box.source_url ? <a href={result.answer_box.source_url} target="_blank" rel="noreferrer" className="mt-3 block break-all text-xs text-[#5549dd] underline">{result.answer_box.source_url}</a> : null}</section> : null}

      <section className="mt-10">
        <h2 className="text-3xl font-semibold">Current organic results</h2>
        <div className="mt-5 overflow-x-auto rounded-2xl border bg-white">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b bg-[#f7f6f3] text-xs uppercase tracking-wide text-[#777680]"><tr><th className="p-4">Rank</th><th className="p-4">Result</th><th className="p-4">Observed snippet</th></tr></thead>
            <tbody className="divide-y">{result.organic_results.map((item) => <tr key={`${item.position}-${item.url}`}><td className="p-4 align-top font-mono text-lg text-[#5549dd]">{item.position}</td><td className="p-4 align-top"><a href={item.url} target="_blank" rel="noreferrer" className="font-semibold underline decoration-[#d7d2ff] underline-offset-4">{item.title}</a><p className="mt-2 break-all text-xs text-[#85848b]">{item.url}</p></td><td className="max-w-xl p-4 align-top leading-6 text-[#686871]">{item.snippet || "No snippet returned."}</td></tr>)}</tbody>
          </table>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="text-3xl font-semibold">Inspected competitor pages</h2>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">{result.competitors.map((page) => <article key={page.url} className="rounded-2xl border bg-white p-5"><div className="flex justify-between gap-3"><h3 className="font-semibold">#{page.position} {page.title}</h3><span className={`h-fit rounded-full px-2 py-1 text-[10px] font-semibold uppercase ${page.fetched ? "bg-green-50 text-green-700" : "bg-stone-100 text-stone-600"}`}>{page.fetched ? "inspected" : "unavailable"}</span></div><a href={page.url} target="_blank" rel="noreferrer" className="mt-2 block break-all text-xs text-[#5549dd] underline">{page.url}</a>{page.fetched ? <><p className="mt-4 text-sm"><strong>{page.word_count}</strong> observed words · {page.schema_types.join(", ") || "no schema observed"}</p><details className="mt-3"><summary className="cursor-pointer text-sm font-semibold text-[#5549dd]">Observed headings ({page.headings.length})</summary><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[#686871]">{page.headings.map((heading, index) => <li key={`${index}-${heading}`}>{heading}</li>)}</ul></details></> : <p className="mt-4 text-sm text-[#686871]">{page.fetch_note}</p>}</article>)}</div>
      </section>

      <section className="mt-10 grid gap-5 lg:grid-cols-3">
        <article className="rounded-2xl border bg-white p-6"><h2 className="text-xl font-semibold">Recurring topics</h2><p className="mt-2 text-xs leading-5 text-[#777680]">Interpretation based on repeated words in result titles and inspected headings.</p><PatternList items={result.topic_patterns} empty="No recurring topic was established." /></article>
        <article className="rounded-2xl border bg-white p-6"><h2 className="text-xl font-semibold">Recurring headings</h2><PatternList items={result.common_headings} empty="No recurring inspected heading was established." /></article>
        <article className="rounded-2xl border bg-white p-6"><h2 className="text-xl font-semibold">Observed schema</h2><PatternList items={result.common_schema} empty="No recurring schema type was observed." /></article>
      </section>

      <section className="mt-8 grid gap-5 lg:grid-cols-2">
        <article className="rounded-2xl border bg-white p-6"><h2 className="text-xl font-semibold">People Also Ask</h2>{result.questions.length ? <ul className="mt-4 list-disc space-y-3 pl-5">{result.questions.map((item) => <li key={item.question}>{item.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer" className="underline underline-offset-2">{item.question}</a> : item.question}</li>)}</ul> : <p className="mt-3 text-sm text-[#686871]">No People Also Ask questions were returned.</p>}</article>
        <article className="rounded-2xl border bg-white p-6"><h2 className="text-xl font-semibold">Related searches</h2>{result.related_searches.length ? <ul className="mt-4 list-disc space-y-3 pl-5">{result.related_searches.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-3 text-sm text-[#686871]">No related searches were returned.</p>}</article>
      </section>

      <section className="mt-8 rounded-2xl border bg-[#f7f6f3] p-6"><h2 className="text-xl font-semibold">Recommended use</h2><ol className="mt-4 list-decimal space-y-2 pl-5 text-sm leading-6 text-[#686871]">{result.recommendations.map((item) => <li key={item}>{item}</li>)}</ol></section>
      <section className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-5"><h2 className="font-semibold text-amber-900">Method limits</h2><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">{result.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>
    </div>
  );
}

export function SerpCompetitorRun({ runId }: { runId: string }) {
  const [run, setRun] = useState<SerpRun | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next = await getSerpRun(runId);
        if (cancelled) return;
        setRun(next);
        if (next.status === "queued" && !started.current) {
          started.current = true;
          void processSerpRun(runId).catch((caught) => {
            started.current = false;
            setError(caught instanceof Error ? caught.message : "Could not start research.");
          });
        }
        if (next.status === "queued" || next.status === "running") timer = setTimeout(poll, 1200);
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "Could not load research.");
      }
    }
    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [runId, version]);

  if (error && !run) return <p role="alert" className="rounded-xl bg-red-50 p-5 text-red-700">{error}</p>;
  if (!run || run.status === "queued" || run.status === "running") return <Progress run={run} />;
  if (run.status === "failed") return <div className="mx-auto max-w-2xl rounded-2xl border bg-white p-8 text-center"><h1 className="text-3xl font-semibold">Research failed</h1><p className="mt-3 text-red-700">{run.error}</p><button disabled={busy} onClick={async () => { setBusy(true); try { await retrySerpRun(runId); started.current = false; setVersion((value) => value + 1); } finally { setBusy(false); } }} className="mt-5 rounded-xl bg-[#ff5738] px-5 py-3 font-semibold text-white disabled:opacity-50">{busy ? "Retrying…" : "Retry research"}</button></div>;
  return run.result ? <Results run={run} /> : <Progress run={run} />;
}
