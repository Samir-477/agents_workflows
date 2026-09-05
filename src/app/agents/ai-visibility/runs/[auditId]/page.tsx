import Link from "next/link";
import { AIVisibilityRun } from "@/components/ai-visibility-run";

export default async function AIVisibilityRunPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  return <main className="reference-run-page"><div className="reference-run-inner">
    <nav aria-label="Breadcrumb" className="mb-8 text-sm text-[#777680]"><Link href="/agents">Agents</Link><span className="mx-2">›</span><Link href="/agents/ai-visibility">AI Visibility Audit</Link><span className="mx-2">›</span><span>Run</span></nav>
    <AIVisibilityRun auditId={auditId} />
  </div></main>;
}
