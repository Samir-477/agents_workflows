"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/agents", label: "Agents", match: (path: string) => path === "/agents" || (path.startsWith("/agents/") && !path.startsWith("/agents/history")) },
  { href: "/diagnosis", label: "New run", match: (path: string) => path.startsWith("/diagnosis") },
  { href: "/agents/history", label: "Sessions", match: (path: string) => path.startsWith("/agents/history") },
];

export function AppHeader() {
  const pathname = usePathname();
  return <header className="sticky top-0 z-40 border-b border-[#e2e5e4] bg-[#fbfcfc]/95 backdrop-blur">
    <div className="mx-auto flex h-[68px] max-w-[1240px] items-center justify-between px-5 sm:px-7">
      <div className="flex items-center gap-6 lg:gap-12">
        <Link href="/agents" className="flex items-center gap-3 font-semibold tracking-[-.02em] text-[#171b1d]">
          <span className="grid h-8 w-8 place-items-center rounded-[10px] bg-[#14191d] text-xs font-bold text-white">S</span>
          <span className="hidden sm:inline">Stellar Agents</span>
        </Link>
        <nav className="flex items-center gap-1" aria-label="Workspace navigation">
          {navItems.map(item => { const active=item.match(pathname); return <Link key={item.href} href={item.href} className={`rounded-full px-3 py-1.5 text-[13px] transition sm:px-4 ${active?"bg-[#f0f2f2] font-medium text-[#181c1e]":"text-[#737a7d] hover:text-[#181c1e]"}`}>{item.label}</Link>; })}
        </nav>
      </div>
      <div className="flex items-center gap-4"><span className="hidden text-[13px] text-[#747b7e] md:inline">demo@stellar.ai</span><form action="/auth/logout" method="post"><button type="submit" className="text-[13px] font-medium text-[#202426] hover:text-[#007846]">Sign out</button></form></div>
    </div>
  </header>;
}
