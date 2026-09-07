import Link from "next/link";

import { LocalSEORun } from "@/components/local-seo-run";

export default async function LocalSEORunPage({
  params,
}: {
  params: Promise<{ generationId: string }>;
}) {
  const { generationId } = await params;
  return (
    <main className="reference-run-page">
      <div className="reference-run-inner">
        <nav aria-label="Breadcrumb" className="mb-8 text-sm text-[#777680]">
          <Link href="/agents" className="hover:text-[#e94320]">Agents</Link>
          <span className="mx-2" aria-hidden="true">›</span>
          <Link href="/agents/local-seo" className="hover:text-[#e94320]">Local SEO Page Generator</Link>
          <span className="mx-2" aria-hidden="true">›</span>
          <span>Run</span>
        </nav>
        <LocalSEORun runId={generationId} />
      </div>
    </main>
  );
}
