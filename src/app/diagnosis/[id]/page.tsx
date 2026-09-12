import { DiagnosisRun } from "@/components/diagnosis-run";
import { loadDiagnosis } from "@/lib/server-diagnosis";

export default async function Page({ params }: { params: Promise<{id: string}> }) {
  const {id} = await params;
  return <DiagnosisRun id={id} initialRun={await loadDiagnosis(id)} />;
}
