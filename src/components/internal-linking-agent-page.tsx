import Link from "next/link";

import { CheckIcon, ClusterIcon } from "@/components/icons";
import { InternalLinkingForm } from "@/components/internal-linking-form";

const benefits = [
  ["Orphan candidates surfaced", "Find pages with no observed inbound links and name relevant pages that could link to them."],
  ["Contextual suggestions", "Recommend links from topical relationships and real source-page passages, not URL similarity alone."],
  ["Descriptive anchors", "Replace generic anchors such as ‘click here’ with options that explain the destination naturally."],
  ["Important pages first", "Use supplied business-critical URLs and observed link scarcity to rank the most useful fixes."],
  ["Placement evidence", "Show the source section and excerpt where each proposed link could fit."],
  ["Transparent confidence", "Expose observed facts, coverage limits and score factors so every recommendation can be reviewed."],
];

const faqs = [
  ["What does an internal linking tool do?", "It maps links between crawled pages, detects missing or weak connections, and returns specific source, target, anchor and placement recommendations."],
  ["What is an orphan page?", "A page with no internal links pointing to it. When crawl coverage is incomplete, this agent conservatively calls it an orphan candidate rather than claiming certainty."],
  ["How are links suggested?", "Code establishes the observed link graph. Topical similarity and source-page passages create candidates; optional AI refines only wording and reasoning and cannot alter crawl facts."],
  ["What makes good anchor text?", "It describes the destination in language that fits the surrounding sentence. Generic phrases such as ‘read more’ waste that descriptive opportunity."],
  ["Can it modify my site?", "No. This workflow is deliberately read-only. It produces a prioritized fix list for review before anyone edits a CMS or codebase."],
  ["Does it work with any CMS?", "Yes, provided the public HTML is crawlable. JavaScript-only, authenticated or bot-protected content may reduce coverage and will be identified as a limitation."],
];

export function InternalLinkingAgentPage() {
  return <main>
    <section className="bg-[radial-gradient(circle_at_78%_15%,rgba(90,77,244,0.10),transparent_32%),radial-gradient(circle_at_16%_15%,rgba(255,87,56,0.08),transparent_28%)]">
      <div className="mx-auto max-w-[1280px] px-5 py-10 sm:px-8 sm:py-14">
        <nav aria-label="Breadcrumb" className="text-sm text-[#777680]"><Link href="/agents" className="hover:text-[#e94320]">Agents</Link><span className="mx-2">›</span><span>Internal Linking Agent</span></nav>
        <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_520px] lg:items-start lg:gap-16">
          <div><div className="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-[#ebe9ff] text-[#5145dc]"><ClusterIcon className="h-6 w-6" /></div><p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-[#d94221]">SEO agents</p><h1 className="mt-4 text-5xl font-semibold tracking-[-0.055em] sm:text-[58px]">Internal Linking Agent</h1><p className="mt-6 max-w-3xl text-xl font-semibold leading-8 tracking-[-0.02em] text-[#20212a] sm:text-[22px]">Point it at your site and get a prioritized list of internal links worth reviewing.</p><p className="mt-5 max-w-3xl leading-7 text-[#686871]">Map the observed site graph, find isolated and underlinked pages, improve weak anchors, and receive source-to-target fixes grounded in actual page sections.</p><ul className="mt-7 flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-[#55555f]">{["Link recommendations", "Orphan candidates", "Anchor options", "Placement evidence"].map((item) => <li key={item} className="inline-flex items-center gap-2"><CheckIcon className="h-5 w-5 text-[#ff5738]" />{item}</li>)}</ul></div>
          <InternalLinkingForm />
        </div>
      </div>
    </section>
    <section className="mx-auto max-w-[1280px] px-5 py-14 sm:px-8 sm:py-20"><div className="max-w-3xl"><p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#5549dd]">From graph to fix list</p><h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">What the agent actually does</h2><p className="mt-5 leading-8 text-[#686871]">The crawler records links and their page locations. Deterministic analysis builds inbound and outbound counts, identifies gaps, and scores candidates. The language model may improve anchor and placement wording, but it cannot invent pages, links or crawl measurements.</p></div><div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">{benefits.map(([title, description], index) => <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6"><span className="font-mono text-xs font-semibold text-[#5549dd]">0{index + 1}</span><h3 className="mt-4 text-lg font-semibold">{title}</h3><p className="mt-3 leading-7 text-[#686871]">{description}</p></article>)}</div></section>
    <section className="border-y border-[#e9e7e2] bg-[#faf9f7]"><div className="mx-auto max-w-[1280px] px-5 py-14 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.035em]">How it works</h2><div className="mt-8 grid gap-5 md:grid-cols-4">{[["Enter a URL", "Set a safe page limit and optionally name important pages."], ["Map the graph", "Crawl public HTML and record unique and contextual links."], ["Rank the gaps", "Separate observed facts from topical opportunities and coverage limits."], ["Review fixes", "Use source, target, anchors, placement and reasoning to make edits."]].map(([title, description], index) => <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#5a4df4] font-mono text-sm font-semibold text-white">{index + 1}</span><h3 className="mt-5 font-semibold">{title}</h3><p className="mt-3 text-sm leading-6 text-[#686871]">{description}</p></article>)}</div></div></section>
    <section className="mx-auto max-w-[1000px] px-5 py-14 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.035em]">Frequently asked questions</h2><div className="mt-8 divide-y divide-[#e4e2dd] border-y border-[#e4e2dd]">{faqs.map(([question, answer]) => <details key={question} className="group py-5"><summary className="flex cursor-pointer list-none items-center justify-between gap-5 text-lg font-semibold"><span>{question}</span><span className="text-2xl font-normal text-[#5549dd] group-open:rotate-45">+</span></summary><p className="max-w-3xl pt-3 leading-7 text-[#686871]">{answer}</p></details>)}</div></section>
  </main>;
}
