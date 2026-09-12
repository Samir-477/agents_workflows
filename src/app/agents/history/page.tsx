import { AuditHistory } from "@/components/audit-history";
import { loadDiagnosisHistory } from "@/lib/server-diagnosis";

export default async function AgentHistoryPage() {
  const sessions = await loadDiagnosisHistory();
  return (
    <main className="min-h-[calc(100vh-68px)] bg-[#f8fafb]"><div className="mx-auto max-w-[1240px] px-5 pb-24 pt-16 sm:px-7 sm:pt-20"><AuditHistory initialSessions={sessions} /></div><footer className="border-t border-[#e2e6e4]"><div className="mx-auto flex max-w-[1240px] flex-wrap justify-between gap-4 px-5 py-8 text-xs text-[#7b8387] sm:px-7"><p>Stellar Agents — SEO, AEO and content analysis for pages that need to be found and understood.</p><p>Saved diagnosis sessions · Evidence-backed reports</p></div></footer></main>
  );
}
