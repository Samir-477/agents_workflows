import { AgentDirectory } from "@/components/agent-directory";
import { agents } from "@/data/agents";

export default function AgentsPage() {
  return (
    <main>
      <section className="border-b border-[#e8e6e1] bg-[radial-gradient(circle_at_75%_20%,rgba(90,77,244,0.10),transparent_34%),radial-gradient(circle_at_22%_24%,rgba(255,87,56,0.08),transparent_30%)]">
        <div className="mx-auto max-w-[1180px] px-5 pb-12 pt-14 sm:px-8 sm:pb-16 sm:pt-20">
          <div className="inline-flex items-center rounded-full border border-[#dbd9d4] bg-white/70 px-4 py-2 font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-[#62616a]">
            <span className="mr-2 h-2 w-2 rounded-sm bg-[#ff5738] shadow-[6px_0_0_#5a4df4]" />
            Stellar agents · {agents.length} specialists
          </div>
          <h1 className="mt-8 max-w-4xl text-5xl font-semibold leading-[1.02] tracking-[-0.055em] sm:text-7xl">
            AI agents for <span className="text-[#da421f]">websites</span>,{" "}<span className="text-[#5a4df4]">SEO and useful work</span>
          </h1>
          <p className="mt-7 max-w-2xl text-lg leading-8 text-[#62626c]">Each Stellar agent does one job end to end. Give it the right input and receive structured output you can understand, share, and act on.</p>
        </div>
      </section>
      <div className="mx-auto max-w-[1180px] px-5 pb-24 sm:px-8"><AgentDirectory /></div>
    </main>
  );
}
