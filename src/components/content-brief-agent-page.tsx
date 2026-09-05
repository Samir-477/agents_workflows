import Link from "next/link";

import { ContentBriefForm } from "@/components/content-brief-form";
import { CheckIcon } from "@/components/icons";

const benefits = [
  ["Intent before outline", "The brief explains what the reader is trying to accomplish and which format best serves that job."],
  ["Section notes writers can use", "Every H2 and H3 gets a purpose, talking points, questions, and a realistic word allowance."],
  ["Coverage with provenance", "Topics and entities are labelled as supplied or inferred, so recommendations never masquerade as measured SERP data."],
  ["Grounded internal links", "Only URLs you supply can enter the link plan, with anchor direction and placement guidance."],
  ["Conversion without derailment", "Calls to action appear only when your business goal or product context makes them defensible."],
  ["Validated handoff", "Code checks hierarchy, duplication, URL grounding, word budgets, and unsupported promises before the brief is saved."],
];
const steps = [
  ["State the assignment", "Provide the keyword and audience. Add your angle, goal, product, source notes, and existing URLs when available."],
  ["Build the strategy", "The agent infers intent, plans the format, and creates the outline, coverage, FAQs, links, and conversion notes."],
  ["Validate and repair", "Deterministic checks inspect the draft. Blocking problems trigger one bounded repair pass."],
  ["Hand it to a writer", "Use the saved brief with a freelancer, your team, or a drafting agent, with assumptions and verification checks intact."],
];
const outputs = [
  ["Intent summary", "Reader job, intent confidence, rationale, format, tone, and target length."],
  ["Heading outline", "An ordered H2/H3 plan with section purpose, talking points, questions, and word budgets."],
  ["Coverage checklist", "Topics, concepts, tools, entities, and standards the writer should address or verify."],
  ["FAQ guidance", "Editorial question suggestions with answer direction—not invented search-demand claims."],
  ["Internal link plan", "Exact supplied destinations with anchor and placement direction."],
  ["Writer checks", "A final handoff checklist plus visible assumptions, warnings, and evidence limitations."],
];
const faqs = [
  ["What does the agent need from me?", "A target keyword and audience. Optional angle, goal, product context, source notes, secondary terms, and existing page URLs make the brief sharper."],
  ["How is this different from an outline generator?", "The outline is only one part. This brief adds intent, section jobs, coverage, FAQs, internal links, conversion notes, assumptions, and validation."],
  ["Does it use live search results?", "Not in this MVP. Intent, questions, and entities are clearly marked as inferred from your assignment unless you provide research in the source notes."],
  ["Can it invent internal pages?", "No. The validator removes every internal-link target that is not an exact URL you supplied."],
  ["Can I use it with freelance writers?", "Yes. The output is structured as a self-contained handoff, including per-section instructions and a final writer checklist."],
  ["Does a brief guarantee rankings?", "No. It reduces avoidable planning failures, but competition, authority, execution, accuracy, and time still matter."],
  ["Can it plan a rewrite?", "Yes. Choose rewrite mode and include the existing page context. The brief adds preservation and verification checks without pretending it inspected the live page."],
  ["Can it brief a whole cluster?", "The current run produces one brief. Use the Keyword Cluster Agent to plan the architecture, then brief each page here; linked batch briefs are a later integration."],
  ["Are generated facts ready to publish?", "No factual claim should be published without review. The brief tells the writer what to cover and explicitly requires fact and source verification."],
  ["Is the result saved?", "Yes. Runs and validated results persist in the same history system as the other agents when Supabase is configured."],
];

function Grid({ items }: { items: string[][] }) { return <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">{items.map(([title, body]) => <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6 sm:p-7"><h3 className="text-lg font-semibold tracking-[-0.02em]">{title}</h3><p className="mt-3 text-[15px] leading-7 text-[#686871]">{body}</p></article>)}</div>; }

