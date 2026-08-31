import Link from "next/link";

import { StellarLogo } from "@/components/stellar-logo";

export function AppHeader() {
  return (
    <header className="border-b border-[#e8e7e4] bg-white">
      <div className="mx-auto flex h-[76px] max-w-[1180px] items-center justify-between px-5 sm:px-8">
        <div className="flex items-center gap-4">
          <StellarLogo />
          <span className="hidden rounded-full border border-[#deddd9] bg-[#faf9f7] px-3 py-1 font-mono text-[11px] tracking-[0.08em] text-[#6d6d75] sm:inline-flex">
            <span className="mr-2 text-[#ff5738]">●</span> early access
          </span>
        </div>

        <nav className="flex items-center gap-3" aria-label="Account navigation">
          <Link
            href="/agents"
            className="hidden rounded-lg px-3 py-2 text-sm font-medium text-[#5f5f68] hover:bg-[#f6f5f2] hover:text-[#12131a] sm:inline-flex"
          >
            Agents
          </Link>
          <Link
            href="/agents/history"
            className="hidden rounded-lg px-3 py-2 text-sm font-medium text-[#5f5f68] hover:bg-[#f6f5f2] hover:text-[#12131a] sm:inline-flex"
          >
            History
          </Link>
          <Link
            href="/agents/settings"
            className="hidden rounded-lg px-3 py-2 text-sm font-medium text-[#5f5f68] hover:bg-[#f6f5f2] hover:text-[#12131a] sm:inline-flex"
          >
            Settings
          </Link>
          <form action="/auth/logout" method="post">
            <button
              type="submit"
              className="rounded-xl border border-[#deddd9] bg-white px-4 py-2.5 text-sm font-semibold text-[#20212a] transition hover:border-[#bdbcb8] hover:bg-[#faf9f7]"
            >
              Log out
            </button>
          </form>
        </nav>
      </div>
    </header>
  );
}
