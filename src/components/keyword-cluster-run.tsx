"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { CheckIcon } from "@/components/icons";
import {
  getKeywordClusterGeneration,
  getKeywordClusterResult,
  processKeywordClusterGeneration,
  retryKeywordClusterGeneration,
  type KeywordClusterItem,
  type KeywordClusterResponse,
  type KeywordClusterResult,
  type SearchIntent,
} from "@/lib/keyword-cluster-api";

const stages = ["queued", "parsing", "clustering", "consolidating", "planning", "validating", "complete"];
const labels: Record<string, string> = {
  queued: "Queued", parsing: "Cleaning the keyword list", clustering: "Finding semantic groups",
  consolidating: "Building one consistent architecture", planning: "Planning pages and internal links",
  validating: "Checking keyword coverage", complete: "Plan complete", failed: "Run failed",
};

function intentStyle(intent: SearchIntent): string {
  if (intent === "commercial") return "bg-[#fff1ed] text-[#b94731]";
  if (intent === "transactional") return "bg-[#fff6df] text-[#8a5a00]";
  if (intent === "informational") return "bg-[#eef6ff] text-[#376b9d]";
  if (intent === "navigational") return "bg-[#ecf8f1] text-[#24724f]";
  return "bg-[#f1efff] text-[#4b3fca]";
}

function Stat({ value, label }: { value: number; label: string }) {
  return <div className="rounded-2xl border border-[#e1dfda] bg-white px-5 py-4"><strong className="text-2xl tracking-[-0.03em]">{value}</strong><p className="mt-1 text-xs text-[#797881]">{label}</p></div>;
}

