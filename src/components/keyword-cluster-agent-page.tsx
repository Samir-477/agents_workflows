import Link from "next/link";

import { CheckIcon, ClusterIcon } from "@/components/icons";
import { KeywordClusterForm } from "@/components/keyword-cluster-form";

const benefits = [
  ["One page per topic", "Group terms that one page can satisfy, so close variants stop competing with each other."],
  ["Intent-led clusters", "Separate informational, commercial, transactional and navigational needs before choosing a page type."],
  ["Pillar architecture", "Turn clusters into hub-and-spoke plans with pillar and supporting pages in a sensible build order."],
  ["Clean URL suggestions", "Give every recommended page a usable title and slug that can move directly into a sitemap."],
  ["Internal links planned", "Map links from pillars to supporting pages, back to hubs, and between relevant sibling pages."],
  ["Reasoning you can review", "Explain why terms belong together so an SEO or subject expert can confidently adjust the plan."],
];

const steps = [
  ["Paste your list", "Add one term per line. Search volumes are optional and can follow the keyword after a comma or tab."],
  ["Review the clusters", "The agent groups the full list by meaning and intent, then explains every page-level decision."],
  ["Use the page plan", "Prioritize pillars and supporting pages, adopt the suggested URLs, and build from the link map."],
];

const faqs = [
  ["What is keyword clustering?", "It is grouping keywords that should be answered by the same page. A raw list becomes a set of page-level decisions rather than one page per phrase."],
  ["How is this different from keyword research?", "Research finds the terms; clustering organizes them. Bring a list from any research source and this agent decides which terms belong on which pages."],
  ["What format does my list need?", "Paste one keyword per line. Search volume is optional: use formats such as ‘crm for freelancers, 1200’ or a tab-separated export."],
  ["How does the agent decide what belongs together?", "It combines semantic meaning with intent signals. Terms stay together when one page could satisfy them, even if they share very few words."],
  ["What is a pillar page?", "A pillar owns a broad topic. Narrower supporting pages deepen subtopics and link back to the pillar, creating a clear section architecture."],
  ["Will clustering improve rankings?", "No tool can guarantee rankings. Clustering helps prevent structural mistakes such as competing pages, shallow topic coverage and improvised internal linking."],
  ["Can I adjust the clusters?", "Yes. Treat the plan as an evidence-backed recommendation. Its reasoning makes it easier to merge, split or reassign groups using your market knowledge."],
  ["How many keywords can I paste?", "This version accepts up to 500 rows per run and analyzes them as one overall architecture. Duplicate terms are removed automatically."],
  ["Is this useful for an existing site?", "Yes. Mix the terms you already rank for with new targets to expose likely overlap risks and missing supporting topics. Confirm live cannibalization with search-performance data."],
];

export function KeywordClusterAgentPage() {
  return (
    <main>
      <section className="bg-[radial-gradient(circle_at_78%_15%,rgba(90,77,244,0.10),transparent_32%),radial-gradient(circle_at_16%_15%,rgba(255,87,56,0.08),transparent_28%)]">
        <div className="mx-auto max-w-[1280px] px-5 py-10 sm:px-8 sm:py-14">
          <nav aria-label="Breadcrumb" className="text-sm text-[#777680]"><Link href="/agents" className="hover:text-[#e94320]">Agents</Link><span className="mx-2">›</span><span>Keyword Cluster Agent</span></nav>
          <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_520px] lg:items-start lg:gap-16">
            <div>
              <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-[#ebe9ff] text-[#5145dc]"><ClusterIcon className="h-6 w-6" /></div>
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-[#d94221]">SEO agents</p>
              <h1 className="mt-4 max-w-3xl text-5xl font-semibold tracking-[-0.055em] sm:text-[58px]">Keyword Cluster Agent</h1>
              <p className="mt-6 max-w-3xl text-xl font-semibold leading-8 tracking-[-0.02em] text-[#20212a] sm:text-[22px]">Turn a raw keyword export into a page architecture—not another sorted spreadsheet.</p>
              <p className="mt-5 max-w-3xl text-base leading-7 text-[#686871]">Group terms by meaning and search intent, identify pillar and supporting pages, choose what to build first, and map the internal links that hold the section together.</p>
              <ul className="mt-7 flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-[#55555f]">
                {["Semantic clusters", "Intent labels", "Pillar page plan", "Internal link map"].map((item) => <li key={item} className="inline-flex items-center gap-2"><CheckIcon className="h-5 w-5 text-[#ff5738]" />{item}</li>)}
              </ul>
            </div>
            <KeywordClusterForm />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1280px] px-5 py-14 sm:px-8 sm:py-20">
        <div className="max-w-3xl"><p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#5549dd]">From inventory to strategy</p><h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">What is the Keyword Cluster Agent?</h2><p className="mt-5 text-base leading-8 text-[#686871]">Keyword research tools are excellent at producing lists. This agent answers the next question: what pages should the site actually have? It groups synonymous and closely related searches onto one page, separates materially different intent, and converts the result into a structure a content team can approve and build.</p></div>
        <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">{benefits.map(([title, description], index) => <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6"><span className="font-mono text-xs font-semibold text-[#5549dd]">0{index + 1}</span><h3 className="mt-4 text-lg font-semibold">{title}</h3><p className="mt-3 leading-7 text-[#686871]">{description}</p></article>)}</div>
      </section>

      <section className="border-y border-[#e9e7e2] bg-[#faf9f7]"><div className="mx-auto max-w-[1280px] px-5 py-14 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.035em]">How it works</h2><div className="mt-8 grid gap-5 md:grid-cols-3">{steps.map(([title, description], index) => <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#5a4df4] font-mono text-sm font-semibold text-white">{index + 1}</span><h3 className="mt-5 text-lg font-semibold">{title}</h3><p className="mt-3 leading-7 text-[#686871]">{description}</p></article>)}</div></div></section>

      <section className="mx-auto max-w-[1280px] px-5 py-14 sm:px-8 sm:py-20"><div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr] lg:gap-16"><div><p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#d94221]">Honest output</p><h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em]">A plan you can challenge</h2><p className="mt-4 leading-7 text-[#686871]">The output preserves every supplied keyword, shows duplicate cleanup, states its assumptions, and explains why each page exists. It identifies likely overlap—it does not claim proven cannibalization or promise rankings without search-performance evidence.</p></div><div className="rounded-[22px] border border-[#d7d2ff] bg-[#f2f0ff] p-7"><p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-[#4b3fca]">What you get</p><div className="mt-5 grid gap-3 sm:grid-cols-2">{["Topic clusters and primary terms", "Intent and recommended page type", "Pillar and supporting page plan", "Suggested titles and URL slugs", "Build priorities and supplied volumes", "Bidirectional internal-link map"].map((item) => <div key={item} className="flex gap-2 rounded-xl bg-white/75 px-4 py-3 text-sm font-medium"><CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-[#ff5738]" />{item}</div>)}</div></div></div></section>

      <section className="border-t border-[#e9e7e2]"><div className="mx-auto max-w-[1000px] px-5 py-14 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.035em]">Frequently asked questions</h2><div className="mt-8 divide-y divide-[#e4e2dd] border-y border-[#e4e2dd]">{faqs.map(([question, answer]) => <details key={question} className="group py-5"><summary className="flex cursor-pointer list-none items-center justify-between gap-5 text-lg font-semibold"><span>{question}</span><span className="text-2xl font-normal text-[#5549dd] group-open:rotate-45">+</span></summary><p className="max-w-3xl pt-3 leading-7 text-[#686871]">{answer}</p></details>)}</div></div></section>
    </main>
  );
}
