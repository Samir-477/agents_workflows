import Link from "next/link";

import { CheckIcon } from "@/components/icons";
import { SerpCompetitorForm } from "@/components/serp-competitor-form";

export function SerpCompetitorAgentPage() {
  return (
    <main>
      <section className="bg-[radial-gradient(circle_at_76%_20%,rgba(90,77,244,.10),transparent_34%),radial-gradient(circle_at_18%_18%,rgba(255,87,56,.08),transparent_28%)]">
        <div className="mx-auto max-w-[1280px] px-5 py-12 sm:px-8">
          <nav aria-label="Breadcrumb" className="text-sm text-[#777680]"><Link href="/agents">Agents</Link><span className="mx-2" aria-hidden="true">›</span>SERP &amp; Competitor Analysis</nav>
          <div className="mt-10 grid gap-10 lg:grid-cols-[1fr_520px] lg:gap-16">
            <div>
              <p className="font-mono text-xs font-semibold uppercase tracking-[.24em] text-[#d94221]">SEO intelligence</p>
              <h1 className="mt-4 text-5xl font-semibold tracking-[-.055em] sm:text-[58px]">SERP &amp; Competitor Analysis</h1>
              <p className="mt-6 text-xl font-semibold leading-8">See what the current search results reward, with evidence you can inspect.</p>
              <p className="mt-5 leading-7 text-[#686871]">Capture the top organic results, inspect selected pages safely, and surface intent, recurring topics, headings, schema and questions.</p>
              <ul className="mt-7 flex flex-wrap gap-5 text-sm font-semibold">{["Timestamped SERP", "Source URLs", "Page-level coverage", "Clear limitations"].map((item) => <li key={item} className="flex gap-2"><CheckIcon className="h-5 w-5 text-[#ff5738]" />{item}</li>)}</ul>
            </div>
            <SerpCompetitorForm />
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8">
        <h2 className="text-4xl font-semibold tracking-[-.04em]">Built for the next stage</h2>
        <p className="mt-4 max-w-4xl leading-8 text-[#686871]">Search snippets remain SERP evidence. Heading counts, schema and content depth appear only for pages the crawler successfully inspected. The resulting research can be reused by the content brief and optimizer.</p>
      </section>
    </main>
  );
}
