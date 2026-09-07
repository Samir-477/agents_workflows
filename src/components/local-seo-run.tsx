"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { CheckIcon, DownloadIcon } from "@/components/icons";
import { localApi, type LocalCopy, type LocalPage, type LocalRun } from "@/lib/local-seo-api";

const steps = [
  { key: "extracting", label: "Establishing the facts" },
  { key: "drafting", label: "Drafting each area" },
  { key: "validating", label: "Checking copy and duplication" },
  { key: "references", label: "Listing references" },
];

function stageLabel(stage: string): string {
  if (stage === "queued") return "Waiting to begin";
  if (stage === "extracting") return "Establishing the facts";
  if (stage.startsWith("drafting_page_")) return `Drafting area ${stage.replace("drafting_page_", "")}`;
  if (stage === "validating") return "Checking copy and duplication";
  if (stage === "maps_references") return "Looking up listing references";
  if (stage === "complete") return "Complete";
  if (stage === "failed") return "Failed";
  return "Working on your drafts";
}

function stepIndex(stage: string): number {
  if (stage === "queued" || stage === "extracting") return 0;
  if (stage.startsWith("drafting_page_")) return 1;
  if (stage === "validating") return 2;
  if (stage === "maps_references") return 3;
  if (stage === "complete") return 4;
  return 0;
}

