"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ArrowIcon, TrashIcon } from "@/components/icons";
import { diagnosisLabels, diagnosisRequest, type HistoryItem, type HistoryPage } from "@/lib/diagnosis-api";

function hostname(value: string) {
  try { return new URL(value).hostname.replace(/^www\./, ""); }
  catch { return value; }
}

function statusLabel(status: string) {
  return status === "complete" ? "Complete" : status === "partial" ? "Needs review" : status === "cancelled" ? "Cancelled" : status === "running" ? "Running" : "Queued";
}

function statusStyle(status: string) {
  if (status === "complete") return "border-[#bfe3ce] bg-[#edf8f1] text-[#087849]";
  if (status === "partial") return "border-[#f0d6a8] bg-[#fff8e9] text-[#8a5a10]";
  if (status === "cancelled") return "border-[#e2e5e4] bg-[#f3f5f4] text-[#697276]";
  if (status === "running") return "border-[#bcd9e8] bg-[#eef7fb] text-[#176584]";
  return "border-[#d8d5ef] bg-[#f4f2fb] text-[#5b5091]";
}

function sessionDate(value: string) {
  const date = new Date(value);
  return {
    date: date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }),
    time: date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }),
  };
}

function pageNumbers(current: number, total: number) {
  const values = new Set([1, total, current - 1, current, current + 1]);
  return [...values].filter((page) => page >= 1 && page <= total).sort((a, b) => a - b);
}

