import Link from "next/link";
import { ContentOptimizerRunView } from "@/components/content-optimizer-run";

export default async function ContentOptimizerRunPage({params}:{params:Promise<{runId:string}>}){const {runId}=await params;return <main className="reference-run-page"><div className="reference-run-inner"><nav aria-label="Breadcrumb" className="mb-8 text-sm text-[#777680]"><Link href="/agents">Agents</Link><span className="mx-2" aria-hidden="true">›</span><Link href="/agents/content-optimizer">SEO Content Optimizer</Link><span className="mx-2" aria-hidden="true">›</span>Run</nav><ContentOptimizerRunView runId={runId}/></div></main>}
