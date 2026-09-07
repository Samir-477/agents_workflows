import Link from "next/link";
import { SerpCompetitorRun } from "@/components/serp-competitor-run";

export default async function SerpRunPage({params}:{params:Promise<{runId:string}>}){const {runId}=await params;return <main className="reference-run-page"><div className="reference-run-inner"><nav aria-label="Breadcrumb" className="mb-8 text-sm text-[#777680]"><Link href="/agents">Agents</Link><span className="mx-2">›</span><Link href="/agents/serp-competitor">SERP &amp; Competitor Analysis</Link><span className="mx-2">›</span><span>Run</span></nav><SerpCompetitorRun runId={runId}/></div></main>}
