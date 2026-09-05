import Link from "next/link";
import { ContentBriefRun } from "@/components/content-brief-run";

export default async function ContentBriefRunPage({ params }: { params: Promise<{ generationId: string }> }) {
  const { generationId } = await params;
  return <main className="reference-run-page"><div className="reference-run-inner">
    <nav aria-label="Breadcrumb" className="mb-8 text-sm text-[#777680]"><Link href="/agents">Agents</Link><span className="mx-2">›</span><Link href="/agents/content-brief">Content Brief Agent</Link><span className="mx-2">›</span><span>Run</span></nav>
    <ContentBriefRun generationId={generationId} />
  </div></main>;
}
