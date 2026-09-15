import Link from "next/link";

import { AgentRunPanel } from "@/components/agent-run-panel";
import type { AgentDefinition } from "@/data/agents";

const stages = [
  ["01", "Resolve the resort", "Confirm the property, destination and page role from the URL, page title, headings and structured identity signals."],
  ["02", "Collect question evidence", "Reuse captured page questions and enrich them with a dated Google question sample when the provider is available."],
  ["03", "Consolidate and classify", "Remove exact duplicates, then assign topic, customer intent, journey stage, provenance and confidence."],
  ["04", "Map page coverage", "Mark each question explicit, implicit, absent or unknown from the captured page evidence."],
  ["05", "Connect the engines", "Prepare a search-theme handoff for SEO, an answer-quality handoff for AEO and a prompt seed for GEO."],
];

const outputRows = [
  ["Question landscape", "A ranked, paginated inventory with evidence provenance and confidence."],
  ["Coverage map", "Clear separation between direct coverage, indirect coverage and unanswered questions."],
  ["Topic clusters", "Decision, planning, amenity and booking questions grouped for practical ownership."],
  ["Action plan", "Evidence-linked next steps, delivery windows and repeatable completion checks."],
];

const handoffs = [
  ["SEO", "Validate demand and assign the right page", "Question themes become inputs for keyword research, page-role decisions and internal linking."],
  ["AEO", "Assess and improve the answer", "Observed gaps move to answer completeness, FAQ coverage and structured-answer workflows."],
  ["GEO", "Test visibility with a grounded prompt", "Questions become prompt seeds for separate mention and citation measurement."],
];

