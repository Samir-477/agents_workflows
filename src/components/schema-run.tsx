"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { CheckIcon } from "@/components/icons";
import {
  getSchemaGeneration,
  getSchemaResult,
  processSchemaGeneration,
  retrySchemaGeneration,
  type SchemaBlockResult,
  type SchemaGenerationResponse,
  type SchemaGenerationResult,
} from "@/lib/schema-api";

const stages = ["queued", "interpreting", "compiling", "validating", "recommending", "complete"];
const labels: Record<string, string> = {
  queued: "Queued",
  interpreting: "Reading visible page facts",
  compiling: "Compiling JSON-LD",
  validating: "Checking eligibility and safety",
  recommending: "Writing placement guidance",
  complete: "Complete",
  failed: "Failed",
};

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }
  return <button type="button" onClick={copy} className="rounded-lg border border-[#d9d8d4] bg-white px-3 py-2 text-xs font-semibold text-[#4f5059] transition hover:border-[#aaa5eb] hover:text-[#4b3fca]">{copied ? "Copied" : label}</button>;
}

function Block({ block }: { block: SchemaBlockResult }) {
  const code = JSON.stringify(block.json_ld, null, 2);
  return <article className="overflow-hidden rounded-[22px] border border-[#dfdedb] bg-white">
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[#ebe9e5] px-6 py-5">
      <div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full bg-[#5a4df4] px-3 py-1 text-xs font-semibold text-white">{block.schema_type}</span>
          <span className="rounded-full bg-[#f1f0ec] px-3 py-1 text-xs text-[#666670]">{block.placement_scope}</span>
          <span className={`rounded-full px-3 py-1 text-xs font-semibold ${block.publish_ready ? "bg-[#eaf8ef] text-[#237348]" : "bg-[#fff0eb] text-[#b83b24]"}`}>{block.publish_ready ? "Checks passed" : "Needs fixes"}</span>
        </div>
        <h3 className="mt-3 text-xl font-semibold">{block.name}</h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[#686871]">{block.rationale}</p>
      </div>
      <CopyButton text={code} label={block.publish_ready ? "Copy entity" : "Copy draft"} />
    </header>
    <pre className="max-h-[420px] overflow-auto bg-[#181922] p-5 text-[13px] leading-6 text-[#e7e6ee]"><code>{code}</code></pre>
    <div className="grid gap-5 px-6 py-5 md:grid-cols-2">
      <div><p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5549dd]">Placement</p><p className="mt-2 text-sm leading-6 text-[#62626c]">{block.placement_guidance}</p></div>
      <div><p className="font-mono text-[11px] font-semibold uppercase tracking-[0.16em] text-[#5549dd]">Useful additions</p><p className="mt-2 text-sm leading-6 text-[#62626c]">{block.missing_properties.length ? block.missing_properties.join(", ") : "No standard completeness gaps detected from the supplied facts."}</p></div>
    </div>
    {block.issues.length ? <ul className="border-t border-[#f0ddd5] bg-[#fff7f3] px-6 py-4 text-sm leading-6 text-[#8e452f]">{block.issues.map((issue) => <li key={`${issue.code}-${issue.message}`}><strong className="capitalize">{issue.severity}:</strong> {issue.message}</li>)}</ul> : null}
  </article>;
}

function Progress({ run }: { run: SchemaGenerationResponse | null }) {
  const stage = run?.generation.stage ?? "queued";
  const index = stages.indexOf(stage);
  const progress = run?.generation.progress ?? 0;
  return <div className="mx-auto max-w-3xl rounded-[24px] border border-[#dfdedb] bg-white p-7 shadow-[0_24px_70px_rgba(26,26,36,0.08)] sm:p-10">
    <div className="flex items-start justify-between gap-5"><div><p className="font-mono text-xs uppercase tracking-[0.18em] text-[#5549dd]">Schema run</p><h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em]">{labels[stage] ?? "Building your schema"}</h1><p className="mt-3 line-clamp-3 text-sm leading-6 text-[#74737c]">{run?.generation.prompt ?? "Loading your page description..."}</p></div><span className="font-mono text-sm text-[#777680]">{progress}%</span></div>
    <div className="mt-7 h-2 overflow-hidden rounded-full bg-[#efeee9]"><div className="h-full rounded-full bg-gradient-to-r from-[#5a4df4] to-[#ff5738] transition-[width] duration-500" style={{ width: `${Math.max(progress, 2)}%` }} /></div>
    <ol className="mt-8 grid gap-3 sm:grid-cols-2">{stages.slice(1, -1).map((item, itemIndex) => { const actualIndex = itemIndex + 1; const done = index > actualIndex; const active = index === actualIndex || (stage === "queued" && itemIndex === 0); return <li key={item} className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-sm ${active ? "border-[#c7c1ff] bg-[#f3f1ff] font-semibold text-[#4034bd]" : "border-[#eceae6] text-[#74737c]"}`}><span className={`flex h-6 w-6 items-center justify-center rounded-full ${done ? "bg-[#5a4df4] text-white" : active ? "bg-white text-[#5a4df4]" : "bg-[#f3f2ee]"}`}>{done ? <CheckIcon className="h-4 w-4" /> : actualIndex}</span>{labels[item]}</li>; })}</ol>
    <p className="mt-7 text-sm leading-6 text-[#74737c]">The final block is compiled by code after the model identifies the page entities and supplied facts.</p>
  </div>;
}

function Results({ result }: { result: SchemaGenerationResult }) {
  const statusStyles = result.publish_ready ? "border-[#bfe6cc] bg-[#eef9f2] text-[#226844]" : "border-[#ffc9bc] bg-[#fff2ee] text-[#9f321e]";
  return <div>
    <header className="flex flex-wrap items-start justify-between gap-5 border-b border-[#e3e1dc] pb-7"><div><p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#4b3fca]">Generation complete</p><h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em] sm:text-[46px]">{result.page_name}</h1><p className="mt-3 text-sm text-[#686871]">{result.blocks.length} schema type{result.blocks.length === 1 ? "" : "s"} · {result.page_type}</p></div><Link href="/agents/schema-markup" className="rounded-xl bg-[#171820] px-4 py-3 text-sm font-semibold text-white hover:bg-[#30313a]">Generate another block</Link></header>
    <div className={`mt-8 rounded-2xl border px-5 py-4 ${statusStyles}`}><p className="font-semibold">{result.publish_ready ? "No blocking checks found" : `${result.blocking_issue_count} blocking issue${result.blocking_issue_count === 1 ? "" : "s"} must be fixed`}</p><p className="mt-1 text-sm leading-6 opacity-90">{result.publish_ready ? "Review the warnings and validate the final live page before publishing." : "This is usable as a working draft, but it should not be placed on the live page yet."}</p></div>
    <section className={`mt-5 overflow-hidden rounded-[22px] border bg-white ${result.publish_ready ? "border-[#d7d2ff]" : "border-[#ffc9bc]"}`}><div className={`flex flex-wrap items-start justify-between gap-4 px-6 py-5 ${result.publish_ready ? "bg-[#f2f0ff]" : "bg-[#fff2ee]"}`}><div><p className={`font-mono text-[11px] font-semibold uppercase tracking-[0.18em] ${result.publish_ready ? "text-[#4b3fca]" : "text-[#b83b24]"}`}>{result.publish_ready ? "Publish-ready draft" : "Draft JSON-LD — fix before publishing"}</p><p className="mt-2 max-w-3xl text-sm leading-6 text-[#656471]">{result.validation_summary}</p></div><CopyButton text={result.script} label={result.publish_ready ? "Copy script" : "Copy draft"} /></div><pre className="max-h-[560px] overflow-auto bg-[#181922] p-6 text-[13px] leading-6 text-[#e7e6ee]"><code>{result.script}</code></pre></section>
    {result.warnings.length ? <ul className="mt-6 list-disc rounded-2xl border border-[#f2d3a7] bg-[#fff8eb] px-10 py-4 text-sm leading-6 text-[#80501b]">{result.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}
    <div className="mt-8 space-y-5">{result.blocks.map((block) => <Block key={block.id} block={block} />)}</div>
    <aside className="mt-8 rounded-[20px] border border-[#dfdedb] bg-[#fcfbf9] p-6"><h2 className="text-lg font-semibold">Before publishing</h2><ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-[#666670]">{!result.publish_ready ? <li>Resolve every blocking issue shown on the entity cards.</li> : null}<li>Confirm every value exactly matches content visible on the page.</li><li>Paste the script into the page or template scope shown above.</li><li>Test the final live page in Google&apos;s Rich Results Test and URL Inspection.</li><li>Keep the markup synchronized when prices, hours, dates or answers change.</li></ol><a href="https://search.google.com/test/rich-results" target="_blank" rel="noreferrer" className="mt-5 inline-flex rounded-xl bg-[#ff5738] px-4 py-3 text-sm font-semibold text-white">Open Rich Results Test ↗</a></aside>
  </div>;
}

export function SchemaRun({ generationId }: { generationId: string }) {
  const [run, setRun] = useState<SchemaGenerationResponse | null>(null);
  const [result, setResult] = useState<SchemaGenerationResult | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const [retrying, setRetrying] = useState(false);
  const processStarted = useRef(false);
  useEffect(() => { let cancelled = false; let timer: ReturnType<typeof setTimeout> | undefined; async function poll() { try { const next = await getSchemaGeneration(generationId); if (cancelled) return; setRun(next); if (next.generation.status === "queued" && !processStarted.current) { processStarted.current = true; void processSchemaGeneration(generationId).catch((caught) => { if (!cancelled) { processStarted.current = false; setError(caught instanceof Error ? caught.message : "The run could not be started."); } }); } if (next.generation.status === "complete") { const completed = await getSchemaResult(generationId); if (!cancelled) setResult(completed); return; } if (next.generation.status === "failed") { setError(next.generation.error ?? "The schema run failed."); return; } timer = setTimeout(poll, 1400); } catch (caught) { if (!cancelled) setError(caught instanceof Error ? caught.message : "Unable to load this run."); } } poll(); return () => { cancelled = true; if (timer) clearTimeout(timer); }; }, [generationId, version]);
  async function retry() { setRetrying(true); try { if (run?.generation.status === "failed") await retrySchemaGeneration(generationId); setError(""); setRun(null); setResult(null); processStarted.current = false; setVersion((value) => value + 1); } catch (caught) { setError(caught instanceof Error ? caught.message : "The run could not be retried."); } finally { setRetrying(false); } }
  if (error) return <div className="mx-auto max-w-2xl rounded-[22px] border border-red-200 bg-white p-8 text-center"><p className="font-mono text-xs uppercase tracking-[0.18em] text-red-600">Generation unavailable</p><h1 className="mt-3 text-3xl font-semibold">We couldn&apos;t finish this run.</h1><p role="alert" className="mt-4 leading-7 text-[#696972]">{error}</p><div className="mt-7 flex flex-wrap justify-center gap-3"><button type="button" onClick={retry} disabled={retrying} className="rounded-xl bg-[#ff5738] px-5 py-3 font-semibold text-white disabled:opacity-60">{retrying ? "Retrying..." : "Retry this run"}</button><Link href="/agents/schema-markup" className="rounded-xl border border-[#d9d8d4] px-5 py-3 font-semibold">Start again</Link></div></div>;
  return result ? <Results result={result} /> : <Progress run={run} />;
}
