import Link from "next/link";

import { CheckIcon } from "@/components/icons";
import { SchemaPromptForm } from "@/components/schema-prompt-form";

const benefits = [
  ["Correct types chosen for you", "The agent maps plain-language page facts to supported schema.org types and explains every selection."],
  ["JSON-LD, compiled safely", "The model interprets facts; deterministic code owns the final JSON-LD structure and syntax check."],
  ["Placement guidance included", "Every block says whether it belongs on one page or once in the shared site template."],
  ["Mismatches flagged", "Invisible FAQs, unsupported ratings and missing facts become visible warnings instead of invented markup."],
  ["Completeness checks", "Required and useful recommended properties are listed before you publish."],
  ["Editable output", "Copy a formatted script block or inspect each entity separately before handing it to a developer."],
];
const steps = [
  ["Describe the page", "List the page type and facts visitors can see: name, address, price, author, dates, questions and answers."],
  ["Review generated JSON-LD", "See the selected types, rationale, missing properties and any content mismatches."],
  ["Validate the output", "Run the published markup through Google's Rich Results Test before launch."],
  ["Add it to the page", "Place the validated script in the page head or CMS using the included scope guidance."],
];
const outputs = [
  ["Local business schema", "Identity, address, phone, hours, geo and location details for visible business pages."],
  ["Article schema", "Headline, author, publisher, dates and image data for editorial content."],
  ["Product and offer schema", "Product details with supplied price, currency, availability and genuine ratings."],
  ["FAQ schema", "Question-and-answer markup for visible FAQ sections, with a note that Google limits FAQ rich-result display for most sites."],
  ["Organization schema", "Site-wide identity markup with legal name, logo, contact points and profiles."],
  ["Event and software schema", "Page-specific event or application entities with eligibility and placement notes."],
];
const faqs = [
  ["What is a schema markup generator?", "It creates machine-readable structured data from a plain-language description, without making you write JSON-LD syntax by hand."],
  ["What is JSON-LD?", "JSON-LD is a script block that describes page entities using schema.org vocabulary. Search engines recommend it because it stays separate from visible HTML."],
  ["Will schema guarantee rich results?", "No. Valid markup can make a page eligible, but search engines decide whether an enhanced result appears."],
  ["Which schema types can it generate?", "The current MVP supports Organization, LocalBusiness, MedicalBusiness, Product, Article, FAQPage, Event and SoftwareApplication, with related nested types."],
  ["Where does JSON-LD go?", "Conventionally in a script tag in the document head. The result explains whether each entity is site-wide or page-specific."],
  ["How do I know the markup is correct?", "The agent checks JSON syntax and common completeness rules. Always validate the final published page in a rich-results test before launch."],
  ["Can incorrect markup hurt?", "Misleading or hidden structured data can violate search guidelines. Only mark up facts users can actually see."],
  ["Should every page have schema?", "No. Use it where structured facts add meaning: organizations, locations, products, articles, events and genuine FAQ sections."],
  ["Can I edit the generated JSON-LD?", "Yes. The output is formatted and readable. Keep edits truthful, valid and synchronized with visible page content."],
  ["Does schema directly improve rankings?", "Structured data is not a direct ranking promise. Its value is clearer machine understanding and possible eligibility for enhanced display."],
  ["Can agencies use it for client work?", "Yes. Every run includes rationale, gaps and placement notes so developers and clients can review the implementation before publishing."],
];

const useCases = [
  ["Local business identity", "A clinic or retailer gets location markup with visible address, hours and contact details."],
  ["Publisher article templates", "An editorial team creates repeatable Article markup with per-post author and date fields."],
  ["E-commerce products", "A store compiles Product and Offer data that matches price, availability and reviews shown to shoppers."],
  ["Agency client delivery", "An SEO hands developers explained JSON-LD instead of an opaque copied snippet."],
  ["Visible FAQ sections", "A content team converts genuine on-page questions and answers into matching FAQPage data."],
  ["Upcoming events", "An organizer structures dates, venue and ticket information without turning opening hours into events."],
];