export function ContentBriefAgentPage() {
  return <main>
    <section className="bg-[radial-gradient(circle_at_78%_18%,rgba(90,77,244,0.10),transparent_33%),radial-gradient(circle_at_18%_16%,rgba(255,87,56,0.08),transparent_28%)]"><div className="mx-auto max-w-[1280px] px-5 py-10 sm:px-8 sm:py-14">
      <nav aria-label="Breadcrumb" className="text-sm text-[#777680]"><Link href="/agents" className="hover:text-[#e94320]">Agents</Link><span className="mx-2">›</span><span>SEO Content Brief Agent</span></nav>
      <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_520px] lg:items-start lg:gap-16"><div><p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-[#d94221]">Content agents</p><h1 className="mt-4 max-w-3xl text-5xl font-semibold tracking-[-0.055em] sm:text-[58px] sm:leading-[1.02]">SEO Content Brief Agent</h1><p className="mt-6 max-w-3xl text-xl font-semibold leading-8 tracking-[-0.02em] sm:text-[22px]">Give it a keyword and audience; get a brief a writer can execute without a second meeting.</p><p className="mt-5 max-w-3xl leading-7 text-[#686871]">Turn an assignment into intent, outline, coverage, FAQ, linking, and conversion guidance—then validate the handoff before it reaches a writer.</p><ul className="mt-7 flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-[#55555f]">{["Intent analysis", "Writer-ready outline", "Grounded links", "Quality checks"].map((item) => <li key={item} className="inline-flex items-center gap-2"><CheckIcon className="h-5 w-5 text-[#ff5738]" />{item}</li>)}</ul></div><ContentBriefForm /></div>
    </div></section>
    <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">What is the SEO Content Brief Agent?</h2><div className="mt-6 max-w-4xl space-y-5 text-[16px] leading-8 text-[#62626c]"><p>A useful brief tells a writer what the reader needs, what each section must accomplish, and which claims and links require care. A keyword plus a list of headings is not enough.</p><p>This agent creates that strategic layer while keeping its evidence boundary visible. Without a live SERP dataset, its intent, FAQ, and entity ideas are recommendations inferred from your assignment—not claims about what currently ranks.</p></div></section>
    <section className="border-y border-[#e8e6e1] bg-white"><div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Why use the agent</h2><Grid items={benefits} /></div></section>
    <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">How it works</h2><div className="mt-8 grid gap-5 md:grid-cols-2">{steps.map(([title, body], index) => <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6 sm:p-7"><span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#5a4df4] font-mono text-sm font-semibold text-white">{index + 1}</span><h3 className="mt-5 text-xl font-semibold">{title}</h3><p className="mt-3 leading-7 text-[#686871]">{body}</p></article>)}</div></section>
    <section className="border-y border-[#e8e6e1] bg-white"><div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">What the agent generates</h2><Grid items={outputs} /><div className="mt-8 rounded-[22px] border border-[#d7d2f2] bg-[#efedff] p-7"><p className="font-mono text-xs uppercase tracking-[0.2em] text-[#4b3fca]">Example output</p><h3 className="mt-3 text-2xl font-semibold">A brief for “email marketing for dentists”</h3><p className="mt-3 max-w-4xl leading-7 text-[#62626c]">Intent rationale, a practical seven-section outline, inferred coverage and FAQ ideas, only the supplied internal URLs, and a proportionate CTA—with every assumption and verification step retained.</p></div></div></section>
    <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Frequently asked questions</h2><div className="mt-8 divide-y divide-[#e6e4df] rounded-[20px] border border-[#dfdedb] bg-white px-6 sm:px-8">{faqs.map(([question, answer]) => <details key={question} className="group py-5"><summary className="flex cursor-pointer list-none items-center justify-between gap-5 font-semibold">{question}<span className="text-xl text-[#5549dd] group-open:rotate-45">+</span></summary><p className="mt-3 max-w-4xl pr-8 text-sm leading-7 text-[#686871]">{answer}</p></details>)}</div></section>
  </main>;
}
