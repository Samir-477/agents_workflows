import Link from "next/link";

import { CheckIcon } from "@/components/icons";
import { LocalSEOForm } from "@/components/local-seo-form";

const benefits = [
  ["Facts before prose", "Business names, phones, addresses and hours are copied verbatim from your brief. Anything missing becomes a review task, never an invented detail."],
  ["One page per real area", "Service areas stay service areas and are never turned into fake offices. Physical branches keep their own address, phone and hours."],
  ["Local FAQs that fit the page", "Five to eight questions per area, grounded in the services and coverage you described."],
  ["Schema suggested, not assumed", "LocalBusiness or Service JSON-LD is drafted only when identity and location are confirmed, and withheld with a clear reason when they are not."],
  ["Duplicate-copy checks", "Introductions, service passages and FAQ answers are compared across areas with city names removed, so near-identical pages are flagged."],
  ["Keyless listing references", "Optionally match a named physical branch against public OpenStreetMap data — no API key, no billing, references only."],
];

const steps = [
  ["Describe the business and areas", "Give the business name, services, up to three real locations or coverage, phone, hours and any local evidence."],
  ["Establish the facts", "Shared details stay consistent; branch-specific address, phone and hours stay separate. Missing facts are held as review tasks."],
  ["Draft each area", "Every area gets an introduction, service sections, local FAQs, metadata, suggested JSON-LD and a call to action."],
  ["Review, edit and export", "Reopen a run from History, edit the copy JSON in place, and download the drafts. Nothing is published."],
];

const faqs = [
  ["Does it publish pages or create real forms?", "No. Every result is a reviewable draft marked needs-review. Domain publishing, visual styling and live lead forms are not part of this version."],
  ["How many areas can one run cover?", "Up to three distinct areas per run. Split larger sets into separate batches so each page gets grounded, area-specific copy."],
  ["Where does the OpenStreetMap lookup data come from?", "It resolves the area to a bounding box with public Nominatim, then queries public Overpass for a matching named place. Only an OSM id, name and link are kept — no listing content, reviews or photos."],
  ["What if my business is not on OpenStreetMap?", "A sole trader with no shopfront often has no OSM entry. The run still completes and adds a warning instead of a match."],
  ["Will this improve my local rankings?", "It produces grounded, distinct location pages — a foundation, not a ranking guarantee. Metadata length checks and duplicate-text similarity are heuristics."],
];

function CardGrid({ items }: { items: string[][] }) {
  return (
    <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
      {items.map(([title, body]) => (
        <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6 sm:p-7">
          <h3 className="text-lg font-semibold tracking-[-0.02em] text-[#171820]">{title}</h3>
          <p className="mt-3 text-[15px] leading-7 text-[#686871]">{body}</p>
        </article>
      ))}
    </div>
  );
}

export function LocalSEOAgentPage() {
  return (
    <main>
      <section className="bg-[radial-gradient(circle_at_78%_18%,rgba(90,77,244,0.10),transparent_33%),radial-gradient(circle_at_18%_16%,rgba(255,87,56,0.08),transparent_28%)]">
        <div className="mx-auto max-w-[1280px] px-5 py-10 sm:px-8 sm:py-14">
          <nav aria-label="Breadcrumb" className="text-sm text-[#777680]">
            <Link href="/agents" className="hover:text-[#e94320]">Agents</Link>
            <span className="mx-2" aria-hidden="true">›</span>
            <span>Local SEO Page Generator</span>
          </nav>
          <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_520px] lg:items-start lg:gap-16">
            <div>
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-[#d94221]">SEO agents</p>
              <h1 className="mt-4 max-w-3xl text-5xl font-semibold tracking-[-0.055em] sm:text-[58px] sm:leading-[1.02]">
                Local SEO Page Generator
              </h1>
              <p className="mt-6 max-w-3xl text-xl font-semibold leading-8 tracking-[-0.02em] text-[#20212a] sm:text-[22px]">
                Useful local pages start with real local facts.
              </p>
              <p className="mt-5 max-w-3xl text-base leading-7 text-[#686871]">
                Describe your business, services and up to three areas. Stellar drafts editable page copy, local FAQs, metadata, business details and suggested schema — with a clear task for anything only you can confirm.
              </p>
              <ul className="mt-7 flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-[#55555f]">
                {["Grounded page copy", "Local FAQs", "Schema suggestions", "Duplicate-copy checks"].map((item) => (
                  <li key={item} className="inline-flex items-center gap-2">
                    <CheckIcon className="h-5 w-5 text-[#ff5738]" /> {item}
                  </li>
                ))}
              </ul>
            </div>
            <LocalSEOForm />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20">
        <div className="max-w-4xl">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#5549dd]">Grounded local pages</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">What is the Local SEO Page Generator?</h2>
          <div className="mt-6 space-y-5 text-[16px] leading-8 text-[#62626c]">
            <p>Location pages fail when they are the same paragraph with the city name swapped. Search engines see the duplication, and visitors see nothing that proves you actually work in their area.</p>
            <p>This agent turns a short brief into one reviewable draft per area: an introduction, service sections, local FAQs, metadata and suggested JSON-LD. Supplied facts are copied exactly, missing facts become review tasks, and nothing is published.</p>
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
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#5a4df4] font-mono text-sm font-semibold text-white">
                {index + 1}
              </span>
              <h3 className="mt-5 text-xl font-semibold tracking-[-0.025em]">{title}</h3>
              <p className="mt-3 leading-7 text-[#686871]">{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-[#e8e6e1] bg-white">
        <div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20">
          <h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Frequently asked questions</h2>
          <div className="mt-8 divide-y divide-[#e6e4df] rounded-[20px] border border-[#dfdedb] bg-white px-6 sm:px-8">
            {faqs.map(([question, answer]) => (
              <details key={question} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-5 font-semibold text-[#20212a]">
                  {question}
                  <span className="text-xl text-[#5549dd] transition-transform group-open:rotate-45">+</span>
                </summary>
                <p className="mt-3 max-w-4xl pr-8 text-sm leading-7 text-[#686871]">{answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
