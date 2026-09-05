import Link from "next/link";
import { InternalLinkingRun } from "@/components/internal-linking-run";

export default async function InternalLinkingRunPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  return <main className="reference-run-page"><div className="reference-run-inner">
    <nav aria-label="Breadcrumb" className="mb-8 text-sm text-[#777680]"><Link href="/agents" className="hover:text-[#e94320]">Agents</Link><span className="mx-2">›</span><Link href="/agents/internal-linking" className="hover:text-[#e94320]">Internal Linking Agent</Link><span className="mx-2">›</span><span>Run</span></nav>
    <InternalLinkingRun auditId={auditId} />
  </div></main>;
}