const sectors = [
  ["Local businesses", "Clinics, restaurants, trades and retailers with identity and location facts."],
  ["E-commerce", "Product, offer and genuine rating data for catalog pages."],
  ["Publishing and media", "Article, author, publisher and date information at content scale."],
  ["Events and education", "Dates, venues, organizers, offers and enrollment details."],
  ["Professional services", "Organization and service identity that matches real-world credentials."],
  ["Agencies", "Reviewable structured-data drafts with client-friendly rationale."],
];

const examples = [
  ["Physiotherapy clinic in Glasgow, open weekdays 8–6, Saturday mornings, with online booking.", "MedicalBusiness with LocalBusiness properties, structured hours, address guidance and missing-field notes."],
  ["Article schema for our company blog—one template, many authors.", "Article markup with author and publisher entities plus guidance to render per-post values."],
  ["Handmade ceramic mug, £24, in stock, with 40 reviews visibly shown.", "Product and Offer markup, a rating-visibility check, and exact supplied commercial facts."],
];

const comparison = [
  ["Choosing types", "Selected from the page description", "Vocabulary research or copied competitor markup"],
  ["Format", "One deterministic JSON-LD script", "Mixed generators or inline microdata"],
  ["Visible-content safety", "Mismatches flagged explicitly", "Easy to overlook hidden or misleading data"],
  ["Placement", "Scope guidance per entity", "Trial and error across templates"],
  ["Completeness", "Required and useful missing fields listed", "Errors discovered after publishing"],
];

const practices = [
  ["Always validate before publishing", "Test the final rendered page, not only a copied draft."],
  ["Mark up only what is visible", "Prices, ratings, FAQs and hours must match what visitors can see."],
  ["Keep markup synchronized", "Update JSON-LD whenever the page's facts change."],
  ["Expect eligibility, not guarantees", "Valid markup enables possibilities; it does not promise display."],
  ["Prefer complete main types", "One well-filled entity is more useful than many thin, speculative ones."],
  ["Use Organization once", "Keep identity markup site-wide and page entities on their relevant pages."],
];

function Grid({ items }: { items: string[][] }) { return <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">{items.map(([title, body]) => <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6 sm:p-7"><h3 className="text-lg font-semibold tracking-[-0.02em] text-[#171820]">{title}</h3><p className="mt-3 text-[15px] leading-7 text-[#686871]">{body}</p></article>)}</div>; }

