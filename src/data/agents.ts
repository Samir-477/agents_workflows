export type AgentStatus = "active" | "coming-soon";

export interface AgentDefinition {
  slug: string;
  category: string;
  name: string;
  description: string;
  status: AgentStatus;
  accent: "orange" | "indigo";
}

export const agents: AgentDefinition[] = [
  {
    slug: "seo-audit",
    category: "SEO Agents",
    name: "SEO Audit Agent",
    description:
      "A plain-English, prioritized audit of your website's search health—not a wall of crawl data.",
    status: "active",
    accent: "indigo",
  },
  {
    slug: "meta-title-description",
    category: "SEO Agents",
    name: "Meta Title and Description Generator",
    description:
      "Turn natural-language page briefs into measured, intent-matched metadata options with a clear recommendation.",
    status: "active",
    accent: "orange",
  },
  {
    slug: "schema-markup",
    category: "SEO Agents",
    name: "Schema Markup Agent",
    description:
      "Generate structured data that matches the visible content and entities on a page.",
    status: "coming-soon",
    accent: "orange",
  },
  {
    slug: "internal-linking",
    category: "SEO Agents",
    name: "Internal Linking Agent",
    description:
      "Find high-value internal linking opportunities and explain exactly where to add them.",
    status: "coming-soon",
    accent: "indigo",
  },
  {
    slug: "content-brief",
    category: "Content Agents",
    name: "SEO Content Brief Agent",
    description:
      "Turn a topic and audience into a structured, evidence-led brief a writer can execute.",
    status: "coming-soon",
    accent: "orange",
  },
  {
    slug: "accessibility-audit",
    category: "Website Agents",
    name: "Accessibility Audit Agent",
    description:
      "Identify common accessibility barriers and return a prioritized remediation plan.",
    status: "coming-soon",
    accent: "indigo",
  },
  {
    slug: "performance-audit",
    category: "Website Agents",
    name: "Website Performance Agent",
    description:
      "Explain what is slowing a website down and rank improvements by impact and effort.",
    status: "coming-soon",
    accent: "orange",
  },
];

export const agentCategories = [
  "All agents",
  ...Array.from(new Set(agents.map((agent) => agent.category))),
];

export function getAgent(slug: string): AgentDefinition | undefined {
  return agents.find((agent) => agent.slug === slug);
}
