import Link from "next/link";

import { AuditRun } from "@/components/audit-run";

export default async function AuditRunPage({ params }: { params: Promise<{ auditId: string }> }) {
  const { auditId } = await params;
  return (
    <main className="mx-auto max-w-[1280px] px-5 py-10 sm:px-8 sm:py-12">
      <nav aria-label="Breadcrumb" className="mb-8 text-sm text-[#777680]">
        <Link href="/agents" className="hover:text-[#e94320]">Agents</Link><span className="mx-2" aria-hidden="true">›</span><Link href="/agents/seo-audit" className="hover:text-[#e94320]">SEO Audit Agent</Link><span className="mx-2" aria-hidden="true">›</span><span>Run</span>
      </nav>
      <AuditRun auditId={auditId} />
    </main>
  );
}
