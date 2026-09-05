import Link from "next/link";
import { SchemaRun } from "@/components/schema-run";

export default async function SchemaRunPage({ params }: { params: Promise<{ generationId: string }> }) {
  const { generationId } = await params;
  return <main className="reference-run-page"><div className="reference-run-inner">
    <nav aria-label="Breadcrumb" className="mb-8 text-sm text-[#777680]"><Link href="/agents" className="hover:text-[#e94320]">Agents</Link><span className="mx-2">›</span><Link href="/agents/schema-markup" className="hover:text-[#e94320]">Schema Generator</Link><span className="mx-2">›</span><span>Run</span></nav>
    <SchemaRun generationId={generationId} />
  </div></main>;
}