export function QuestionDiscoveryAgentPage({agent}:{agent:AgentDefinition}) {
  return <main className="bg-[#f8fafb] text-[#111719]">
    <section className="border-b border-[#e1e6e3] bg-[radial-gradient(ellipse_at_72%_0%,rgba(216,238,226,.8),transparent_50%)]">
      <div className="mx-auto max-w-[1240px] px-5 pb-16 pt-12 sm:px-7 sm:pb-20 sm:pt-16">
        <Link href="/agents" className="text-xs font-medium text-[#68736e] hover:text-[#007846]">← All agents</Link>
        <div className="mt-9 grid gap-10 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-start">
          <div className="max-w-[760px]"><div className="flex flex-wrap gap-2"><span className="rounded-full bg-[#eee8ff] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.13em] text-[#6d36d9]">AEO · Core agent</span><span className="rounded-full border bg-white px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[.13em] text-[#65706b]">Runnable now</span></div>
            <p className="mt-7 text-[11px] font-semibold uppercase tracking-[.22em] text-[#707b76]">Discover what customers need answered</p>
            <h1 className="mt-4 text-4xl font-semibold leading-[1.05] tracking-[-.055em] sm:text-6xl">Question Discovery Agent</h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[#64706b]">Turn one Sterling resort URL into a defensible map of customer questions—where each question came from, whether the page covers it, and which engine should act next.</p>
            <div className="mt-9 grid max-w-[760px] overflow-hidden rounded-[20px] border border-[#dce3df] bg-white sm:grid-cols-4"><div className="border-b p-4 sm:border-b-0 sm:border-r"><p className="text-[10px] uppercase tracking-[.14em] text-[#7b8580]">Input</p><p className="mt-2 text-sm font-semibold">Resort URL</p></div><div className="border-b p-4 sm:border-b-0 sm:border-r"><p className="text-[10px] uppercase tracking-[.14em] text-[#7b8580]">Primary score</p><p className="mt-2 text-sm font-semibold">Question coverage</p></div><div className="border-b p-4 sm:border-b-0 sm:border-r"><p className="text-[10px] uppercase tracking-[.14em] text-[#7b8580]">Evidence</p><p className="mt-2 text-sm font-semibold">Page + search</p></div><div className="p-4"><p className="text-[10px] uppercase tracking-[.14em] text-[#7b8580]">Handoffs</p><p className="mt-2 text-sm font-semibold">SEO · AEO · GEO</p></div></div>
          </div>
          <AgentRunPanel agent={agent}/>
        </div>
      </div>
    </section>

    <section className="mx-auto max-w-[1240px] px-5 py-16 sm:px-7 sm:py-20"><p className="text-[11px] font-semibold uppercase tracking-[.2em] text-[#707b76]">Pipeline</p><h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-[-.045em] sm:text-4xl">From a resort page to a connected question system</h2><p className="mt-4 max-w-3xl text-base leading-7 text-[#69746f]">The workflow preserves the difference between evidence and ideas. Search-result questions are observed; the resort framework fills planning blind spots and stays visibly labelled as inferred.</p><ol className="mt-10 grid overflow-hidden rounded-[22px] border border-[#dce2df] bg-white lg:grid-cols-5">{stages.map(([number,title,description],index)=><li key={number} className="border-b p-5 last:border-b-0 lg:border-b-0 lg:border-r lg:last:border-r-0"><span className="text-[11px] font-semibold text-[#7c3aed]">{number}</span><h3 className="mt-5 text-base font-semibold">{title}</h3><p className="mt-2 text-[13px] leading-6 text-[#707a75]">{description}</p>{index<stages.length-1?<span className="mt-5 hidden text-[#a9b2ae] lg:block">→</span>:null}</li>)}</ol></section>

    <section className="border-y border-[#e1e6e3] bg-white"><div className="mx-auto grid max-w-[1240px] gap-12 px-5 py-16 sm:px-7 sm:py-20 lg:grid-cols-[.85fr_1.15fr]"><div><p className="text-[11px] font-semibold uppercase tracking-[.2em] text-[#707b76]">Report contract</p><h2 className="mt-3 text-3xl font-semibold tracking-[-.045em]">A report a team can actually use</h2><p className="mt-4 text-base leading-7 text-[#69746f]">The output uses the same score, findings, evidence, actions, verification, trace and methodology structure as every agent report in the session.</p><div className="mt-7 rounded-[18px] border border-[#bde8d0] bg-[#f0faf4] p-5"><p className="text-[10px] font-bold uppercase tracking-[.16em] text-[#087849]">Two scores, two meanings</p><p className="mt-3 text-sm leading-6"><b>Question Coverage</b> measures how clearly the captured page addresses the assessed set. <b>Discovery Confidence</b> measures the strength of the question sources. They are never blended into a demand metric.</p></div></div><div className="overflow-hidden rounded-[22px] border border-[#dce2df]">{outputRows.map(([title,description],index)=><div key={title} className="grid gap-2 border-b p-5 last:border-b-0 sm:grid-cols-[180px_1fr]"><div className="flex items-center gap-3"><span className="grid h-7 w-7 place-items-center rounded-full bg-[#121918] text-[10px] font-semibold text-white">{index+1}</span><h3 className="text-sm font-semibold">{title}</h3></div><p className="text-sm leading-6 text-[#6c7671]">{description}</p></div>)}</div></div></section>

    <section className="mx-auto max-w-[1240px] px-5 py-16 sm:px-7 sm:py-20"><p className="text-[11px] font-semibold uppercase tracking-[.2em] text-[#707b76]">Connected intelligence</p><h2 className="mt-3 text-3xl font-semibold tracking-[-.045em]">One question, three accountable handoffs</h2><div className="mt-9 grid gap-4 lg:grid-cols-3">{handoffs.map(([engine,title,description])=><article key={engine} className="rounded-[22px] border border-[#dce2df] bg-white p-6 shadow-[0_10px_28px_rgba(23,31,27,.05)]"><span className={`inline-flex rounded-full px-3 py-1 text-[10px] font-bold ${engine==="SEO"?"bg-blue-50 text-blue-700":engine==="AEO"?"bg-purple-50 text-purple-700":"bg-emerald-50 text-emerald-700"}`}>{engine}</span><h3 className="mt-5 text-lg font-semibold">{title}</h3><p className="mt-3 text-sm leading-6 text-[#69746f]">{description}</p></article>)}</div><div className="mt-10 flex flex-wrap items-center gap-5 border-t pt-8"><Link href="/diagnosis" className="rounded-full bg-[#007846] px-6 py-3 text-sm font-semibold text-white hover:bg-[#00683d]">Run with other agents</Link><Link href="/agents/history" className="text-sm font-semibold text-[#087849]">Open saved sessions →</Link></div></section>
  </main>;
}
