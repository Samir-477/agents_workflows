"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DownloadIcon, EyeIcon, PlusIcon, TrashIcon } from "@/components/icons";
import { deleteAudit, getAuditHistory, getAuditPdfUrl, type AuditResponse } from "@/lib/api";

const PAGE_SIZE = 10;

function statusStyle(status: string): string {
  if (status === "complete") return "bg-[#ecf8f1] text-[#24724f]";
  if (status === "failed") return "bg-[#fff0ee] text-[#c33d28]";
  return "bg-[#f2f0ff] text-[#4b3fca]";
}

export function AuditHistory() {
  const [audits, setAudits] = useState<AuditResponse[]>([]);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState("");
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadHistory = useCallback(async (selectedPage: number, search: string) => {
    setLoading(true);
    setError("");
    try {
      const response = await getAuditHistory(selectedPage, PAGE_SIZE, search);
      setAudits(response.items);
      setTotal(response.total);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load audit history.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => loadHistory(page, query), 250);
    return () => clearTimeout(timer);
  }, [loadHistory, page, query]);

  async function handleDelete(item: AuditResponse) {
    const confirmed = window.confirm(`Delete the audit for ${item.audit.requested_url}? This cannot be undone.`);
    if (!confirmed) return;
    setDeletingId(item.audit.id);
    try {
      await deleteAudit(item.audit.id);
      const nextPage = audits.length === 1 && page > 1 ? page - 1 : page;
      setPage(nextPage);
      await loadHistory(nextPage, query);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The audit could not be deleted.");
    } finally {
      setDeletingId("");
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#5549dd]">Saved runs</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em] text-[#171820]">Audit history</h1>
          <p className="mt-2 text-sm leading-6 text-[#686871]">Reopen past reports, review failed attempts, download results, or remove old runs.</p>
        </div>
        <Link href="/agents/seo-audit" className="inline-flex items-center gap-2 rounded-xl bg-[#ff5738] px-5 py-3 text-sm font-semibold text-white shadow-[0_8px_22px_rgba(255,87,56,0.18)] transition hover:bg-[#e9482b]"><PlusIcon className="h-4 w-4" />New audit</Link>
      </div>

      <div className="mt-8 rounded-[20px] border border-[#dfdedb] bg-white">
        <div className="flex flex-wrap items-center gap-3 border-b border-[#eceae6] p-4 sm:p-5">
          <label htmlFor="history-search" className="sr-only">Search audit history</label>
          <input id="history-search" type="search" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Search by website URL" className="h-11 min-w-[240px] flex-1 rounded-xl border border-[#deddd9] bg-[#fcfbf9] px-4 text-sm outline-none placeholder:text-[#9a999f] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
          <span className="text-xs text-[#85848b]">{total} saved audit{total === 1 ? "" : "s"}</span>
        </div>

        {error ? <p className="border-b border-red-100 bg-red-50 px-5 py-3 text-sm text-red-700">{error}</p> : null}
        {loading ? <div className="p-8 text-sm text-[#74737c]">Loading audit history…</div> : audits.length ? (
          <ul className="divide-y divide-[#eceae6]">
            {audits.map((item) => (
              <li key={item.audit.id} className="grid gap-4 p-5 transition hover:bg-[#fcfbf9] md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${statusStyle(item.audit.status)}`}>{item.audit.status}</span>
                    <span className="text-xs text-[#85848b]">{new Date(item.audit.created_at).toLocaleString()}</span>
                  </div>
                  <p className="mt-2 truncate font-semibold text-[#24252d]">{item.audit.requested_url}</p>
                  <p className="mt-1 text-xs text-[#85848b]">{item.pages_crawled} pages · {item.findings_count} findings · limit {item.audit.crawl_limit}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link href={`/agents/seo-audit/runs/${item.audit.id}`} className="inline-flex items-center gap-1.5 rounded-lg border border-[#deddd9] bg-white px-3 py-2 text-xs font-semibold text-[#34343d] transition hover:border-[#c9c5bd] hover:bg-[#f7f6f2]"><EyeIcon className="h-4 w-4 text-[#66656d]" />{item.report_available ? "Open report" : "View run"}</Link>
                  {item.report_available ? <a href={getAuditPdfUrl(item.audit.id)} download className="inline-flex items-center gap-1.5 rounded-lg border border-[#d9d5ff] bg-[#f4f2ff] px-3 py-2 text-xs font-semibold text-[#493dc0] transition hover:border-[#beb7ff] hover:bg-[#ebe8ff]"><DownloadIcon className="h-4 w-4" />PDF</a> : null}
                  <button type="button" onClick={() => handleDelete(item)} disabled={deletingId === item.audit.id} className="inline-flex items-center gap-1.5 rounded-lg border border-[#f0c7c0] bg-white px-3 py-2 text-xs font-semibold text-[#bd3b27] transition hover:border-[#e9a99f] hover:bg-[#fff4f2] disabled:cursor-wait disabled:opacity-60"><TrashIcon className="h-4 w-4" />{deletingId === item.audit.id ? "Deleting…" : "Delete"}</button>
                </div>
              </li>
            ))}
          </ul>
        ) : <p className="p-8 text-center text-sm text-[#74737c]">No matching audits found.</p>}

        <div className="flex items-center justify-between border-t border-[#eceae6] px-5 py-4">
          <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1 || loading} className="rounded-lg border border-[#deddd9] px-3 py-2 text-xs font-semibold text-[#44454e] disabled:opacity-40">Previous</button>
          <span className="text-xs text-[#777680]">Page {Math.min(page, totalPages)} of {totalPages}</span>
          <button type="button" onClick={() => setPage((value) => Math.min(totalPages, value + 1))} disabled={page >= totalPages || loading} className="rounded-lg border border-[#deddd9] px-3 py-2 text-xs font-semibold text-[#44454e] disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  );
}
