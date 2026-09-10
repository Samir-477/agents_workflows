import { DiagnosisRun } from "@/components/diagnosis-run";
export default async function Page({ params }: { params: Promise<{id: string}> }) {
  const {id} = await params;
  return <DiagnosisRun id={id} />;
}
