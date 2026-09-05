"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { DownloadIcon, EyeIcon, PlusIcon, TrashIcon } from "@/components/icons";
import { deleteAudit, getAuditPdfUrl } from "@/lib/api";
import { getAgentRunHistory, type AgentFilter, type AgentRunSummary } from "@/lib/history-api";
import { deleteMetadataGeneration } from "@/lib/metadata-api";
import { deleteSchemaGeneration } from "@/lib/schema-api";
import { deleteKeywordClusterGeneration } from "@/lib/keyword-cluster-api";
import { deleteInternalLinkAudit } from "@/lib/internal-linking-api";
import { deleteContentBrief } from "@/lib/content-brief-api";
import { deleteVisibilityAudit } from "@/lib/ai-visibility-api";

const PAGE_SIZE = 10;

function statusStyle(status: string): string {
  if (status === "complete") return "bg-[#ecf8f1] text-[#24724f]";
  if (status === "failed") return "bg-[#fff0ee] text-[#c33d28]";
  return "bg-[#f2f0ff] text-[#4b3fca]";
}

function agentStyle(slug: string): string {
  if (slug === "seo-audit") return "bg-[#eef6ff] text-[#376b9d]";
  if (slug === "schema-markup") return "bg-[#f1efff] text-[#4b3fca]";
  if (slug === "keyword-cluster") return "bg-[#eaf7f1] text-[#267257]";
  if (slug === "internal-linking") return "bg-[#f2f0ff] text-[#4b3fca]";
  if (slug === "content-brief") return "bg-[#fff1ed] text-[#bd4a33]";
  if (slug === "ai-visibility") return "bg-[#eef0ff] text-[#4034bd]";
  return "bg-[#fff1ed] text-[#bd4a33]";
}

function runHref(item: AgentRunSummary): string {
  if (item.agent_slug === "seo-audit") return `/agents/seo-audit/runs/${item.id}`;
  if (item.agent_slug === "schema-markup") return `/agents/schema-markup/runs/${item.id}`;
  if (item.agent_slug === "keyword-cluster") return `/agents/keyword-cluster/runs/${item.id}`;
  if (item.agent_slug === "internal-linking") return `/agents/internal-linking/runs/${item.id}`;
  if (item.agent_slug === "content-brief") return `/agents/content-brief/runs/${item.id}`;
  if (item.agent_slug === "ai-visibility") return `/agents/ai-visibility/runs/${item.id}`;
  return `/agents/meta-title-description/runs/${item.id}`;
}