function CountBadge({ label, count, limit }: { label: string; count: number; limit: number }) {
  const over = count > limit;
  return (
    <span
      className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
        over ? "border-[#ffd1a9] bg-[#fff6e9] text-[#9a5600]" : "border-[#b9dfcc] bg-[#eef9f3] text-[#23724f]"
      }`}
    >
      {label} {count} · {over ? `over ${limit}` : "within range"}
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

function DraftPage({
  page,
  index,
  runId,
  onSave,
}: {
  page: LocalPage;
  index: number;
  runId: string;
  onSave: (run: LocalRun) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    setError("");
    try {
      const content = JSON.parse(text) as LocalCopy;
      onSave(await localApi<LocalRun>(`/${runId}/pages/${index}`, "PUT", content));
      setEditing(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save draft.");
    } finally {
      setBusy(false);
    }
  }

  const combined = `Title: ${page.content.title}\nMeta description: ${page.content.meta_description}`;

  return (
    <section className="mt-10 overflow-hidden rounded-[24px] border border-[#dfdedb] bg-white">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-[#e8e6e1] px-6 py-6 sm:px-8">
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-[#5549dd]">Page {index + 1}</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.035em] sm:text-3xl">{page.area}</h2>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-[#666670]">
            <span className="rounded-full bg-[#f2f0ec] px-3 py-1.5 capitalize">{page.kind.replaceAll("_", " ")}</span>
            <span className="rounded-full bg-[#f2f0ec] px-3 py-1.5">path {page.suggested_slug}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <CopyButton text={combined} label="Copy metadata" />
          <button
            type="button"
            onClick={() => {
              setEditing(!editing);
              setText(JSON.stringify(page.content, null, 2));
              setError("");
            }}
            className="rounded-lg border border-[#d9d8d4] bg-white px-3 py-2 text-xs font-semibold text-[#4f5059] transition hover:border-[#aaa5eb] hover:text-[#4b3fca]"
          >
            {editing ? "Cancel editing" : "Edit draft copy"}
          </button>
        </div>
      </header>

      {editing ? (
        <div className="px-6 py-7 sm:px-8">
          <label htmlFor={`copy-${index}`} className="font-semibold">Editable copy JSON</label>
          <p className="mt-1 text-sm leading-6 text-[#686871]">
            Edit the text and reorder sections; keep the field names. Saving recalculates metadata counts and duplication warnings.
          </p>
          <textarea
            id={`copy-${index}`}
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={22}
            className="mt-3 w-full resize-y rounded-2xl border border-[#d9d8d4] bg-[#fcfbf9] p-4 font-mono text-sm leading-6 outline-none focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10"
          />
          {error ? <p role="alert" className="mt-2 text-sm text-red-700">{error}</p> : null}
          <button
            type="button"
            onClick={save}
            disabled={busy}
            className="mt-3 rounded-xl bg-[#ff5738] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#e9482b] disabled:opacity-60"
          >
            {busy ? "Saving…" : "Save draft"}
          </button>
        </div>
      ) : (
        <>
          <div className="bg-[#f8f7f4] px-6 py-7 sm:px-8">
            <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-[#85848b]">Search preview</p>
            <p className="mt-1 text-xs text-[#8a8990]">Illustrative only; search engines may rewrite or truncate snippets.</p>
            <div className="mt-5 max-w-3xl rounded-2xl border border-[#dfdedb] bg-white p-5 shadow-[0_8px_28px_rgba(24,24,32,0.05)] sm:p-6">
              <p className="text-sm text-[#3d6654]">your-site.com{page.suggested_slug}</p>
              <p className="mt-1 text-xl leading-7 text-[#1a0dab]">{page.content.title}</p>
              <p className="mt-1 text-sm leading-6 text-[#4d5156]">{page.content.meta_description}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <CountBadge label="Title" count={page.title_characters} limit={60} />
                <CountBadge label="Description" count={page.description_characters} limit={160} />
              </div>
            </div>
          </div>

          <div className="px-6 py-8 sm:px-8">
            <h3 className="text-2xl font-semibold tracking-[-0.03em]">{page.content.headline}</h3>
            <p className="mt-4 whitespace-pre-wrap leading-8 text-[#575760]">{page.content.introduction}</p>
            {page.content.sections.map((section, sectionIndex) => (
              <section key={sectionIndex} className="mt-6">
                <h4 className="text-lg font-semibold">{section.heading}</h4>
                <p className="mt-2 whitespace-pre-wrap leading-7 text-[#686871]">{section.body}</p>
              </section>
            ))}

            <h4 className="mt-8 text-lg font-semibold">Local FAQs</h4>
            <div className="mt-3 divide-y divide-[#e8e6e1] rounded-2xl border border-[#e6e4df]">
              {page.content.faqs.map((faq, faqIndex) => (
                <details key={faqIndex} className="group px-4 py-3">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-[#20212a]">
                    {faq.question}
                    <span className="text-lg text-[#5549dd] transition-transform group-open:rotate-45">+</span>
                  </summary>
                  <p className="mt-2 leading-7 text-[#686871]">{faq.answer}</p>
                </details>
              ))}
            </div>

            <p className="mt-6 rounded-2xl border-l-2 border-[#c9c3ff] bg-[#faf9ff] px-5 py-4 font-semibold text-[#3f3796]">
              {page.content.call_to_action}
            </p>
          </div>
        </>
      )}

      <div className="grid gap-8 border-t border-[#e8e6e1] px-6 py-8 sm:px-8 lg:grid-cols-2">
        <section>
          <h3 className="font-semibold">Business details</h3>
          <dl className="mt-3 space-y-2 text-sm">
            {Object.entries(page.business_details).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-4 border-b border-[#efede9] pb-2">
                <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#85848b]">{key}</dt>
                <dd className="text-right text-[#3d3e46]">{value || "Not supplied"}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-4 flex flex-wrap gap-2">
            {page.call_url ? (
              <a href={page.call_url} className="rounded-lg border border-[#d9d8d4] bg-white px-3 py-2 text-xs font-semibold text-[#4f5059] hover:border-[#aaa5eb]">
                Call link
              </a>
            ) : null}
            {page.directions_url ? (
              <a href={page.directions_url} target="_blank" rel="noreferrer" className="rounded-lg border border-[#d9d8d4] bg-white px-3 py-2 text-xs font-semibold text-[#4f5059] hover:border-[#aaa5eb]">
                Directions link
              </a>
            ) : null}
          </div>
        </section>

        <section>
          <h3 className="font-semibold">Linking</h3>
          <p className="mt-3 text-sm leading-6 text-[#686871]">
            Proposed sibling paths (not published):{" "}
            <span className="text-[#3d3e46]">{page.proposed_sibling_slugs.join(", ") || "None"}</span>
          </p>
          {page.existing_link_candidates.length ? (
            <ul className="mt-3 space-y-2 text-sm">
              {page.existing_link_candidates.map((url) => (
                <li key={url}>
                  <a href={url} target="_blank" rel="noreferrer" className="break-all text-[#4b3fca] hover:underline">
                    Review link candidate: {url}
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-[#8a8990]">No existing URLs were supplied for this run.</p>
          )}
        </section>
      </div>

      <details className="border-t border-[#e8e6e1] bg-[#fcfbf9] px-6 py-4 sm:px-8">
        <summary className="cursor-pointer text-sm font-semibold text-[#4b3fca]">Suggested JSON-LD — review before use</summary>
        <pre className="mt-3 overflow-auto rounded-xl border border-[#e6e4df] bg-white p-4 text-xs leading-5">
          {JSON.stringify(page.json_ld, null, 2)}
        </pre>
        <p className="mt-2 text-xs leading-5 text-[#8a8990]">
          Place reviewed JSON-LD in an application/ld+json script on the page. Empty output means schema was withheld pending facts.
        </p>
      </details>

      <section className="border-t border-[#e8e6e1] bg-[#fff8ef] px-6 py-5 sm:px-8">
        <h3 className="font-semibold text-[#7a4a12]">Before this page goes live</h3>
        <ul className="mt-3 space-y-2 text-sm leading-6 text-[#80501b]">
          {page.review_tasks.map((task) => (
            <li key={task} className="flex gap-2">
              <span aria-hidden="true">•</span> {task}
            </li>
          ))}
        </ul>
      </section>
    </section>
  );
}

function LocalProgress({ run }: { run: LocalRun | null }) {
  const stage = run?.stage ?? "queued";
  const index = stepIndex(stage);
  const progress = run?.progress ?? 0;
  return (
    <div className="mx-auto max-w-3xl rounded-[24px] border border-[#dfdedb] bg-white p-7 shadow-[0_24px_70px_rgba(26,26,36,0.08)] sm:p-10">
      <div className="flex items-start justify-between gap-5">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-[#5549dd]">Local page run</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em]">{stageLabel(stage)}</h1>
          <p className="mt-3 text-sm leading-6 text-[#74737c]">Preparing up to three grounded drafts. This can take a few minutes.</p>
        </div>
        <span className="font-mono text-sm text-[#777680]">{progress}%</span>
      </div>
      <div className="mt-7 h-2 overflow-hidden rounded-full bg-[#efeee9]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[#5a4df4] to-[#ff5738] transition-[width] duration-500"
          style={{ width: `${Math.max(progress, 2)}%` }}
        />
      </div>
      <p className="sr-only" aria-live="polite">{progress} percent complete. {stageLabel(stage)}.</p>
      <ol className="mt-8 grid gap-3 sm:grid-cols-2">
        {steps.map((item, itemIndex) => {
          const done = index > itemIndex;
          const active = index === itemIndex;
          return (
            <li
              key={item.key}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-sm ${
                active ? "border-[#c7c1ff] bg-[#f3f1ff] font-semibold text-[#4034bd]" : "border-[#eceae6] text-[#74737c]"
              }`}
            >
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full ${
                  done ? "bg-[#5a4df4] text-white" : active ? "bg-white text-[#5a4df4]" : "bg-[#f3f2ee]"
                }`}
              >
                {done ? <CheckIcon className="h-4 w-4" /> : itemIndex + 1}
              </span>
              {item.label}
            </li>
          );
        })}
      </ol>
      <p className="mt-7 text-sm leading-6 text-[#74737c]">
        You can leave this page open. It refreshes automatically and publishes the completed drafts here.
      </p>
    </div>
  );
}

function LocalResults({ run, onSave }: { run: LocalRun; onSave: (run: LocalRun) => void }) {
  const result = run.result!;

  function download() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "local-page-drafts.json";
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <div>
      <header className="flex flex-wrap items-start justify-between gap-5 border-b border-[#e3e1dc] pb-7">
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#4b3fca]">Saved · needs human review</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em] sm:text-[46px]">Your local page drafts</h1>
          <p className="mt-3 text-sm text-[#686871]">
            {result.pages.length} page{result.pages.length === 1 ? "" : "s"} · editable copy, local FAQs and suggested schema
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={download}
            className="inline-flex items-center gap-2 rounded-xl bg-[#171820] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#30313a]"
          >
            <DownloadIcon className="h-4 w-4" /> Download drafts JSON
          </button>
          <Link
            href="/agents/local-seo"
            className="rounded-xl border border-[#d9d8d4] bg-white px-4 py-3 text-sm font-semibold text-[#282932] hover:bg-[#f8f7f4]"
          >
            Generate another set
          </Link>
        </div>
      </header>

      <section className="mt-8 rounded-[20px] border border-[#d7d2f2] bg-[#f4f2ff] p-6">
        <h2 className="text-lg font-semibold">Before you use these drafts</h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-[#5b5b66]">
          {result.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      {result.warnings.length ? (
        <section className="mt-5 rounded-[20px] border border-[#f2d3a7] bg-[#fff8eb] p-6">
          <h2 className="font-semibold text-[#7a4a12]">Batch review notes</h2>
          <ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-6 text-[#80501b]">
            {result.warnings.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {result.maps_candidates.length ? (
        <section className="mt-5 rounded-[20px] border border-[#dfdedb] bg-white p-6">
          <h2 className="font-semibold">Unconfirmed OpenStreetMap references</h2>
          <p className="mt-2 text-sm leading-6 text-[#686871]">
            Open each candidate to check identity. No match has been adopted as your business details.
          </p>
          <ul className="mt-4 space-y-2">
            {result.maps_candidates.map((candidate) => (
              <li key={`${candidate.area}-${candidate.place_id}`}>
                <a
                  href={candidate.maps_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 text-sm font-semibold text-[#4b3fca] hover:underline"
                >
                  {candidate.area} — {candidate.name ?? "view candidate"}
                  <span className="font-mono text-[11px] font-normal text-[#8a8990]">{candidate.place_id}</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {result.pages.map((page, index) => (
        <DraftPage key={index} page={page} index={index} runId={run.id} onSave={onSave} />
      ))}
    </div>
  );
}

export function LocalSEORun({ runId }: { runId: string }) {
  const [run, setRun] = useState<LocalRun | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const [retrying, setRetrying] = useState(false);
  const processStarted = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const next = await localApi<LocalRun>(`/${runId}`);
        if (cancelled) return;
        setRun(next);

        if (next.status === "queued" && !processStarted.current) {
          processStarted.current = true;
          void localApi<LocalRun>(`/${runId}/process`, "POST").catch(() => {
            /* Keep polling the persisted status even if the process connection drops. */
          });
        }
        if (next.status === "failed") {
          setError(next.error ?? "The generation failed before drafts were saved.");
          return;
        }
        if (next.status === "queued" || next.status === "running") {
          timer = setTimeout(poll, 1800);
        }
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "Unable to load this run.");
      }
    }

    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [runId, version]);

  async function retry() {
    setRetrying(true);
    try {
      if (run?.status === "failed") await localApi(`/${runId}/retry`, "POST");
      setError("");
      setRun(null);
      processStarted.current = false;
      setVersion((value) => value + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The run could not be retried.");
    } finally {
      setRetrying(false);
    }
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl rounded-[22px] border border-red-200 bg-white p-8 text-center">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-red-600">Run unavailable</p>
        <h1 className="mt-3 text-3xl font-semibold">We couldn&apos;t finish this run.</h1>
        <p role="alert" className="mt-4 leading-7 text-[#696972]">{error}</p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={retry}
            disabled={retrying}
            className="rounded-xl bg-[#ff5738] px-5 py-3 font-semibold text-white transition hover:bg-[#e9482b] disabled:opacity-60"
          >
            {retrying ? "Retrying…" : "Retry this run"}
          </button>
          <Link href="/agents/local-seo" className="rounded-xl border border-[#d9d8d4] bg-white px-5 py-3 font-semibold text-[#34343d]">
            Start a new run
          </Link>
        </div>
      </div>
    );
  }

  return run?.result ? <LocalResults run={run} onSave={setRun} /> : <LocalProgress run={run} />;
}
