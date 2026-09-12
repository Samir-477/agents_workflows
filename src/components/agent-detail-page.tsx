import Link from "next/link";

import { AgentRunPanel } from "@/components/agent-run-panel";
import { agents, type AgentDefinition } from "@/data/agents";
import { agentDetails, type DetailPair } from "@/data/agent-details";

function SectionTitle({ label, children }: { label:string; children:React.ReactNode }) {
  return <header><p className="text-[11px] font-semibold uppercase tracking-[.2em] text-[#747d81]">{label}</p><h2 className="mt-3 text-2xl font-semibold tracking-[-.04em] text-[#14191b]">{children}</h2></header>;
}
function NumberedList({items}:{items:DetailPair[]}) {
  return <ol className="mt-7 space-y-6">{items.map(([title,body],index)=><li key={title} className="grid grid-cols-[32px_1fr] gap-3"><span className="grid h-8 w-8 place-items-center rounded-full bg-[#f0f2f1] text-[11px] font-semibold">{index+1}</span><div><h3 className="text-sm font-semibold text-[#1b2022]">{title}</h3><p className="mt-1.5 text-sm leading-6 text-[#71797d]">{body}</p></div></li>)}</ol>;
}

export function AgentDetailPage({agent}:{agent:AgentDefinition}) {
  const detail=agentDetails[agent.slug];
  if(!detail) return null;
  const pairs=detail.pairWith.map(slug=>agents.find(item=>item.slug===slug)).filter((item):item is AgentDefinition=>Boolean(item));
  return <main className="bg-[#f8fafb]">
    <div className="mx-auto max-w-[1240px] px-5 pb-20 pt-12 sm:px-7 sm:pt-14">
      <Link href="/agents" className="text-xs text-[#727a7e] hover:text-[#007846]">← All agents</Link>
      <div className="mt-7 flex flex-wrap gap-2"><span className="rounded-full bg-[#dff2e5] px-2.5 py-1 text-[11px] font-semibold text-[#08663e]">{detail.discipline}</span><span className="rounded-full border border-[#dce1df] px-2.5 py-1 text-[11px] text-[#737b7f]">{detail.tier} tier</span>{detail.tags.map(tag=><span key={tag} className="rounded-full border border-[#dce1df] px-2.5 py-1 text-[11px] text-[#737b7f]">{tag}</span>)}</div>
      <h1 className="mt-6 max-w-4xl text-4xl font-semibold tracking-[-.05em] text-[#111719] sm:text-5xl">{agent.name}</h1><p className="mt-4 max-w-3xl text-lg leading-7 text-[#70787c]">{agent.description}</p>
      <div className="mt-9 grid max-w-[760px] overflow-hidden rounded-[22px] border border-[#dde2e0] bg-white sm:grid-cols-4"><div className="border-b p-4 sm:border-b-0 sm:border-r"><p className="text-[10px] uppercase tracking-[.14em] text-[#7c8488]">Input</p><p className="mt-1.5 text-sm font-semibold">Page URL</p></div><div className="border-b p-4 sm:border-b-0 sm:border-r"><p className="text-[10px] uppercase tracking-[.14em] text-[#7c8488]">Evidence</p><p className="mt-1.5 text-sm font-semibold">Saved capture</p></div><div className="border-b p-4 sm:border-b-0 sm:border-r"><p className="text-[10px] uppercase tracking-[.14em] text-[#7c8488]">Discipline</p><p className="mt-1.5 text-sm font-semibold">{detail.discipline.split(" · ")[0]}</p></div><div className="p-4"><p className="text-[10px] uppercase tracking-[.14em] text-[#7c8488]">Tier</p><p className="mt-1.5 text-sm font-semibold">{detail.tier}</p></div></div>

      <div className="mt-11 grid gap-10 lg:grid-cols-[minmax(0,760px)_380px] lg:items-start lg:justify-between">
        <div><p className="text-base leading-7 text-[#343b3d]">{detail.introduction}</p>
          <section className="mt-10 border-t border-[#e1e5e3] pt-10"><SectionTitle label="Method">How this agent works</SectionTitle><NumberedList items={detail.method}/></section>
          <section className="mt-10 border-t border-[#e1e5e3] pt-10"><SectionTitle label="Coverage">What the agent checks</SectionTitle><div className="mt-7 grid gap-4 sm:grid-cols-2">{detail.coverage.map(([title,body])=><article key={title} className="rounded-[20px] border border-[#dde2e0] bg-white p-5 shadow-[0_8px_24px_rgba(23,31,27,.05)]"><h3 className="text-sm font-semibold">{title}</h3><p className="mt-2 text-[13px] leading-5 text-[#747c80]">{body}</p></article>)}</div></section>
          <section className="mt-10 border-t border-[#e1e5e3] pt-10"><SectionTitle label="Weighting">Signals that change priority</SectionTitle><div className="mt-7 overflow-hidden rounded-[20px] border border-[#dde2e0] bg-white">{detail.weighting.map(([title,body])=><div key={title} className="grid gap-2 border-b border-[#e4e7e6] p-5 last:border-b-0 sm:grid-cols-[190px_1fr]"><h3 className="text-sm font-semibold">{title}</h3><p className="text-[13px] leading-5 text-[#747c80]">{body}</p></div>)}</div></section>
          <section className="mt-10 border-t border-[#e1e5e3] pt-10"><SectionTitle label="Output">What you get back</SectionTitle><div className="mt-7 flex flex-wrap gap-2.5">{detail.output.map(item=><span key={item} className="rounded-full border border-[#dce1df] bg-white px-3.5 py-2 text-[13px]">{item}</span>)}</div></section>
          <section className="mt-10 border-t border-[#e1e5e3] pt-10"><SectionTitle label="Questions">Before you run it</SectionTitle><div className="mt-7 space-y-6">{detail.questions.map(([question,answer])=><div key={question}><h3 className="text-sm font-semibold">{question}</h3><p className="mt-1.5 text-sm leading-6 text-[#747c80]">{answer}</p></div>)}</div></section>
          <section className="mt-10 border-t border-[#e1e5e3] pt-10"><SectionTitle label="Pair with">Other useful agents</SectionTitle><div className="mt-7 grid gap-4 sm:grid-cols-3">{pairs.map(item=><Link key={item.slug} href={`/agents/${item.slug}`} className="rounded-[20px] border border-[#dde2e0] bg-white p-5 shadow-[0_8px_24px_rgba(23,31,27,.05)] transition hover:-translate-y-0.5 hover:border-[#b8c7c0]"><h3 className="text-sm font-semibold">{item.name}</h3><p className="mt-2 text-[13px] leading-5 text-[#747c80]">{item.description}</p></Link>)}</div></section>
        </div><AgentRunPanel agent={agent}/>
      </div>
    </div><footer className="border-t border-[#e2e6e4]"><div className="mx-auto flex max-w-[1340px] flex-wrap justify-between gap-4 px-5 py-10 text-sm text-[#7b8387] sm:px-8"><p>Stellar Agents — evidence-backed SEO, AEO and content workflows.</p><Link href="/diagnosis" className="font-medium text-[#087849]">Run multiple agents →</Link></div></footer>
  </main>;
}