function Progress({ run }: { run: KeywordClusterResponse | null }) {
  const stage = run?.generation.stage ?? "queued";
  const stageIndex = stages.indexOf(stage);
  const progress = run?.generation.progress ?? 0;
  const rows = run?.generation.raw_keywords.split(/\r?\n/).filter((line) => line.trim()).length ?? 0;
  return <div className="mx-auto max-w-4xl overflow-hidden rounded-[26px] border border-[#dfdedb] bg-white shadow-[0_24px_70px_rgba(26,26,36,0.08)]">
    <header className="border-b border-[#e9e7e2] p-7 sm:p-10"><div className="flex items-start justify-between gap-5"><div><p className="font-mono text-xs uppercase tracking-[0.18em] text-[#5549dd]">Keyword planning in progress</p><h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">{labels[stage] ?? "Building your architecture"}</h1><p className="mt-3 text-sm text-[#74737c]">{rows ? `${rows} supplied rows` : "Loading your keyword list…"}</p></div><span className="rounded-full bg-[#f1efff] px-4 py-2 font-mono text-sm font-semibold text-[#4b3fca]">{progress}%</span></div><div className="mt-7 h-2 overflow-hidden rounded-full bg-[#efeee9]"><div className="h-full rounded-full bg-gradient-to-r from-[#5a4df4] to-[#ff5738] transition-[width] duration-500" style={{ width: `${Math.max(progress, 2)}%` }} /></div></header>
    <div className="grid gap-7 p-7 sm:p-10 md:grid-cols-[minmax(0,1fr)_280px]"><ol className="space-y-2">{stages.slice(1, -1).map((item, index) => { const actual = index + 1; const done = stageIndex > actual; const active = stageIndex === actual || (stage === "queued" && index === 0); return <li key={item} className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm ${active ? "bg-[#f1efff] font-semibold text-[#4034bd]" : "text-[#74737c]"}`}><span className={`flex h-7 w-7 items-center justify-center rounded-full border ${done ? "border-[#5a4df4] bg-[#5a4df4] text-white" : active ? "border-[#aaa2ff] bg-white text-[#5a4df4]" : "border-[#dddcd7] bg-[#f5f4f0]"}`}>{done ? <CheckIcon className="h-4 w-4" /> : actual}</span>{labels[item]}</li>; })}</ol><aside className="rounded-2xl bg-[#f7f6f3] p-5"><h2 className="font-semibold">What happens now?</h2><p className="mt-3 text-sm leading-6 text-[#686871]">The page refreshes automatically. The final pass verifies that every unique keyword still appears exactly once in the plan.</p><p className="mt-5 border-t border-[#e0ded8] pt-4 text-xs leading-5 text-[#85848b]">Large exports can take a little longer because batch groups are reconciled into one architecture.</p></aside></div>
  </div>;
}

function ClusterCard({ cluster }: { cluster: KeywordClusterItem }) {
  return <article className="rounded-[20px] border border-[#dfdedb] bg-white p-5 sm:p-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div className="flex flex-wrap gap-2"><span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold capitalize ${intentStyle(cluster.intent)}`}>{cluster.intent}</span><span className="rounded-full bg-[#f2f1ed] px-2.5 py-1 text-[11px] font-semibold capitalize text-[#66656d]">{cluster.role}</span><span className="rounded-full bg-[#f2f1ed] px-2.5 py-1 text-[11px] text-[#66656d]">{cluster.recommended_page_type}</span><span className="rounded-full border border-[#ddd9ff] bg-white px-2.5 py-1 text-[11px] font-semibold capitalize text-[#5549dd]">{cluster.confidence} confidence</span></div><span className="font-mono text-xs font-semibold text-[#4b3fca]">Priority {cluster.build_priority}</span></div>
    <h3 className="mt-4 text-xl font-semibold tracking-[-0.025em]">{cluster.suggested_title}</h3><p className="mt-1 font-mono text-xs text-[#85848b]">{cluster.suggested_slug}</p>
    <p className="mt-4 text-sm leading-6 text-[#686871]">{cluster.reasoning}</p><p className="mt-3 text-xs leading-5 text-[#85848b]"><strong className="text-[#62616a]">Priority basis:</strong> {cluster.priority_factors.join(" · ")}</p>
    <div className="mt-5 border-t border-[#eceae6] pt-4"><div className="flex flex-wrap items-center justify-between gap-2"><p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#777680]">{cluster.keywords.length} keyword{cluster.keywords.length === 1 ? "" : "s"}</p>{cluster.total_volume !== null ? <span className="text-xs text-[#777680]">Volume {cluster.total_volume.toLocaleString()}</span> : null}</div><div className="mt-3 flex flex-wrap gap-2">{cluster.keywords.map((item) => <span key={item.keyword} className={`rounded-lg px-2.5 py-1.5 text-xs ${item.keyword === cluster.primary_keyword ? "bg-[#eae7ff] font-semibold text-[#493dc0]" : "bg-[#f6f5f2] text-[#5e5d66]"}`}>{item.keyword}{item.volume !== null ? ` · ${item.volume.toLocaleString()}` : ""}</span>)}</div></div>
  </article>;
}

function Results({ result }: { result: KeywordClusterResult }) {
  const clusters = new Map(result.clusters.map((cluster) => [cluster.id, cluster]));
  return <div>
    <header className="flex flex-wrap items-start justify-between gap-5 border-b border-[#e3e1dc] pb-7"><div><p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#4b3fca]">Keyword plan complete</p><h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em] sm:text-[46px]">Your content architecture</h1><p className="mt-3 max-w-3xl leading-7 text-[#686871]">{result.strategy_summary}</p></div><Link href="/agents/keyword-cluster" className="rounded-xl bg-[#171820] px-4 py-3 text-sm font-semibold text-white hover:bg-[#30313a]">Cluster another list</Link></header>
    <section className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><Stat value={result.unique_keyword_count} label="unique keywords" /><Stat value={result.clusters.length} label="recommended pages" /><Stat value={result.pillars.length} label="topic pillars" /><Stat value={result.internal_links.length} label="planned links" /></section>
    {(result.warnings.length || result.assumptions.length) ? <div className="mt-6 grid gap-4 md:grid-cols-2">{result.warnings.length ? <div className="rounded-2xl border border-[#f2d3a7] bg-[#fff8eb] p-5"><h2 className="text-sm font-semibold text-[#80501b]">Input notes</h2><ul className="mt-2 space-y-1 text-sm leading-6 text-[#80501b]">{result.warnings.map((item) => <li key={item}>• {item}</li>)}</ul></div> : null}{result.assumptions.length ? <div className="rounded-2xl border border-[#d7d2ff] bg-[#f4f2ff] p-5"><h2 className="text-sm font-semibold text-[#493dc0]">Assumptions</h2><ul className="mt-2 space-y-1 text-sm leading-6 text-[#5b54a1]">{result.assumptions.map((item) => <li key={item}>• {item}</li>)}</ul></div> : null}</div> : null}
    <section className="mt-12"><p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-[#d94221]">Recommended sitemap</p><h2 className="mt-2 text-3xl font-semibold tracking-[-0.035em]">Topic hubs and supporting pages</h2><div className="mt-7 space-y-9">{result.pillars.map((pillar, index) => <section key={pillar.name}><div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><div className="flex flex-wrap items-center gap-2"><p className="font-mono text-xs text-[#85848b]">Topic hub {String(index + 1).padStart(2, "0")}</p><span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] ${pillar.recommendation_status === "established" ? "bg-[#ecf8f1] text-[#24724f]" : "bg-[#fff6df] text-[#8a5a00]"}`}>{pillar.recommendation_status}</span></div><h3 className="mt-1 text-2xl font-semibold">{pillar.name}</h3><p className="mt-1 text-sm text-[#777680]">{pillar.cluster_ids.length} planned page{pillar.cluster_ids.length === 1 ? "" : "s"} · build priority {pillar.build_priority}</p><p className="mt-2 max-w-3xl text-xs leading-5 text-[#85848b]">{pillar.rationale}</p></div><span className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${intentStyle(pillar.intent)}`}>{pillar.intent}</span></div><div className="grid gap-4 lg:grid-cols-2">{pillar.cluster_ids.map((id) => clusters.get(id)).filter((cluster): cluster is KeywordClusterItem => Boolean(cluster)).map((cluster) => <ClusterCard key={cluster.id} cluster={cluster} />)}</div></section>)}</div></section>
    <section className="mt-14"><p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-[#5549dd]">Architecture map</p><h2 className="mt-2 text-3xl font-semibold tracking-[-0.035em]">Internal links to plan</h2><p className="mt-3 max-w-3xl leading-7 text-[#686871]">Write these links into briefs and drafts so topical relationships are part of the section from day one.</p><div className="mt-6 overflow-hidden rounded-[20px] border border-[#dfdedb] bg-white"><div className="hidden grid-cols-[1fr_32px_1fr_0.8fr] gap-4 border-b border-[#e8e6e1] bg-[#f7f6f3] px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#777680] md:grid"><span>From</span><span /><span>To</span><span>Anchor</span></div><ul className="divide-y divide-[#eceae6]">{result.internal_links.map((link, index) => <li key={`${link.source_cluster_id}-${link.target_cluster_id}-${index}`} className="grid gap-2 px-5 py-4 text-sm md:grid-cols-[1fr_32px_1fr_0.8fr] md:items-center md:gap-4"><code className="truncate text-[#55555f]">{link.source_slug}</code><span className="text-[#ff5738]">→</span><code className="truncate text-[#55555f]">{link.target_slug}</code><span className="font-medium text-[#493dc0]">{link.anchor_text}</span><p className="text-xs leading-5 text-[#85848b] md:col-span-4">{link.reason}</p></li>)}</ul></div></section>
    <aside className="mt-8 rounded-[20px] border border-[#dfdedb] bg-[#fcfbf9] p-6"><h2 className="text-lg font-semibold">Before committing the plan</h2><p className="mt-2 max-w-4xl text-sm leading-6 text-[#666670]">Review page types against your products and current sitemap. The grouping represents likely shared search intent; use Search Console or equivalent data to confirm actual cannibalization on an existing site.</p></aside>
  </div>;
}

export function KeywordClusterRun({ generationId }: { generationId: string }) {
  const [run, setRun] = useState<KeywordClusterResponse | null>(null);
  const [result, setResult] = useState<KeywordClusterResult | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const [retrying, setRetrying] = useState(false);
  const processStarted = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next = await getKeywordClusterGeneration(generationId);
        if (cancelled) return;
        setRun(next);
        if (next.generation.status === "queued" && !processStarted.current) {
          processStarted.current = true;
          void processKeywordClusterGeneration(generationId).catch((caught) => {
            if (!cancelled) { processStarted.current = false; setError(caught instanceof Error ? caught.message : "The run could not be started."); }
          });
        }
        if (next.generation.status === "complete") {
          const completed = await getKeywordClusterResult(generationId);
          if (!cancelled) setResult(completed);
          return;
        }
        if (next.generation.status === "failed") { setError(next.generation.error ?? "The clustering run failed."); return; }
        timer = setTimeout(poll, 1400);
      } catch (caught) { if (!cancelled) setError(caught instanceof Error ? caught.message : "Unable to load this run."); }
    }
    void poll();
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [generationId, version]);

  async function retry() {
    setRetrying(true);
    try {
      if (run?.generation.status === "failed") await retryKeywordClusterGeneration(generationId);
      setError(""); setRun(null); setResult(null); processStarted.current = false; setVersion((value) => value + 1);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "The run could not be retried."); }
    finally { setRetrying(false); }
  }

  if (error) return <div className="mx-auto max-w-2xl rounded-[22px] border border-red-200 bg-white p-8 text-center"><p className="font-mono text-xs uppercase tracking-[0.18em] text-red-600">Plan unavailable</p><h1 className="mt-3 text-3xl font-semibold">We couldn&apos;t finish this run.</h1><p role="alert" className="mt-4 leading-7 text-[#696972]">{error}</p><div className="mt-7 flex flex-wrap justify-center gap-3"><button type="button" onClick={retry} disabled={retrying} className="rounded-xl bg-[#ff5738] px-5 py-3 font-semibold text-white disabled:opacity-60">{retrying ? "Retrying…" : "Retry this run"}</button><Link href="/agents/keyword-cluster" className="rounded-xl border border-[#d9d8d4] px-5 py-3 font-semibold">Start again</Link></div></div>;
  return result ? <Results result={result} /> : <Progress run={run} />;
}
