import Link from "next/link";

import { CheckIcon } from "@/components/icons";
import { MetadataPromptForm } from "@/components/metadata-prompt-form";

const benefits = [
  ["Options, not a single guess", "Each page gets distinct title and description variants at different angles, so you choose instead of settling."],
  ["Length guidance on every option", "Exact character counts and practical range labels show what is likely to fit before a search engine truncates it."],
  ["Intent alignment notes", "Every option is tied to the informational, commercial, transactional or navigational intent it serves."],
  ["Page-type specific patterns", "Service, article, category, homepage and pricing pages receive different metadata shapes."],
  ["Brand placement handled deliberately", "The agent explains when the brand belongs in the title without pretending to know branded search demand."],
  ["Whole-site batches", "Describe up to ten pages together and receive a consistent set with cross-page duplication checks."],
];

const steps = [
  ["Describe the page or pages", "Give the topic, target term, audience, page type and any facts the copy may use."],
  ["Get options with notes", "Receive four titles and three descriptions per page, with counts, intent and rationale."],
  ["Review the recommendation", "See the strongest pairing, validation warnings and why it was selected."],
  ["Copy and apply", "Copy individual fields or the recommended pair into any CMS or SEO plugin."],
];

const features = [
  ["Character awareness", "Titles target roughly 50–60 characters and descriptions 140–160, with exact counts calculated by code."],
  ["Search intent matching", "The brief is interpreted through the page’s purpose instead of forcing every query into one formula."],
  ["Keyword placement strategy", "Confirmed target terms are placed naturally and remain distinct from keywords inferred by the agent."],
  ["Claim protection", "Prices, numbers and starting-from qualifiers are checked against the supplied brief before an option can be recommended."],
  ["Duplicate detection", "Variants and batch pages are compared so near-identical boilerplate is flagged and repaired."],
  ["Brand treatment options", "The agent includes or excludes the brand deliberately and explains the choice without unsupported assumptions."],
];

const faqs = [
  ["How long should a title tag and meta description be?", "Practical working ranges are about 50–60 characters for titles and 140–160 for descriptions. Search engines measure rendered width and may rewrite either field, so the range is guidance rather than a guarantee."],
  ["Will better metadata improve my rankings?", "Metadata is not a direct ranking promise. Clearer, more relevant snippets can help earn clicks from positions a page already holds."],
  ["Why does Google rewrite metadata?", "Common reasons include query mismatch, duplication, boilerplate and length. Distinct, intent-matched metadata reduces the risk but cannot prevent rewriting."],
  ["Can I brief several pages together?", "Yes. One prompt can describe up to ten pages, and the agent checks the resulting set for repetition and inconsistent patterns."],
];

function CardGrid({ items, columns = 3 }: { items: string[][]; columns?: 2 | 3 }) {
  return (
    <div className={`mt-8 grid gap-5 ${columns === 3 ? "md:grid-cols-2 lg:grid-cols-3" : "md:grid-cols-2"}`}>
      {items.map(([title, body]) => (
        <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6 sm:p-7">
          <h3 className="text-lg font-semibold tracking-[-0.02em] text-[#171820]">{title}</h3>
          <p className="mt-3 text-[15px] leading-7 text-[#686871]">{body}</p>
        </article>
      ))}
    </div>
  );
}

export function MetadataAgentPage() {
  return (
    <main>
      <section className="bg-[radial-gradient(circle_at_78%_18%,rgba(90,77,244,0.10),transparent_33%),radial-gradient(circle_at_18%_16%,rgba(255,87,56,0.08),transparent_28%)]">
        <div className="mx-auto max-w-[1280px] px-5 py-10 sm:px-8 sm:py-14">
          <nav aria-label="Breadcrumb" className="text-sm text-[#777680]">
            <Link href="/agents" className="hover:text-[#e94320]">Agents</Link>
            <span className="mx-2" aria-hidden="true">›</span>
            <span>Meta Title and Description Generator</span>
          </nav>
          <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_520px] lg:items-start lg:gap-16">
            <div>
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-[#d94221]">SEO agents</p>
              <h1 className="mt-4 max-w-3xl text-5xl font-semibold tracking-[-0.055em] sm:text-[58px] sm:leading-[1.02]">
                Meta Title and Description Generator
              </h1>
              <p className="mt-6 max-w-3xl text-xl font-semibold leading-8 tracking-[-0.02em] text-[#20212a] sm:text-[22px]">
                Turn a page brief into title tags and meta descriptions that earn the click.
              </p>
              <p className="mt-5 max-w-3xl text-base leading-7 text-[#686871]">
                Describe one page or a batch. Stellar returns multiple options with exact counts, intent notes, claim checks and a recommended pairing—without inventing facts you did not provide.
              </p>
              <ul className="mt-7 flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-[#55555f]">
                {["Four title options", "Three descriptions", "Length checks", "Intent notes"].map((item) => (
                  <li key={item} className="inline-flex items-center gap-2">
                    <CheckIcon className="h-5 w-5 text-[#ff5738]" /> {item}
                  </li>
                ))}
              </ul>
            </div>
            <MetadataPromptForm />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20">
        <div className="max-w-4xl">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#5549dd]">Purpose-built copy</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">What is the Meta Title and Description Generator?</h2>
          <div className="mt-6 space-y-5 text-[16px] leading-8 text-[#62626c]">
            <p>The title tag and meta description are the two lines that help a searcher decide whether to click your result. They are small fields, but they deserve the same care as a headline.</p>
            <p>This agent turns a natural-language brief into several reviewable options. It separates supplied facts from inferred context, measures every variant, and explains which pairing best matches the page and search intent.</p>
          </div>
        </div>
      </section>

      <section className="border-y border-[#e8e6e1] bg-white">
        <div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20">
          <h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Why use the generator</h2>
          <CardGrid items={benefits} />
        </div>
      </section>

      <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20">
        <h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">How it works</h2>
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          {steps.map(([title, body], index) => (
            <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6 sm:p-7">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#5a4df4] font-mono text-sm font-semibold text-white">{index + 1}</span>
              <h3 className="mt-5 text-xl font-semibold tracking-[-0.025em]">{title}</h3>
              <p className="mt-3 leading-7 text-[#686871]">{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-[#e8e6e1] bg-white">
        <div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20">
          <h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Generator features</h2>
          <CardGrid items={features} />
        </div>
      </section>

      <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20">
        <h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Frequently asked questions</h2>
        <div className="mt-8 divide-y divide-[#e6e4df] rounded-[20px] border border-[#dfdedb] bg-white px-6 sm:px-8">
          {faqs.map(([question, answer]) => (
            <details key={question} className="group py-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-5 font-semibold text-[#20212a]">
                {question}<span className="text-xl text-[#5549dd] group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 max-w-4xl pr-8 text-sm leading-7 text-[#686871]">{answer}</p>
            </details>
          ))}
        </div>
      </section>
    </main>
  );
}
