import Link from "next/link";

import { MetadataRun } from "@/components/metadata-run";

export default async function MetadataRunPage({
  params,
}: {
  params: Promise<{ generationId: string }>;
}) {
  const { generationId } = await params;
  return (
    <main className="reference-run-page"><div className="reference-run-inner">
      <nav aria-label="Breadcrumb" className="mb-8 text-sm text-[#777680]">
        <Link href="/agents" className="hover:text-[#e94320]">Agents</Link>
        <span className="mx-2" aria-hidden="true">›</span>
        <Link href="/agents/meta-title-description" className="hover:text-[#e94320]">Metadata Generator</Link>
        <span className="mx-2" aria-hidden="true">›</span>
        <span>Run</span>
      </nav>
      <MetadataRun generationId={generationId} />
    </div></main>
  );
}
