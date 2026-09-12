import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { AgentDetailPage } from "@/components/agent-detail-page";
import { agents, getAgent } from "@/data/agents";

export function generateStaticParams() {
  return agents.map(agent => ({ slug: agent.slug }));
}

export default async function AgentPage({ params }: { params: Promise<{ slug:string }> }) {
  const {slug}=await params;
  if(slug==="resort-orchestrator") redirect("/diagnosis");
  const agent=getAgent(slug);
  if(!agent) notFound();
  if(agent.status==="active") return <AgentDetailPage agent={agent}/>;
  return <main className="min-h-[calc(100vh-68px)] bg-[#f8fafb]"><div className="mx-auto max-w-[820px] px-5 py-20 text-center sm:px-7"><p className="text-[11px] font-semibold uppercase tracking-[.2em] text-[#747d81]">{agent.category}</p><h1 className="mt-5 text-4xl font-semibold tracking-[-.05em]">{agent.name}</h1><p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-[#70787c]">{agent.description}</p><span className="mt-7 inline-flex rounded-full bg-[#e9eeeb] px-3.5 py-1.5 text-xs font-semibold text-[#65706b]">Planned</span><div><Link href="/agents" className="mt-8 inline-flex text-sm font-medium text-[#087849]">← Back to all agents</Link></div></div></main>;
}