export function SchemaAgentPage() {
  return <main>
    <section className="bg-[radial-gradient(circle_at_78%_18%,rgba(90,77,244,0.10),transparent_33%),radial-gradient(circle_at_18%_16%,rgba(255,87,56,0.08),transparent_28%)]"><div className="mx-auto max-w-[1280px] px-5 py-10 sm:px-8 sm:py-14">
      <nav aria-label="Breadcrumb" className="text-sm text-[#777680]"><Link href="/agents" className="hover:text-[#e94320]">Agents</Link><span className="mx-2">›</span><span>Schema Markup Generator</span></nav>
      <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_520px] lg:items-start lg:gap-16"><div>
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-[#d94221]">SEO agents</p>
        <h1 className="mt-4 max-w-3xl text-5xl font-semibold tracking-[-0.055em] sm:text-[58px] sm:leading-[1.02]">Schema Markup Generator</h1>
        <p className="mt-6 max-w-3xl text-xl font-semibold leading-8 tracking-[-0.02em] text-[#20212a] sm:text-[22px]">Describe a page, get valid JSON-LD structured data and clear instructions on where to put it.</p>
        <p className="mt-5 max-w-3xl text-base leading-7 text-[#686871]">Tell the agent what visitors can see. It chooses fitting types, compiles readable JSON-LD, flags missing or misleading properties, and saves the run for review.</p>
        <ul className="mt-7 flex flex-wrap gap-x-6 gap-y-3 text-sm font-semibold text-[#55555f]">{["JSON-LD blocks", "Type selection", "Mismatch checks", "Placement notes"].map((item) => <li key={item} className="inline-flex items-center gap-2"><CheckIcon className="h-5 w-5 text-[#ff5738]" />{item}</li>)}</ul>
      </div><SchemaPromptForm /></div>
    </div></section>
    <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">What is the Schema Markup Generator?</h2><div className="mt-6 max-w-4xl space-y-5 text-[16px] leading-8 text-[#62626c]"><p>Structured data tells machines what a page is, not only what it says. This agent turns visible page facts into the JSON-LD format search engines recommend.</p><p>It explains why each type fits, identifies properties worth adding, and refuses to silently turn unsupported or hidden content into markup. The output is a reviewable draft, not a promise of rankings or rich results.</p></div></section>
    <section className="border-y border-[#e8e6e1] bg-white"><div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Why use the generator</h2><Grid items={benefits} /></div></section>
    <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">How it works</h2><div className="mt-8 grid gap-5 md:grid-cols-2">{steps.map(([title, body], index) => <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6 sm:p-7"><span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#5a4df4] font-mono text-sm font-semibold text-white">{index + 1}</span><h3 className="mt-5 text-xl font-semibold">{title}</h3><p className="mt-3 leading-7 text-[#686871]">{body}</p></article>)}</div></section>
    <section className="border-y border-[#e8e6e1] bg-white"><div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">What the agent generates</h2><Grid items={outputs} /></div></section>
    <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Popular use cases</h2><Grid items={useCases} /></section>
    <section className="border-y border-[#e8e6e1] bg-white"><div className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Where it gets used</h2><Grid items={sectors} /></div></section>
    <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Examples</h2><div className="mt-8 space-y-5">{examples.map(([input, output]) => <article key={input} className="grid gap-6 rounded-[20px] border border-[#dfdedb] bg-white p-6 md:grid-cols-2 sm:p-7"><div><p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-[#85848b]">You provide</p><p className="mt-3 leading-7">{input}</p></div><div><p className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-[#85848b]">You get</p><p className="mt-3 leading-7 text-[#686871]">{output}</p></div></article>)}</div></section>
    <section className="border-y border-[#e8e6e1] bg-white"><div className="mx-auto max-w-[1180px] overflow-x-auto px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Schema Generator vs. the manual process</h2><table className="mt-8 w-full min-w-[760px] overflow-hidden rounded-[20px] border border-[#dfdedb] text-left"><thead className="bg-[#f6f4f0] font-mono text-xs uppercase tracking-[0.14em]"><tr><th className="p-4">Aspect</th><th className="p-4 text-[#d94221]">With the agent</th><th className="p-4">Manual process</th></tr></thead><tbody>{comparison.map(([aspect, agent, manual]) => <tr key={aspect} className="border-t border-[#e6e4df]"><th className="p-4 font-semibold">{aspect}</th><td className="p-4 text-[#44444c]">{agent}</td><td className="p-4 text-[#686871]">{manual}</td></tr>)}</tbody></table></div></section>
    <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Best practices</h2><div className="mt-8 grid gap-5 md:grid-cols-2">{practices.map(([title, body], index) => <article key={title} className="rounded-[20px] border border-[#dfdedb] bg-white p-6"><div className="flex gap-4"><span className="font-mono text-sm font-semibold text-[#d94221]">{String(index + 1).padStart(2, "0")}</span><div><h3 className="font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-[#686871]">{body}</p></div></div></article>)}</div></section>
    <section className="mx-auto max-w-[1180px] px-5 py-16 sm:px-8 sm:py-20"><h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Frequently asked questions</h2><div className="mt-8 divide-y divide-[#e6e4df] rounded-[20px] border border-[#dfdedb] bg-white px-6 sm:px-8">{faqs.map(([question, answer]) => <details key={question} className="group py-5"><summary className="flex cursor-pointer list-none items-center justify-between gap-5 font-semibold">{question}<span className="text-xl text-[#5549dd] group-open:rotate-45">+</span></summary><p className="mt-3 max-w-4xl pr-8 text-sm leading-7 text-[#686871]">{answer}</p></details>)}</div></section>
  </main>;
}
