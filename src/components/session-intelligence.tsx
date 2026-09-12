"use client";

import { useMemo, useState } from "react";
import type { IntelligencePriority, ManagementReport } from "@/lib/diagnosis-api";

const engineStyle = {
  SEO: { dot: "bg-[#2f6ee5]", bar: "bg-[#2f6ee5]", soft: "bg-[#eef4ff]", text: "text-[#2559bd]" },
  AEO: { dot: "bg-[#7c3aed]", bar: "bg-[#7c3aed]", soft: "bg-[#f5efff]", text: "text-[#6a30c9]" },
  GEO: { dot: "bg-[#087849]", bar: "bg-[#087849]", soft: "bg-[#edf8f2]", text: "text-[#087849]" },
};

function Section({ eyebrow, title, copy, children }: { eyebrow: string; title: string; copy?: string; children: React.ReactNode }) {
  return <section className="border-t border-[#dfe4e2] py-10 first:border-0 first:pt-0">
    <p className="text-[10px] font-semibold uppercase tracking-[.2em] text-[#717b7f]">{eyebrow}</p>
    <h2 className="mt-2.5 text-[25px] font-semibold tracking-[-.04em] text-[#111719]">{title}</h2>
    {copy ? <p className="mt-2 max-w-3xl text-sm leading-6 text-[#6d777b]">{copy}</p> : null}
    <div className="mt-6">{children}</div>
  </section>;
}

function PriorityDetail({ item, onOpenAgent }: { item: IntelligencePriority; onOpenAgent: (agent: string) => void }) {
  const factors = item.score_factors;
  return <article className="self-start rounded-[20px] border border-[#dbe2de] bg-white p-6 shadow-[0_12px_32px_rgba(23,31,27,.06)]">
    <div className="flex flex-wrap items-center gap-2">
      <span className="rounded-full bg-[#121918] px-3 py-1 text-[10px] font-bold text-white">Rank {item.rank}</span>
      <span className={`rounded-full px-3 py-1 text-[10px] font-semibold ${engineStyle[item.engine].soft} ${engineStyle[item.engine].text}`}>{item.engine}</span>
      <span className="text-[10px] font-semibold uppercase tracking-[.14em] text-[#747e7a]">{item.priority} priority</span>
    </div>
    <h3 className="mt-5 text-xl font-semibold leading-7">{item.title}</h3>
    <p className="mt-3 text-sm leading-6 text-[#69736f]">{item.rationale}</p>
    <div className="mt-5 rounded-[16px] border border-emerald-200 bg-[#f2faf6] p-4">
      <p className="text-[10px] font-bold uppercase tracking-[.16em] text-[#087849]">Recommended change</p>
      <p className="mt-2 text-sm font-medium leading-6">{item.action}</p>
    </div>
    <dl className="mt-5 grid overflow-hidden rounded-[16px] border border-[#e0e5e2] sm:grid-cols-2">
      <div className="border-b p-4 sm:border-r"><dt className="text-[10px] uppercase tracking-[.14em] text-[#7a8480]">Impact</dt><dd className="mt-1 text-sm font-semibold">{item.impact}</dd></div>
      <div className="border-b p-4"><dt className="text-[10px] uppercase tracking-[.14em] text-[#7a8480]">Effort</dt><dd className="mt-1 text-sm font-semibold">{item.effort}</dd></div>
      <div className="p-4 sm:border-r"><dt className="text-[10px] uppercase tracking-[.14em] text-[#7a8480]">Owner</dt><dd className="mt-1 text-sm font-semibold">{item.owner}</dd></div>
      <div className="p-4"><dt className="text-[10px] uppercase tracking-[.14em] text-[#7a8480]">Delivery window</dt><dd className="mt-1 text-sm font-semibold">{item.timeframe}</dd></div>
    </dl>
    <div className="mt-5 space-y-4 border-t pt-5 text-xs leading-5 text-[#66716c]">
      <div><p className="font-semibold text-[#202824]">Verification</p><p className="mt-1">{item.done_when}</p></div>
      <div><p className="font-semibold text-[#202824]">Why it ranked here</p><p className="mt-1">Severity {factors.severity} + impact {factors.impact} + effort fit {factors.effort} + engine need {factors.engine_weakness} = <b>{item.priority_score}</b>.</p></div>
      <button onClick={() => onOpenAgent(item.agent)} className="font-semibold text-[#087849]">Open supporting {item.agent_label} report →</button>
    </div>
  </article>;
}

