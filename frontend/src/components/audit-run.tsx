"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { CheckIcon, DownloadIcon } from "@/components/icons";
import {
  getAudit,
  getAuditPdfUrl,
  getAuditReport,
  processAudit,
  retryAudit,
  type AuditReport,
  type AuditResponse,
} from "@/lib/api";

const stages = ["queued", "validating", "crawling", "auditing", "scoring", "reporting", "complete"];
const visibleStages = ["validating", "crawling", "auditing", "scoring", "reporting"];

const stageLabels: Record<string, string> = {
  queued: "Queued",
  validating: "Validating website",
  crawling: "Crawling pages",
  auditing: "Checking SEO signals",
  scoring: "Prioritizing findings",
  reporting: "Writing your report",
  complete: "Complete",
  failed: "Failed",
};

function severityStyles(severity: string): string {
  if (severity === "critical") return "bg-[#fff0ee] text-[#c83220] border-[#ffc8bf]";
  if (severity === "important") return "bg-[#fff6e8] text-[#a85a00] border-[#ffdca6]";
  return "bg-[#eeedff] text-[#4b3fca] border-[#d5d1ff]";
}

function AuditProgress({ audit }: { audit: AuditResponse | null }) {
  const stage = audit?.audit.stage ?? "queued";
  const currentIndex = stages.indexOf(stage);
  const isQueued = stage === "queued";
  const progress = audit?.audit.progress ?? 0;

  return (
    <div className="mx-auto max-w-3xl rounded-[24px] border border-[#dfdedb] bg-white p-7 shadow-[0_24px_70px_rgba(26,26,36,0.08)] sm:p-10">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-[#5549dd]">{isQueued ? "Audit queued" : "Audit in progress"}</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[#12131a]">{isQueued ? "Waiting to begin" : stageLabels[stage] ?? "Working on your audit"}</h1>
          {audit?.audit.requested_url ? <p className="mt-2 break-all text-sm text-[#74737c]">{audit.audit.requested_url}</p> : null}
        </div>
        <span className="font-mono text-sm text-[#777680]">{progress}%</span>
      </div>
      <div className="mt-7 h-2 overflow-hidden rounded-full bg-[#efeee9]" aria-hidden="true">
        <div className="h-full rounded-full bg-gradient-to-r from-[#5a4df4] to-[#ff5738] transition-[width] duration-500" style={{ width: `${Math.max(progress, 2)}%` }} />
      </div>
      <p className="sr-only" aria-live="polite">Audit {progress} percent complete. Current stage: {stageLabels[stage]}.</p>

      <ol className="mt-9 grid gap-3 sm:grid-cols-2">
        {visibleStages.map((item, index) => {
          const actualIndex = index + 1;
          const done = currentIndex > actualIndex;
          const active = isQueued ? index === 0 : currentIndex === actualIndex;
          return (
            <li key={item} className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-sm ${active ? "border-[#c7c1ff] bg-[#f3f1ff] font-semibold text-[#4034bd]" : "border-[#eceae6] text-[#74737c]"}`}>
              <span className={`flex h-6 w-6 items-center justify-center rounded-full ${done ? "bg-[#5a4df4] text-white" : active ? "bg-white text-[#5a4df4]" : "bg-[#f3f2ee]"}`} aria-hidden="true">
                {done ? <CheckIcon className="h-4 w-4" /> : actualIndex}
              </span>
              {stageLabels[item]}
            </li>
          );
        })}
      </ol>
      <p className="mt-8 text-sm leading-6 text-[#74737c]">You can leave this page open. It refreshes automatically and publishes the completed report here.</p>
    </div>
  );
}

function AuditResults({ report }: { report: AuditReport }) {
  const score = report.site_score ?? 0;
  const scoreLabel = score >= 80 ? "Strong" : score >= 60 ? "Needs attention" : "Needs work";
  const scoreColor = score >= 80 ? "#2f8f68" : score >= 60 ? "#e39a2d" : "#e5523a";
  return (
    <div>
      <header className="flex flex-wrap items-start justify-between gap-5 border-b border-[#e3e1dc] pb-7">
        <div className="max-w-3xl">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#4b3fca]">Completed audit</p>
          <h1 className="mt-2 break-words text-4xl font-semibold tracking-[-0.045em] text-[#11121a] sm:text-[46px]">SEO audit report</h1>
          <a href={report.requested_url} target="_blank" rel="noreferrer" className="mt-2 block break-all text-sm text-[#65656e] underline decoration-[#c9c7c2] underline-offset-4 hover:text-[#e94320]">{report.requested_url}</a>
        </div>
        <div className="flex flex-wrap gap-3">
          <a href={getAuditPdfUrl(report.audit_id)} download className="inline-flex items-center gap-2 rounded-xl bg-[#171820] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#30313a]"><DownloadIcon className="h-4 w-4" />Download PDF</a>
          <Link href="/agents/seo-audit" className="rounded-xl border border-[#d9d8d4] bg-white px-4 py-3 text-sm font-semibold text-[#282932] hover:bg-[#f8f7f4]">Run another audit</Link>
        </div>
      </header>

      <section aria-label="Audit overview" className="mt-8 overflow-hidden rounded-[20px] border border-[#dfdedb] bg-white">
        <div className="grid gap-7 p-6 sm:p-8 lg:grid-cols-[180px_1fr] lg:items-center">
          <div className="flex flex-col items-center lg:border-r lg:border-[#eceae6] lg:pr-7">
            <div className="relative flex h-32 w-32 items-center justify-center rounded-full" style={{ background: `conic-gradient(${scoreColor} ${score * 3.6}deg, #eeece7 0deg)` }}>
              <div className="flex h-[108px] w-[108px] flex-col items-center justify-center rounded-full bg-white">
                <strong className="text-4xl font-semibold tracking-[-0.06em] text-[#171820]">{report.site_score ?? "—"}</strong>
                <span className="text-[11px] text-[#85848b]">out of 100</span>
              </div>
            </div>
            <span className="mt-3 text-sm font-semibold" style={{ color: scoreColor }}>{scoreLabel}</span>
          </div>
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-[#84838a]">Executive summary</p>
            <p className="mt-3 max-w-4xl text-base leading-7 text-[#44454e]">{report.executive_summary}</p>
          </div>
        </div>
        <div className="grid border-t border-[#eceae6] bg-[#fcfbf9] sm:grid-cols-4">
          <div className="px-5 py-4 sm:border-r sm:border-[#eceae6]"><strong className="text-lg text-[#282932]">{report.pages_crawled}</strong><span className="ml-2 text-sm text-[#777680]">pages inspected</span></div>
          {(["critical", "important", "minor"] as const).map((severity) => (
            <div key={severity} className="flex items-center gap-3 border-t border-[#eceae6] px-5 py-4 sm:border-r sm:border-t-0">
              <span className={`h-2.5 w-2.5 rounded-full ${severity === "critical" ? "bg-[#e5523a]" : severity === "important" ? "bg-[#e39a2d]" : "bg-[#6658e8]"}`} />
              <strong className="text-lg text-[#282932]">{report.severity_counts[severity] ?? 0}</strong>
              <span className="text-sm capitalize text-[#777680]">{severity}</span>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="quick-wins-heading" className="mt-8 rounded-[18px] border border-[#dfdedb] bg-white p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-2"><h2 id="quick-wins-heading" className="text-xl font-semibold tracking-[-0.025em]">Quick wins</h2><span className="text-xs text-[#777680]">Best places to start</span></div>
        <ol className="mt-4 grid gap-x-8 md:grid-cols-2">
          {report.quick_wins.map((item, index) => (
            <li key={item} className="flex gap-3 border-t border-[#eceae6] py-3 text-[#45464f]">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[#f3f1ff] font-mono text-xs font-semibold text-[#5549dd]">{index + 1}</span>
              <span className="text-sm leading-6">{item}</span>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="findings-heading" className="mt-12">
        <div className="flex items-end gap-4">
          <div>
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-[#84838a]">Detailed results</p>
            <h2 id="findings-heading" className="mt-1 text-3xl font-semibold tracking-[-0.035em]">Prioritized findings</h2>
          </div>
          <span className="mb-2 h-px flex-1 bg-[#e3e1dc]" />
        </div>

        <div className="mt-6 space-y-3">
          {report.findings.map((finding, index) => (
            <article key={`${finding.rule_id}-${index}`} className="overflow-hidden rounded-[16px] border border-[#e2e0dc] bg-white transition-shadow hover:shadow-[0_10px_32px_rgba(24,24,32,0.05)]">
              <div className="p-5 sm:px-6 sm:py-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="flex min-w-0 gap-4">
                    <span className="font-mono text-sm text-[#aaa8ae]">{String(index + 1).padStart(2, "0")}</span>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold capitalize ${severityStyles(finding.severity)}`}>{finding.severity}</span>
                        <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#85848b]">{finding.confidence} confidence</span>
                      </div>
                      <h3 className="mt-2 text-xl font-semibold tracking-[-0.025em] text-[#171820]">{finding.title}</h3>
                    </div>
                  </div>
                  <span className="rounded-lg bg-[#f5f3ef] px-3 py-2 font-mono text-[11px] text-[#68676e]">Priority {Math.round(finding.score)}</span>
                </div>

                <div className="mt-5 grid gap-5 border-t border-[#efede9] pt-5 lg:grid-cols-[0.9fr_1.1fr]">
                  <div>
                    <h4 className="text-sm font-semibold text-[#23242c]">Why it matters</h4>
                    <p className="mt-2 text-sm leading-6 text-[#686871]">{finding.why_it_matters}</p>
                    <p className="mt-3 text-xs leading-5 text-[#8a8990]"><span className="font-semibold text-[#6d6c74]">Evidence:</span> {finding.evidence}</p>
                  </div>
                  <div className="border-l-2 border-[#c9c3ff] bg-[#faf9ff] px-4 py-3">
                    <h4 className="text-sm font-semibold text-[#4137b5]">Suggested fix</h4>
                    <p className="mt-2 text-sm leading-6 text-[#555166]">{finding.recommendation}</p>
                  </div>
                </div>

              </div>

              <details className="border-t border-[#eceae6] bg-[#fcfbf9] px-5 py-3 sm:px-6">
                <summary className="cursor-pointer text-sm font-semibold text-[#4b3fca]">{finding.affected_urls.length} affected page{finding.affected_urls.length === 1 ? "" : "s"}</summary>
                <ul className="mt-3 space-y-2 text-sm text-[#6a6971]">
                  {finding.affected_urls.map((url) => <li key={url} className="break-all">{url}</li>)}
                </ul>
              </details>
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="limitations-heading" className="mt-10 rounded-2xl border border-[#dfdedb] bg-[#f7f6f2] p-6">
        <h2 id="limitations-heading" className="text-lg font-semibold">Coverage and limitations</h2>
        <ul className="mt-3 space-y-2 text-sm leading-6 text-[#686871]">{report.limitations.map((item) => <li key={item}>• {item}</li>)}</ul>
      </section>
    </div>
  );
}

export function AuditRun({ auditId }: { auditId: string }) {
  const [audit, setAudit] = useState<AuditResponse | null>(null);
  const [report, setReport] = useState<AuditReport | null>(null);
  const [error, setError] = useState("");
  const [pollVersion, setPollVersion] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const processStartedRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const nextAudit = await getAudit(auditId);
        if (cancelled) return;
        setAudit(nextAudit);

        if (nextAudit.audit.status === "queued" && !processStartedRef.current) {
          processStartedRef.current = true;
          void processAudit(auditId).catch((caught) => {
            if (!cancelled) {
              processStartedRef.current = false;
              setError(caught instanceof Error ? caught.message : "The audit could not be started.");
            }
          });
        }

        if (nextAudit.audit.status === "complete") {
          const nextReport = await getAuditReport(auditId);
          if (!cancelled) setReport(nextReport);
          return;
        }
        if (nextAudit.audit.status === "failed") {
          setError(nextAudit.audit.error ?? "The audit failed before a report was created.");
          return;
        }
        timer = setTimeout(poll, 1500);
      } catch (caught) {
        if (!cancelled) setError(caught instanceof Error ? caught.message : "Unable to load audit progress.");
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [auditId, pollVersion]);

  async function handleRetry() {
    setIsRetrying(true);
    try {
      if (audit?.audit.status === "failed") await retryAudit(auditId);
      setError("");
      setAudit(null);
      setReport(null);
      processStartedRef.current = false;
      setPollVersion((version) => version + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The audit could not be retried.");
    } finally {
      setIsRetrying(false);
    }
  }

  if (error) {
    const friendlyError = error === "All connection attempts failed"
      ? "The worker could not reach the submitted website. The site or network may have been temporarily unavailable."
      : error;
    return (
      <div className="mx-auto max-w-2xl rounded-[22px] border border-red-200 bg-white p-8 text-center">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-red-600">Audit unavailable</p>
        <h1 className="mt-3 text-3xl font-semibold">We couldn&apos;t finish this run.</h1>
        <p role="alert" className="mt-4 leading-7 text-[#696972]">{friendlyError}</p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={handleRetry} disabled={isRetrying} className="rounded-xl bg-[#ff5738] px-5 py-3 font-semibold text-white disabled:cursor-wait disabled:opacity-70">
            {isRetrying ? "Retrying…" : audit?.audit.status === "failed" ? "Retry this audit" : "Check connection again"}
          </button>
          <Link href="/agents/seo-audit" className="rounded-xl border border-[#d9d8d4] bg-white px-5 py-3 font-semibold text-[#34343d]">Start a new audit</Link>
        </div>
      </div>
    );
  }

  return report ? <AuditResults report={report} /> : <AuditProgress audit={audit} />;
}
