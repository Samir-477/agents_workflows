import Link from "next/link";
import { KeywordClusterRun } from "@/components/keyword-cluster-run";

export default async function KeywordClusterRunPage({ params }: { params: Promise<{ generationId: string }> }) {
  const { generationId } = await params;
  return <main className="reference-run-page"><div className="reference-run-inner">
    <nav aria-label="Breadcrumb" className="mb-8 text-sm text-[#777680]"><Link href="/agents" className="hover:text-[#e94320]">Agents</Link><span className="mx-2">›</span><Link href="/agents/keyword-cluster" className="hover:text-[#e94320]">Keyword Cluster Agent</Link><span className="mx-2">›</span><span>Run</span></nav>
    <KeywordClusterRun generationId={generationId} />
  </div></main>;
}
