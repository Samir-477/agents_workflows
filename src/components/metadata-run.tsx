"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { CheckIcon } from "@/components/icons";
import {
  getMetadataGeneration,
  getMetadataResult,
  processMetadataGeneration,
  retryMetadataGeneration,
  type MetadataGenerationResponse,
  type MetadataGenerationResult,
  type MetadataOption,
  type PageMetadataResult,
} from "@/lib/metadata-api";

const stages = [
  "queued",
  "parsing",
  "generating",
  "validating",
  "deduplicating",
  "recommending",
  "complete",
];

const labels: Record<string, string> = {
  queued: "Queued",
  parsing: "Reading your brief",
  generating: "Writing distinct options",
  validating: "Checking lengths and claims",
  deduplicating: "Comparing variants",
  recommending: "Choosing the strongest pair",
  complete: "Complete",
  failed: "Failed",
};

function LengthBadge({ option }: { option: MetadataOption }) {
  const styles =
    option.length_status === "good"
      ? "border-[#b9dfcc] bg-[#eef9f3] text-[#23724f]"
      : option.length_status === "long"
        ? "border-[#ffd1a9] bg-[#fff6e9] text-[#9a5600]"
        : "border-[#d6d2ff] bg-[#f2f0ff] text-[#4b3fca]";
  return (
    <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${styles}`}>
      {option.character_count} chars · {option.length_status}
    </span>
  );
}

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="rounded-lg border border-[#d9d8d4] bg-white px-3 py-2 text-xs font-semibold text-[#4f5059] transition hover:border-[#aaa5eb] hover:text-[#4b3fca]"
    >
      {copied ? "Copied" : label}
    </button>
  );
}

function OptionCard({ option, index }: { option: MetadataOption; index: number }) {
  return (
    <article
      className={`rounded-2xl border p-5 ${
        option.recommended
          ? "border-[#aaa4ff] bg-[#f7f6ff] shadow-[0_8px_28px_rgba(84,72,220,0.08)]"
          : option.issues.length
            ? "border-[#f0c7bf] bg-[#fffafa]"
            : "border-[#e1dfdb] bg-white"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-[#9a989f]">{String(index + 1).padStart(2, "0")}</span>
          {option.recommended ? (
            <span className="rounded-full bg-[#5a4df4] px-2.5 py-1 text-[11px] font-semibold text-white">Recommended</span>
          ) : null}
          <LengthBadge option={option} />
        </div>
        <CopyButton text={option.text} />
      </div>
      <p className="mt-4 text-[17px] font-semibold leading-7 text-[#20212a]">{option.text}</p>
      <div className="mt-4 flex flex-wrap gap-2 text-xs text-[#666670]">
        <span className="rounded-full bg-[#f1f0ec] px-2.5 py-1">{option.intent}</span>
        <span className="rounded-full bg-[#f1f0ec] px-2.5 py-1">{option.angle}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-[#71717a]">{option.rationale}</p>
      {option.issues.length ? (
        <ul className="mt-4 space-y-1 rounded-xl border border-[#f3d1ca] bg-[#fff3f1] px-4 py-3 text-xs leading-5 text-[#a53d2c]">
          {option.issues.map((issue) => <li key={issue}>• {issue}</li>)}
        </ul>
      ) : null}
    </article>
  );
}

function PageResult({ page, index }: { page: PageMetadataResult; index: number }) {
  const title = page.titles.find((item) => item.id === page.recommended_title_id) ?? page.titles[0];
  const description = page.descriptions.find((item) => item.id === page.recommended_description_id) ?? page.descriptions[0];
  const combined = `Title: ${title.text}\nMeta description: ${description.text}`;

  return (
    <section className="mt-10 overflow-hidden rounded-[24px] border border-[#dfdedb] bg-white">
      <header className="border-b border-[#e8e6e1] px-6 py-6 sm:px-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-[#5549dd]">Page {index + 1}</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-[-0.035em] sm:text-3xl">{page.page_name}</h2>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-[#666670]">
              <span className="rounded-full bg-[#f2f0ec] px-3 py-1.5">{page.page_type}</span>
              <span className="rounded-full bg-[#f2f0ec] px-3 py-1.5">{page.search_intent}</span>
              {page.primary_keyword ? (
                <span className="rounded-full bg-[#fff0eb] px-3 py-1.5 text-[#b73d25]">
                  {page.primary_keyword} · {page.keyword_source}
                </span>
              ) : null}
            </div>
          </div>
          <CopyButton text={combined} label="Copy recommended pair" />
        </div>
      </header>

      <div className="bg-[#f8f7f4] px-6 py-7 sm:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-[#85848b]">Recommended search preview</p>
            <p className="mt-1 text-xs text-[#8a8990]">Preview is illustrative; search engines may rewrite or truncate snippets.</p>
          </div>
        </div>
        <div className="mt-5 max-w-3xl rounded-2xl border border-[#dfdedb] bg-white p-5 shadow-[0_8px_28px_rgba(24,24,32,0.05)] sm:p-6">
          <p className="text-sm text-[#3d6654]">your-site.com › {page.page_key}</p>
          <p className="mt-1 text-xl leading-7 text-[#1a0dab]">{title.text}</p>
          <p className="mt-1 text-sm leading-6 text-[#4d5156]">{description.text}</p>
          <div className="mt-3 flex flex-wrap gap-2"><LengthBadge option={title} /><LengthBadge option={description} /></div>
        </div>
        {page.warnings.length ? (
          <ul className="mt-4 max-w-3xl space-y-1 rounded-xl border border-[#f2d3a7] bg-[#fff8eb] px-4 py-3 text-sm leading-6 text-[#80501b]">
            {page.warnings.map((warning) => <li key={warning}>• {warning}</li>)}
          </ul>
        ) : null}
      </div>

      <div className="grid gap-10 px-6 py-8 sm:px-8 lg:grid-cols-2">
        <div>
          <div className="flex items-end justify-between gap-3">
            <div><p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#85848b]">Title tags</p><h3 className="mt-1 text-xl font-semibold">Four options</h3></div>
            <span className="text-xs text-[#8b8a91]">Preferred: 50–60</span>
          </div>
          <div className="mt-4 space-y-3">{page.titles.map((option, optionIndex) => <OptionCard key={option.id} option={option} index={optionIndex} />)}</div>
        </div>
        <div>
          <div className="flex items-end justify-between gap-3">
            <div><p className="font-mono text-[11px] uppercase tracking-[0.18em] text-[#85848b]">Meta descriptions</p><h3 className="mt-1 text-xl font-semibold">Three options</h3></div>
            <span className="text-xs text-[#8b8a91]">Preferred: 140–160</span>
          </div>
          <div className="mt-4 space-y-3">{page.descriptions.map((option, optionIndex) => <OptionCard key={option.id} option={option} index={optionIndex} />)}</div>
        </div>
      </div>

      <footer className="border-t border-[#e8e6e1] bg-[#fcfbf9] px-6 py-5 text-sm leading-6 text-[#62626c] sm:px-8">
        <strong className="text-[#24252d]">Brand guidance:</strong> {page.brand_guidance}
      </footer>
    </section>
  );
}

function GenerationProgress({ run }: { run: MetadataGenerationResponse | null }) {
  const stage = run?.generation.stage ?? "queued";
  const index = stages.indexOf(stage);
  const progress = run?.generation.progress ?? 0;
  return (
    <div className="mx-auto max-w-3xl rounded-[24px] border border-[#dfdedb] bg-white p-7 shadow-[0_24px_70px_rgba(26,26,36,0.08)] sm:p-10">
      <div className="flex items-start justify-between gap-5">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-[#5549dd]">Metadata run</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em]">{labels[stage] ?? "Working on your metadata"}</h1>
          <p className="mt-3 line-clamp-2 text-sm leading-6 text-[#74737c]">{run?.generation.prompt ?? "Loading your brief…"}</p>
        </div>
        <span className="font-mono text-sm text-[#777680]">{progress}%</span>
      </div>
      <div className="mt-7 h-2 overflow-hidden rounded-full bg-[#efeee9]">
        <div className="h-full rounded-full bg-gradient-to-r from-[#5a4df4] to-[#ff5738] transition-[width] duration-500" style={{ width: `${Math.max(progress, 2)}%` }} />
      </div>
      <ol className="mt-8 grid gap-3 sm:grid-cols-2">
        {stages.slice(1, -1).map((item, itemIndex) => {
          const actualIndex = itemIndex + 1;
          const done = index > actualIndex;
          const active = index === actualIndex || (stage === "queued" && itemIndex === 0);
          return (
            <li key={item} className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-sm ${active ? "border-[#c7c1ff] bg-[#f3f1ff] font-semibold text-[#4034bd]" : "border-[#eceae6] text-[#74737c]"}`}>
              <span className={`flex h-6 w-6 items-center justify-center rounded-full ${done ? "bg-[#5a4df4] text-white" : active ? "bg-white text-[#5a4df4]" : "bg-[#f3f2ee]"}`}>
                {done ? <CheckIcon className="h-4 w-4" /> : actualIndex}
              </span>
              {labels[item]}
            </li>
          );
        })}
      </ol>
      <p className="mt-7 text-sm leading-6 text-[#74737c]">The run may make a repair pass when counts, claims or duplication checks need attention.</p>
    </div>
  );
}

function GenerationResults({ result }: { result: MetadataGenerationResult }) {
  return (
    <div>
      <header className="flex flex-wrap items-start justify-between gap-5 border-b border-[#e3e1dc] pb-7">
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#4b3fca]">Generation complete</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em] sm:text-[46px]">Your metadata options</h1>
          <p className="mt-3 text-sm text-[#686871]">{result.pages.length} page{result.pages.length === 1 ? "" : "s"} · four titles and three descriptions per page</p>
        </div>
        <Link href="/agents/meta-title-description" className="rounded-xl bg-[#171820] px-4 py-3 text-sm font-semibold text-white hover:bg-[#30313a]">Generate another set</Link>
      </header>
      {result.batch_warnings.length ? (
        <ul className="mt-6 rounded-2xl border border-[#f2d3a7] bg-[#fff8eb] px-5 py-4 text-sm leading-6 text-[#80501b]">
          {result.batch_warnings.map((warning) => <li key={warning}>• {warning}</li>)}
        </ul>
      ) : null}
      {result.pages.map((page, index) => <PageResult key={page.page_key} page={page} index={index} />)}
    </div>
  );
}

export function MetadataRun({ generationId }: { generationId: string }) {
  const [run, setRun] = useState<MetadataGenerationResponse | null>(null);
  const [result, setResult] = useState<MetadataGenerationResult | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const [retrying, setRetrying] = useState(false);
  const processStarted = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next = await getMetadataGeneration(generationId);
        if (cancelled) return;
        setRun(next);
        if (next.generation.status === "queued" && !processStarted.current) {
          processStarted.current = true;
          void processMetadataGeneration(generationId).catch((caught) => {
            if (!cancelled) {
              processStarted.current = false;
              setError(caught instanceof Error ? caught.message : "The run could not be started.");
            }
          });
        }
        if (next.generation.status === "complete") {
          const completed = await getMetadataResult(generationId);
          if (!cancelled) setResult(completed);
          return;
        }
        if (next.generation.status === "failed") {
          setError(next.generation.error ?? "The metadata run failed.");
          return;
        }
        timer = setTimeout(poll, 1400);
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "Unable to load this run.");
      }
    }
    poll();
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [generationId, version]);

  async function retry() {
    setRetrying(true);
    try {
      if (run?.generation.status === "failed") await retryMetadataGeneration(generationId);
      setError("");
      setRun(null);
      setResult(null);
      processStarted.current = false;
      setVersion((item) => item + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The run could not be retried.");
    } finally {
      setRetrying(false);
    }
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl rounded-[22px] border border-red-200 bg-white p-8 text-center">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-red-600">Generation unavailable</p>
        <h1 className="mt-3 text-3xl font-semibold">We couldn&apos;t finish this run.</h1>
        <p role="alert" className="mt-4 leading-7 text-[#696972]">{error}</p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={retry} disabled={retrying} className="rounded-xl bg-[#ff5738] px-5 py-3 font-semibold text-white disabled:opacity-60">{retrying ? "Retrying…" : "Retry this run"}</button>
          <Link href="/agents/meta-title-description" className="rounded-xl border border-[#d9d8d4] px-5 py-3 font-semibold">Start again</Link>
        </div>
      </div>
    );
  }

  return result ? <GenerationResults result={result} /> : <GenerationProgress run={run} />;
}