export function AuditHistory() {
  const [runs, setRuns] = useState<AgentRunSummary[]>([]);
  const [query, setQuery] = useState("");
  const [agent, setAgent] = useState<AgentFilter>("all");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState("");
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadHistory = useCallback(async (selectedPage: number, search: string, selectedAgent: AgentFilter) => {
    setLoading(true);
    setError("");
    try {
      const response = await getAgentRunHistory(selectedPage, PAGE_SIZE, search, selectedAgent);
      setRuns(response.items);
      setTotal(response.total);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load run history.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => loadHistory(page, query, agent), 250);
    return () => clearTimeout(timer);
  }, [agent, loadHistory, page, query]);

  async function handleDelete(item: AgentRunSummary) {
    if (!window.confirm(`Delete this ${item.agent_name} run? This cannot be undone.`)) return;
    setDeletingId(item.id);
    try {
      if (item.agent_slug === "seo-audit") await deleteAudit(item.id);
      else if (item.agent_slug === "schema-markup") await deleteSchemaGeneration(item.id);
      else if (item.agent_slug === "keyword-cluster") await deleteKeywordClusterGeneration(item.id);
      else if (item.agent_slug === "internal-linking") await deleteInternalLinkAudit(item.id);
      else if (item.agent_slug === "content-brief") await deleteContentBrief(item.id);
      else if (item.agent_slug === "ai-visibility") await deleteVisibilityAudit(item.id);
      else await deleteMetadataGeneration(item.id);
      const nextPage = runs.length === 1 && page > 1 ? page - 1 : page;
      setPage(nextPage);
      await loadHistory(nextPage, query, agent);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The run could not be deleted.");
    } finally {
      setDeletingId("");
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#5549dd]">Saved runs</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-[-0.045em] text-[#171820]">Agent history</h1>
          <p className="mt-2 text-sm leading-6 text-[#686871]">Review runs from every agent in one place, or narrow the list to a specific workflow.</p>
        </div>
        <Link href="/agents" className="inline-flex items-center gap-2 rounded-xl bg-[#ff5738] px-5 py-3 text-sm font-semibold text-white shadow-[0_8px_22px_rgba(255,87,56,0.18)] transition hover:bg-[#e9482b]"><PlusIcon className="h-4 w-4" />Start a run</Link>
      </div>

      <div className="mt-8 rounded-[20px] border border-[#dfdedb] bg-white">
        <div className="grid gap-3 border-b border-[#eceae6] p-4 sm:grid-cols-[minmax(0,1fr)_250px_auto] sm:p-5">
          <label htmlFor="history-search" className="sr-only">Search agent history</label>
          <input id="history-search" type="search" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Search URLs or generation prompts" className="h-11 min-w-0 rounded-xl border border-[#deddd9] bg-[#fcfbf9] px-4 text-sm outline-none placeholder:text-[#9a999f] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10" />
          <label htmlFor="agent-filter" className="sr-only">Filter by agent</label>
          <select id="agent-filter" value={agent} onChange={(event) => { setAgent(event.target.value as AgentFilter); setPage(1); }} className="h-11 rounded-xl border border-[#deddd9] bg-[#fcfbf9] px-4 text-sm font-medium text-[#44444c] outline-none focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10">
            <option value="all">All agents</option>
            <option value="seo-audit">SEO/AEO Audit Agent</option>
            <option value="meta-title-description">Meta Title & Description</option>
            <option value="schema-markup">Schema Markup Generator</option>
            <option value="keyword-cluster">Keyword Cluster Agent</option>
            <option value="internal-linking">Internal Linking Agent</option>
            <option value="content-brief">SEO Content Brief Agent</option>
            <option value="ai-visibility">AI Visibility Audit Agent</option>
          </select>
          <span className="self-center text-xs text-[#85848b] sm:text-right">{total} saved run{total === 1 ? "" : "s"}</span>
        </div>

        {error ? <p className="border-b border-red-100 bg-red-50 px-5 py-3 text-sm text-red-700">{error}</p> : null}
        {loading ? <div className="p-8 text-sm text-[#74737c]">Loading agent history…</div> : runs.length ? (
          <ul className="divide-y divide-[#eceae6]">
            {runs.map((item) => (
              <li key={`${item.agent_slug}-${item.id}`} className="grid gap-4 p-5 transition hover:bg-[#fcfbf9] md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${agentStyle(item.agent_slug)}`}>{item.agent_name}</span>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${statusStyle(item.status)}`}>{item.status}</span>
                    <span className="text-xs text-[#85848b]">{new Date(item.created_at).toLocaleString()}</span>
                  </div>
                  <p className="mt-2 line-clamp-2 font-semibold leading-6 text-[#24252d]">{item.title}</p>
                  <p className="mt-1 text-xs text-[#85848b]">{item.detail} · {item.progress}%</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link href={runHref(item)} className="inline-flex items-center gap-1.5 rounded-lg border border-[#deddd9] bg-white px-3 py-2 text-xs font-semibold text-[#34343d] transition hover:border-[#c9c5bd] hover:bg-[#f7f6f2]"><EyeIcon className="h-4 w-4 text-[#66656d]" />{item.result_available ? "Open result" : "View run"}</Link>
                  {item.agent_slug === "seo-audit" && item.result_available ? <a href={getAuditPdfUrl(item.id)} download className="inline-flex items-center gap-1.5 rounded-lg border border-[#d9d5ff] bg-[#f4f2ff] px-3 py-2 text-xs font-semibold text-[#493dc0] transition hover:border-[#beb7ff] hover:bg-[#ebe8ff]"><DownloadIcon className="h-4 w-4" />PDF</a> : null}
                  <button type="button" onClick={() => handleDelete(item)} disabled={deletingId === item.id} className="inline-flex items-center gap-1.5 rounded-lg border border-[#f0c7c0] bg-white px-3 py-2 text-xs font-semibold text-[#bd3b27] transition hover:border-[#e9a99f] hover:bg-[#fff4f2] disabled:cursor-wait disabled:opacity-60"><TrashIcon className="h-4 w-4" />{deletingId === item.id ? "Deleting…" : "Delete"}</button>
                </div>
              </li>
            ))}
          </ul>
        ) : <p className="p-8 text-center text-sm text-[#74737c]">No matching runs found.</p>}

        <div className="flex items-center justify-between border-t border-[#eceae6] px-5 py-4">
          <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1 || loading} className="rounded-lg border border-[#deddd9] px-3 py-2 text-xs font-semibold text-[#44454e] disabled:opacity-40">Previous</button>
          <span className="text-xs text-[#777680]">Page {Math.min(page, totalPages)} of {totalPages}</span>
          <button type="button" onClick={() => setPage((value) => Math.min(totalPages, value + 1))} disabled={page >= totalPages || loading} className="rounded-lg border border-[#deddd9] px-3 py-2 text-xs font-semibold text-[#44454e] disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  );
}
