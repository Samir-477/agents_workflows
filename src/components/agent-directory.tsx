"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { ArrowIcon, ClusterIcon, GlobeIcon, SearchIcon, SparkIcon } from "@/components/icons";
import {
  agentCategories,
  agents,
  type AgentDefinition,
} from "@/data/agents";

function AgentCard({ agent }: { agent: AgentDefinition }) {
  const active = agent.status === "active";
  const icon = agent.slug === "seo-audit"
    ? <GlobeIcon className="h-5 w-5" />
    : agent.slug === "keyword-cluster"
      ? <ClusterIcon className="h-5 w-5" />
      : <SparkIcon className="h-5 w-5" />;
  return (
    <article className="flex min-h-[270px] flex-col rounded-[22px] border border-[#dfdedb] bg-white p-7 transition hover:-translate-y-0.5 hover:border-[#c9c7c2] hover:shadow-[0_18px_50px_rgba(26,26,36,0.07)]">
      <div className="flex items-start justify-between gap-4">
        <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#4437ad]">
          {agent.category}
        </p>
        <span
          className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
            active
              ? "bg-[#eceaff] text-[#493ddb]"
              : "bg-[#f4f2ee] text-[#77746d]"
          }`}
        >
          {active ? "Live" : "Coming soon"}
        </span>
      </div>
      <div className={`mt-5 flex h-11 w-11 items-center justify-center rounded-xl ${agent.slug === "keyword-cluster" ? "bg-[#ebe9ff] text-[#5145dc]" : "bg-[#fff0eb] text-[#e34a2b]"}`}>
        {icon}
      </div>
      <h3 className="mt-4 text-2xl font-semibold tracking-[-0.03em] text-[#11121a]">
        {agent.name}
      </h3>
      <p className="mt-3 flex-1 text-[16px] leading-7 text-[#62626c]">
        {agent.description}
      </p>
      {active ? (
        <Link
          href={`/agents/${agent.slug}`}
          className="mt-6 inline-flex w-fit items-center gap-2 rounded-md font-semibold text-[#e94320] hover:text-[#bd3317]"
        >
          Open agent <ArrowIcon className="h-5 w-5" />
        </Link>
      ) : (
        <span className="mt-6 inline-flex w-fit items-center gap-2 font-semibold text-[#9a9892]">
          In development
        </span>
      )}
    </article>
  );
}

export function AgentDirectory() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All agents");

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return agents.filter((agent) => {
      const matchesCategory = category === "All agents" || agent.category === category;
      const matchesQuery =
        !normalizedQuery ||
        `${agent.name} ${agent.description} ${agent.category}`
          .toLowerCase()
          .includes(normalizedQuery);
      return matchesCategory && matchesQuery;
    });
  }, [category, query]);

  return (
    <section aria-labelledby="all-agents-heading" className="mt-10 sm:mt-12">
      <h2 id="all-agents-heading" className="text-3xl font-semibold tracking-[-0.035em]">
        All agents
      </h2>
      <div className="relative mt-7">
        <SearchIcon className="pointer-events-none absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#898991]" />
        <label htmlFor="agent-search" className="sr-only">
          Search agents
        </label>
        <input
          id="agent-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder='Search agents—try "SEO" or "website"'
          className="h-15 w-full rounded-2xl border border-[#deddd9] bg-white pl-13 pr-5 text-[16px] outline-none transition placeholder:text-[#97969d] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10"
        />
      </div>

      <div className="mt-5 flex flex-wrap gap-2" aria-label="Filter agents by category">
        {agentCategories.map((item) => {
          const selected = item === category;
          return (
            <button
              key={item}
              type="button"
              aria-pressed={selected}
              onClick={() => setCategory(item)}
              className={`rounded-full border px-4 py-2 text-sm font-semibold transition ${
                selected
                  ? "border-[#ff5738] bg-[#fff2ed] text-[#d63b1c]"
                  : "border-[#deddd9] bg-white text-[#55555f] hover:border-[#bdbcb7]"
              }`}
            >
              {item}
            </button>
          );
        })}
      </div>

      <p className="mt-8 font-mono text-xs tracking-[0.12em] text-[#85848b]" aria-live="polite">
        {filtered.length} of {agents.length} agents
      </p>
      {filtered.length ? (
        <div className="mt-5 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((agent) => (
            <AgentCard key={agent.slug} agent={agent} />
          ))}
        </div>
      ) : (
        <div className="mt-5 rounded-2xl border border-dashed border-[#cfcdc7] px-6 py-14 text-center text-[#686871]">
          No agents match that search yet.
        </div>
      )}
    </section>
  );
}
