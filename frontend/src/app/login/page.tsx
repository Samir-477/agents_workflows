import { LoginForm } from "@/components/login-form";
import { SparkIcon } from "@/components/icons";
import { StellarLogo } from "@/components/stellar-logo";

export default function LoginPage() {
  return (
    <main className="grid min-h-screen bg-[#f8f7f4] lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden bg-[#171820] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-36 -top-28 h-96 w-96 rounded-full bg-[#5a4df4]/35 blur-3xl" />
        <div className="absolute -bottom-32 -left-24 h-96 w-96 rounded-full bg-[#ff5738]/30 blur-3xl" />
        <div className="relative"><StellarLogo href="/login" inverse /></div>
        <div className="relative max-w-xl">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-[#ff8068]">
            <SparkIcon className="h-6 w-6" />
          </div>
          <h1 className="mt-7 text-5xl font-semibold leading-[1.08] tracking-[-0.05em]">Specialist agents.<br />Useful results.</h1>
          <p className="mt-5 max-w-lg text-lg leading-8 text-white/65">Give Stellar a URL and context. Get structured, evidence-backed work you can understand and act on.</p>
        </div>
        <p className="relative font-mono text-xs uppercase tracking-[0.16em] text-white/40">Built for clear decisions, not chat transcripts</p>
      </section>

      <section className="flex items-center justify-center px-5 py-12 sm:px-10">
        <div className="w-full max-w-md">
          <div className="mb-10 lg:hidden"><StellarLogo href="/login" /></div>
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#5549dd]">Demo workspace</p>
          <h2 className="mt-3 text-4xl font-semibold tracking-[-0.045em] text-[#14151d]">Welcome back</h2>
          <p className="mt-3 leading-7 text-[#6b6a73]">Sign in to open your Stellar agent catalogue.</p>
          <LoginForm />
          <div className="mt-6 rounded-xl border border-[#dfded9] bg-white/70 px-4 py-3 text-sm text-[#67666e]">
            <strong className="text-[#24252d]">Demo access:</strong> admin@gmail.com / admin123
          </div>
        </div>
      </section>
    </main>
  );
}
