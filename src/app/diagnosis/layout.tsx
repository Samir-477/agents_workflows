import { AppHeader } from "@/components/app-header";
export default function Layout({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-[#f8fafb] text-[#121719]"><AppHeader />{children}</div>;
}
