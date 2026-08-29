import { AppHeader } from "@/components/app-header";

export default function AgentsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#fbfaf8] text-[#12131a]">
      <AppHeader />
      {children}
    </div>
  );
}