export function AuditHistory({ initialSessions = null }: { initialSessions?: HistoryPage | null }) {
  const [history, setHistory] = useState<HistoryPage | null>(initialSessions);
  const [loading, setLoading] = useState(initialSessions === null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState("");

  async function loadPage(page: number) {
    setLoading(true);
    setError("");
    try {
      setHistory(await diagnosisRequest<HistoryPage>(`?page=${page}&page_size=10`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load sessions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (initialSessions !== null) return;
    let active = true;
    diagnosisRequest<HistoryPage>("?page=1&page_size=10")
      .then((result) => { if (active) setHistory(result); })
      .catch((caught) => { if (active) setError(caught instanceof Error ? caught.message : "Unable to load sessions."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [initialSessions]);

  async function remove(item: HistoryItem) {
    if (!window.confirm(`Delete the saved session for ${hostname(item.url)}? This cannot be undone.`)) return;
    setDeleting(item.id);
    setError("");
    try {
      await diagnosisRequest<void>(`/${item.id}`, undefined, "DELETE");
      const currentPage = history?.page || 1;
      const targetPage = history?.items.length === 1 && currentPage > 1 ? currentPage - 1 : currentPage;
      await loadPage(targetPage);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to delete this session.");
    } finally {
      setDeleting("");
    }
  }

  const sessions = history?.items || [];
  const currentPage = history?.page || 1;
  const totalPages = history?.total_pages || 1;
  const firstItem = history?.total ? (currentPage - 1) * history.page_size + 1 : 0;
  const lastItem = history ? Math.min(currentPage * history.page_size, history.total) : 0;
  const pages = pageNumbers(currentPage, totalPages);

  return <div>
    <header className="flex flex-wrap items-end justify-between gap-8">
      <div><p className="text-[11px] font-semibold uppercase tracking-[.22em] text-[#747d81]">History</p><h1 className="mt-4 text-4xl font-semibold tracking-[-.045em] text-[#121719]">Sessions</h1><p className="mt-4 text-base leading-7 text-[#70787c]">Review saved URL runs, participating agents and report status from one place.</p></div>
      <Link href="/diagnosis" className="rounded-full bg-[#007846] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00683d]">New run</Link>
    </header>

    {error && <p role="alert" className="mt-8 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">{error}</p>}

    {history || loading ? <section className="mt-10 overflow-hidden rounded-[22px] border border-[#dce2df] bg-white shadow-[0_12px_36px_rgba(23,31,27,.055)]" aria-busy={loading}>
      <div className="overflow-x-auto">
        <table className={`w-full min-w-[1050px] border-collapse text-left transition-opacity ${loading ? "opacity-55" : "opacity-100"}`}>
          <thead className="bg-[#f4f7f5] text-[10px] font-semibold uppercase tracking-[.16em] text-[#6f7975]">
            <tr><th className="w-[31%] px-6 py-4">Session</th><th className="w-[13%] px-4 py-4">Run type</th><th className="w-[22%] px-4 py-4">Agent coverage</th><th className="px-4 py-4 text-center">Findings</th><th className="px-4 py-4">Status</th><th className="px-4 py-4">Created</th><th className="px-6 py-4 text-right">Actions</th></tr>
          </thead>
          <tbody className="divide-y divide-[#e3e7e5]">
            {sessions.map((item) => {
              const created = sessionDate(item.created_at);
              const visibleAgents = item.selected_agents.slice(0, 2);
              return <tr key={item.id} className="group transition hover:bg-[#f8fbf9]">
                <td className="px-6 py-5"><Link href={`/diagnosis/${item.id}`} className="block"><strong className="block text-sm font-semibold text-[#171c1e] group-hover:text-[#007846]">{hostname(item.url)}</strong><span className="mt-1 block max-w-[360px] truncate text-xs text-[#768084]" title={item.url}>{item.url}</span></Link></td>
                <td className="px-4 py-5"><span className="inline-flex rounded-full bg-[#edf2ef] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.08em] text-[#52615a]">{item.run_mode === "individual" ? "Individual" : "Combined"}</span></td>
                <td className="px-4 py-5"><div className="flex flex-wrap gap-1.5">{visibleAgents.map((key) => <span key={key} className="rounded-full border border-[#e0e5e3] bg-white px-2.5 py-1 text-[10px] text-[#4e5955]">{diagnosisLabels[key] || key}</span>)}{item.selected_agents.length > visibleAgents.length && <span title={item.selected_agents.slice(2).map((key) => diagnosisLabels[key] || key).join(", ")} className="rounded-full border border-[#cfe0d8] px-2.5 py-1 text-[10px] font-semibold text-[#087849]">+{item.selected_agents.length - 2}</span>}</div></td>
                <td className="px-4 py-5 text-center text-sm font-semibold text-[#202725]">{item.finding_count}</td>
                <td className="px-4 py-5"><span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-semibold ${statusStyle(item.status)}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{statusLabel(item.status)}</span></td>
                <td className="whitespace-nowrap px-4 py-5"><span className="block text-xs font-semibold text-[#303739]">{created.date}</span><span className="mt-1 block text-[10px] text-[#7a8386]">{created.time}</span></td>
                <td className="px-6 py-5"><div className="flex items-center justify-end gap-2"><button type="button" disabled={deleting === item.id} onClick={() => remove(item)} className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-medium text-[#727b7e] transition hover:bg-red-50 hover:text-red-700 disabled:opacity-50"><TrashIcon className="h-4 w-4" />{deleting === item.id ? "Deleting…" : "Delete"}</button><Link href={`/diagnosis/${item.id}`} className="inline-flex items-center gap-2 whitespace-nowrap rounded-full bg-[#17201c] px-4 py-2.5 text-xs font-semibold text-white transition hover:bg-[#007846]">Open <ArrowIcon className="h-4 w-4" /></Link></div></td>
              </tr>;
            })}
          </tbody>
        </table>
      </div>

      {!sessions.length && !loading && <div className="border-t border-[#e3e7e5] px-6 py-16 text-center"><h2 className="text-lg font-semibold">No saved sessions yet</h2><p className="mt-2 text-sm text-[#747c80]">Run one or more agents on a URL and the session will appear here.</p></div>}

      <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-[#e0e5e2] bg-[#fafcfb] px-6 py-4">
        <p className="text-xs text-[#717b77]">Showing <strong className="text-[#26302c]">{firstItem}–{lastItem}</strong> of <strong className="text-[#26302c]">{history?.total || 0}</strong> sessions</p>
        <nav className="flex items-center gap-1.5" aria-label="Session pages">
          <button type="button" disabled={loading || currentPage === 1} onClick={() => loadPage(currentPage - 1)} className="rounded-full border border-[#d9dfdc] bg-white px-3.5 py-2 text-xs font-semibold text-[#4f5955] transition hover:border-[#aebbb5] disabled:cursor-not-allowed disabled:opacity-40">Previous</button>
          {pages.map((page, index) => <span key={page} className="contents">{index > 0 && page - pages[index - 1] > 1 && <span className="px-1 text-xs text-[#89918e]">…</span>}<button type="button" disabled={loading} aria-current={page === currentPage ? "page" : undefined} onClick={() => loadPage(page)} className={`grid h-8 min-w-8 place-items-center rounded-full px-2 text-xs font-semibold transition ${page === currentPage ? "bg-[#17201c] text-white" : "text-[#59635f] hover:bg-[#edf2ef]"}`}>{page}</button></span>)}
          <button type="button" disabled={loading || currentPage === totalPages} onClick={() => loadPage(currentPage + 1)} className="rounded-full border border-[#d9dfdc] bg-white px-3.5 py-2 text-xs font-semibold text-[#4f5955] transition hover:border-[#aebbb5] disabled:cursor-not-allowed disabled:opacity-40">Next</button>
        </nav>
      </footer>
    </section> : null}
  </div>;
}
