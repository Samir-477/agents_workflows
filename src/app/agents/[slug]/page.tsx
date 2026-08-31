import Link from "next/link";
import { notFound } from "next/navigation";

import { AuditForm } from "@/components/audit-form";
import { CheckIcon } from "@/components/icons";
import { MetadataAgentPage } from "@/components/metadata-agent-page";
import { agents, getAgent } from "@/data/agents";

export function generateStaticParams() {
  return agents.map((agent) => ({ slug: agent.slug }));
}

export default async function AgentPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const agent = getAgent(slug);
  if (!agent) notFound();

  if (slug === "meta-title-description") {
    return <MetadataAgentPage />;
  }

  if (agent.status !== "active") {
    return (
      <main className="mx-auto max-w-[900px] px-5 py-20 text-center sm:px-8">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-[#5549dd]">{agent.category}</p>
        <h1 className="mt-4 text-5xl font-semibold tracking-[-0.05em]">{agent.name}</h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-[#686871]">{agent.description}</p>
        <span className="mt-8 inline-flex rounded-full bg-[#f0eee9] px-4 py-2 text-sm font-semibold text-[#77746d]">Coming soon</span>
        <div><Link href="/agents" className="mt-8 inline-flex text-sm font-semibold text-[#e94320]">← Back to all agents</Link></div>
      </main>
    );
  }

  return (
    <main>
      <section className="bg-[radial-gradient(circle_at_76%_20%,rgba(90,77,244,0.10),transparent_34%),radial-gradient(circle_at_18%_18%,rgba(255,87,56,0.08),transparent_28%)]">
        <div className="mx-auto max-w-[1280px] px-5 py-10 sm:px-8 sm:py-14">
          <nav aria-label="Breadcrumb" className="text-sm text-[#777680]">
            <Link href="/agents" className="hover:text-[#e94320]">Agents</Link><span className="mx-2" aria-hidden="true">›</span><span>SEO Audit Agent</span>
          </nav>
          <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_520px] lg:items-start lg:gap-16">
            <div>
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-[#d94221]">SEO agents</p>
              <h1 className="mt-4 text-5xl font-semibold tracking-[-0.055em] sm:text-[58px]">SEO Audit Agent</h1>
              <p className="mt-6 max-w-3xl text-xl font-semibold leading-8 tracking-[-0.02em] text-[#20212a] sm:text-[22px]">A plain-English, prioritized audit of your website&apos;s search health — not a wall of crawl data.</p>
              <p className="mt-5 max-w-3xl text-base leading-7 text-[#686871]">Enter a URL and Stellar checks crawling, metadata, headings, structured data, internal links and content coverage. Findings are grouped by severity, explained clearly, and paired with a practical fix.</p>
              <ul className="mt-7 flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-[#55555f]">
                {["Prioritized report", "Severity grouping", "Fix guidance", "Schema checks"].map((item) => <li key={item} className="inline-flex items-center gap-2"><CheckIcon className="h-5 w-5 text-[#ff5738]" /> {item}</li>)}
              </ul>
            </div>
            <AuditForm />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1280px] px-5 py-14 sm:px-8 sm:py-20">
        <div className="max-w-2xl">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#5549dd]">How it helps</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em]">What is the SEO Audit Agent?</h2>
          <p className="mt-3 leading-7 text-[#686871]">It turns a representative website crawl into one readable work queue: what is wrong, why it matters, which pages are affected, and what your team should do next.</p>
        </div>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {[
            ["Crawl and indexation", "Status codes, robots signals, canonicals, redirects and crawl coverage."],
            ["Page quality", "Titles, descriptions, headings, content depth, images and structured data."],
            ["Priority and action", "Severity, confidence, affected pages, quick wins and practical fixes."],
          ].map(([title, description], index) => <article key={title} className="rounded-2xl border border-[#dfdedb] bg-white p-6"><span className="font-mono text-xs font-semibold text-[#5549dd]">0{index + 1}</span><h3 className="mt-4 text-lg font-semibold">{title}</h3><p className="mt-3 leading-7 text-[#686871]">{description}</p></article>)}
        </div>
      </section>
    </main>
  );
}