export function SessionIntelligenceView({ report, onOpenAgent, onRefresh, busy }: { report: ManagementReport; onOpenAgent: (agent: string) => void; onRefresh: () => void; busy: boolean }) {
  const intelligence = report.session_intelligence;
  const priorities = useMemo(() => intelligence?.priorities || [], [intelligence?.priorities]);
  const [selectedId, setSelectedId] = useState(priorities[0]?.id || "");
  const selected = priorities.find(item => item.id === selectedId) || priorities[0];
  const byId = useMemo(() => new Map(priorities.map(item => [item.id, item])), [priorities]);

  if (!intelligence) return <section className="rounded-[22px] border border-amber-200 bg-amber-50 p-7">
    <h2 className="text-xl font-semibold">Build this session’s intelligence layer</h2>
    <p className="mt-2 text-sm leading-6 text-amber-900/75">This saved report predates the decision layer. Its existing evidence can be reassembled without rerunning the agents.</p>
    <button disabled={busy} onClick={onRefresh} className="mt-5 rounded-full bg-[#121918] px-5 py-2.5 text-xs font-semibold text-white disabled:opacity-50">{busy ? "Building…" : "Build from saved results"}</button>
  </section>;

  const score = report.session_score?.score ?? 0;
  const top = priorities[0];
  const quick = intelligence.quick_win_ids.map(id => byId.get(id)).filter(Boolean) as IntelligencePriority[];
  const risks = intelligence.risk_ids.map(id => byId.get(id)).filter(Boolean) as IntelligencePriority[];
  const evidenceLinked = priorities.filter(item => item.finding_id).length;
  const rawBuckets = [
    { key: "now", label: "Now", window: "This week" },
    { key: "next", label: "Next", window: "This month" },
    { key: "later", label: "Later", window: "Next review cycle" },
  ] as const;
  const plannedBuckets = rawBuckets.map(bucket => ({ ...bucket, items: intelligence.delivery[bucket.key].map(id => byId.get(id)).filter(Boolean) as IntelligencePriority[] })).filter(bucket => bucket.items.length);

  return <div>
    <Section eyebrow="Executive intelligence" title="Decision brief" copy="A concise, evidence-bound view of the current position and the next management decision.">
      <div className="overflow-hidden rounded-[22px] bg-[#102d22] text-white shadow-[0_16px_38px_rgba(15,45,34,.12)] lg:grid lg:grid-cols-[1.35fr_.65fr]">
        <div className="p-6 sm:p-8">
          <p className="text-[10px] font-semibold uppercase tracking-[.18em] text-emerald-300">Recommended first move</p>
          <h3 className="mt-3 max-w-3xl text-2xl font-semibold leading-8 tracking-[-.035em]">{top ? top.action : "Keep this result as a dated baseline and rerun after the next material page change."}</h3>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-white/70">{top ? top.rationale : "No retained finding currently requires implementation."}</p>
          {top ? <div className="mt-6 grid gap-3 border-t border-white/15 pt-5 sm:grid-cols-2"><div><p className="text-[10px] uppercase tracking-[.14em] text-white/50">Accountable owner</p><p className="mt-1 text-sm font-semibold">{top.owner}</p></div><div><p className="text-[10px] uppercase tracking-[.14em] text-white/50">Verified when</p><p className="mt-1 text-sm leading-5 text-white/85">{top.done_when}</p></div></div> : null}
        </div>
        <dl className="grid grid-cols-2 border-t border-white/15 bg-white/[.04] lg:border-l lg:border-t-0">
          <div className="border-b border-r border-white/15 p-5"><dt className="text-[10px] uppercase tracking-[.14em] text-white/50">Session score</dt><dd className="mt-2 text-3xl font-semibold">{score}<span className="text-sm text-white/45">/100</span></dd></div>
          <div className="border-b border-white/15 p-5"><dt className="text-[10px] uppercase tracking-[.14em] text-white/50">Actions</dt><dd className="mt-2 text-3xl font-semibold">{priorities.length}</dd></div>
          <div className="border-r border-white/15 p-5"><dt className="text-[10px] uppercase tracking-[.14em] text-white/50">Evidence linked</dt><dd className="mt-2 text-3xl font-semibold">{evidenceLinked}</dd></div>
          <div className="p-5"><dt className="text-[10px] uppercase tracking-[.14em] text-white/50">Engines assessed</dt><dd className="mt-2 text-3xl font-semibold">{intelligence.engine_scores.length}<span className="text-sm text-white/45">/3</span></dd></div>
        </dl>
      </div>
    </Section>

    <Section eyebrow="Coverage" title="What this session assessed" copy="Scores reflect only the agents that participated. Unassessed engines remain outside the conclusion.">
      <div className="grid gap-4 md:grid-cols-3">
        {intelligence.engine_scores.map(item => { const style = engineStyle[item.engine]; return <button key={item.engine} onClick={() => onOpenAgent(item.weakest_agent)} className="rounded-[20px] border border-[#dce2df] bg-white p-5 text-left shadow-[0_9px_24px_rgba(23,31,27,.05)] transition hover:-translate-y-0.5"><div className="flex items-center justify-between"><span className="flex items-center gap-2 text-sm font-semibold"><i className={`h-2.5 w-2.5 rounded-full ${style.dot}`} />{item.engine} Engine</span><span className="text-[11px] text-[#77817d]">{item.agent_count} agent{item.agent_count === 1 ? "" : "s"}</span></div><div className="mt-5 flex items-end justify-between"><div><b className="text-4xl tracking-[-.05em]">{item.score}</b><span className="ml-1 text-xs text-[#7b8581]">/100</span></div><span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${style.soft} ${style.text}`}>{item.score_status.label}</span></div><div className="mt-4 h-2 overflow-hidden rounded-full bg-[#e8ecea]" role="progressbar" aria-label={`${item.engine} engine score`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={item.score}><div className={`h-full rounded-full ${style.bar}`} style={{ width: `${item.score}%` }} /></div><dl className="mt-5 space-y-2 border-t pt-4 text-xs"><div className="flex justify-between gap-3"><dt className="text-[#77817d]">Critical / warnings</dt><dd className="font-semibold">{item.critical_count} / {item.warning_count}</dd></div><div className="flex justify-between gap-3"><dt className="text-[#77817d]">Review first</dt><dd className="truncate font-semibold">{item.weakest_agent_label}</dd></div></dl></button>; })}
        {intelligence.missing_engines.map(engine => <article key={engine} className="rounded-[20px] border border-dashed border-[#d4dcda] bg-[#f5f7f6] p-5 text-[#7b8581]"><div className="flex items-center gap-2 text-sm font-semibold"><i className="h-2.5 w-2.5 rounded-full bg-[#c7cecb]" />{engine} Engine</div><p className="mt-5 text-2xl font-semibold text-[#6f7975]">Not assessed</p><p className="mt-3 text-xs leading-5">No {engine} agent participated, so this session makes no claim about that engine.</p></article>)}
      </div>
    </Section>

    <Section eyebrow="Opportunity orchestrator" title="Prioritized action queue" copy={`${priorities.length} action${priorities.length === 1 ? "" : "s"} ranked from retained evidence, delivery impact, effort and the weakness of the participating engine.`}>
      {priorities.length && selected ? <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(330px,.8fr)]"><PriorityDetail item={selected} onOpenAgent={onOpenAgent} /><div className="self-start overflow-hidden rounded-[20px] border border-[#dce2df] bg-white"><div className="hidden grid-cols-[52px_1fr_68px_68px_52px] border-b bg-[#f4f6f5] px-5 py-3 text-[10px] font-semibold uppercase tracking-[.14em] text-[#707a76] md:grid"><span>Rank</span><span>Issue · source</span><span>Impact</span><span>Effort</span><span>Fit</span></div>{priorities.map(item => <button key={item.id} onClick={() => setSelectedId(item.id)} className={`grid w-full gap-2 border-t px-5 py-4 text-left first:border-t-0 md:grid-cols-[52px_1fr_68px_68px_52px] md:items-center ${selected.id === item.id ? "bg-[#edf5f0]" : "hover:bg-[#f8faf9]"}`}><span className="text-xs font-bold">#{item.rank}</span><span><b className="block text-sm">{item.title}</b><small className={`mt-1 block text-[11px] ${engineStyle[item.engine].text}`}>{item.engine} · {item.agent_label}</small></span><span className="text-xs">{item.impact}</span><span className="text-xs">{item.effort}</span><span className="text-xs font-semibold">{item.priority_score}</span></button>)}</div></div> : <div className="rounded-[20px] border border-emerald-200 bg-[#f2faf6] p-6 text-sm text-[#38644f]">No retained action currently requires implementation.</div>}
    </Section>

    {quick.length || risks.length ? <Section eyebrow="Decision support" title="Quick wins and exposure" copy="Separate low-effort movement from issues whose cost grows when they are delayed."><div className={`grid gap-5 ${quick.length && risks.length ? "lg:grid-cols-2" : ""}`}>{quick.length ? <div><h3 className="text-lg font-semibold">Quick wins</h3><p className="mt-1 text-xs text-[#727c78]">Useful actions that the source agents classify as low effort.</p><div className="mt-4 grid gap-3 sm:grid-cols-2">{quick.map(item => <button key={item.id} onClick={() => setSelectedId(item.id)} className="rounded-[18px] border bg-white p-5 text-left"><span className={`text-[10px] font-bold uppercase tracking-[.14em] ${engineStyle[item.engine].text}`}>{item.engine} · Rank {item.rank}</span><b className="mt-2 block text-sm leading-5">{item.action}</b><span className="mt-3 block text-[11px] text-[#77817d]">Owner: {item.owner}</span></button>)}</div></div> : null}{risks.length ? <div><h3 className="text-lg font-semibold">Risk if delayed</h3><p className="mt-1 text-xs text-[#727c78]">Only critical and high-priority conditions appear here.</p><div className="mt-4 space-y-3">{risks.map(item => <button key={item.id} onClick={() => setSelectedId(item.id)} className="block w-full rounded-[18px] border border-red-100 bg-white p-5 text-left"><span className="text-[10px] font-bold uppercase tracking-[.14em] text-red-600">{item.priority} priority</span><b className="mt-2 block text-sm">{item.title}</b><span className="mt-2 block text-xs leading-5 text-[#727c78]">{item.risk_if_delayed}</span></button>)}</div></div> : null}</div></Section> : null}

    {top ? <Section eyebrow="Execution" title="Implementation and verification" copy="The recommended change, accountable handoff and acceptance test stay together."><div className="grid overflow-hidden rounded-[20px] border border-[#dce2df] bg-white md:grid-cols-3"><div className="border-b p-5 md:border-b-0 md:border-r"><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[#77817d]">1 · Implement</p><p className="mt-3 text-sm font-semibold leading-6">{top.action}</p></div><div className="border-b p-5 md:border-b-0 md:border-r"><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[#77817d]">2 · Hand off</p><p className="mt-3 text-sm font-semibold">{top.owner}</p><p className="mt-2 text-xs leading-5 text-[#727c78]">Target window: {top.timeframe}</p></div><div className="p-5"><p className="text-[10px] font-semibold uppercase tracking-[.14em] text-[#77817d]">3 · Verify</p><p className="mt-3 text-sm font-semibold leading-6">{top.done_when}</p></div></div></Section> : null}

    {plannedBuckets.length ? <Section eyebrow="Delivery" title="Sequenced plan" copy="Only delivery windows containing retained work are shown."><div className="grid gap-4 md:grid-cols-2">{plannedBuckets.flatMap(bucket => bucket.items.map(item => <button key={item.id} onClick={() => onOpenAgent(item.agent)} className="rounded-[20px] border border-[#dce2df] bg-white p-5 text-left transition hover:-translate-y-0.5 hover:border-[#b9c8c0]"><div className="flex items-center justify-between gap-4"><span className="font-semibold">{bucket.label}</span><span className="text-[11px] text-[#75807b]">{bucket.window}</span></div><span className="mt-5 block text-[10px] font-semibold uppercase tracking-[.12em] text-[#7b8581]">Rank {item.rank} · {item.engine}</span><b className="mt-2 block text-sm leading-6">{item.action}</b><span className="mt-3 block text-[11px] text-[#75807b]">{item.agent_label}</span></button>))}</div></Section> : null}

    <Section eyebrow="Governance" title="How to trust this decision" copy="The intelligence layer organizes saved agent evidence; it does not create new measurements or unsupported forecasts."><div className="grid gap-4 rounded-[20px] border border-[#dce2df] bg-white p-5 md:grid-cols-[1fr_auto] md:items-center"><div><p className="text-sm font-semibold">Transparent, reproducible prioritization</p><p className="mt-2 max-w-3xl text-xs leading-5 text-[#6f7975]">{intelligence.method}</p></div>{top ? <button onClick={() => onOpenAgent(top.agent)} className="rounded-full border border-[#cfd8d3] px-4 py-2.5 text-xs font-semibold text-[#087849]">Review source evidence →</button> : null}</div></Section>
  </div>;
}
