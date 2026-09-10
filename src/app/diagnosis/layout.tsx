import { AppHeader } from "@/components/app-header";
export default function Layout({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-[#f7f6f2] text-[#20212b]"><AppHeader />{children}</div>;
}
