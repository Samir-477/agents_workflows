import { CheckIcon, SparkIcon } from "@/components/icons";
import { LoginForm } from "@/components/login-form";
import { StellarLogo } from "@/components/stellar-logo";

const workspaceBenefits = [
  "Run evidence-backed website audits",
  "Keep every report in one searchable history",
  "Download clear, client-ready results",
];

export default function LoginPage() {
  return (
    <main className="grid min-h-screen bg-[#f7f6f3] lg:grid-cols-[1.08fr_0.92fr]">
      <section className="relative hidden overflow-hidden bg-[#171820] px-12 py-10 text-white lg:flex lg:flex-col lg:justify-between xl:px-16 xl:py-12">
        <div className="absolute -right-32 -top-32 h-[430px] w-[430px] rounded-full bg-[#5a4df4]/35 blur-[90px]" />
        <div className="absolute -bottom-44 -left-28 h-[440px] w-[440px] rounded-full bg-[#ff5738]/25 blur-[100px]" />
        <div className="absolute inset-0 bg-[linear-gradient(135deg,transparent_35%,rgba(255,255,255,0.025)_35%,rgba(255,255,255,0.025)_50%,transparent_50%)] bg-[length:28px_28px] opacity-30" />

        <div className="relative flex items-center justify-between">
          <StellarLogo href="/login" inverse />
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-white/55">
            Agent workspace
          </span>
        </div>

        <div className="relative max-w-[610px] py-12">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/10 text-[#ff8068] shadow-[0_12px_40px_rgba(0,0,0,0.16)]">
            <SparkIcon className="h-6 w-6" />
          </div>
          <p className="mt-7 font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-[#a9a2ff]">
            One focused job at a time
          </p>
          <h1 className="mt-4 text-5xl font-semibold leading-[1.04] tracking-[-0.055em] xl:text-[58px]">
            Specialist agents.
            <br />
            <span className="text-white/68">Useful results.</span>
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-white/62">
            Turn a URL and a little context into structured work your team can understand, share, and act on.
          </p>

          <ul className="mt-8 grid max-w-xl gap-3 sm:grid-cols-2">
            {workspaceBenefits.map((benefit) => (
              <li key={benefit} className="flex items-start gap-3 rounded-xl border border-white/[0.08] bg-white/[0.045] px-4 py-3 text-sm leading-6 text-white/72 backdrop-blur-sm">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#6658e8]/25 text-[#b9b4ff]">
                  <CheckIcon className="h-3.5 w-3.5" />
                </span>
                {benefit}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative flex items-center gap-3 text-white/35">
          <span className="h-px w-10 bg-white/20" />
          <p className="font-mono text-[10px] uppercase tracking-[0.18em]">
            Clear decisions, not chat transcripts
          </p>
        </div>
      </section>

      <section className="relative flex items-center justify-center overflow-hidden px-5 py-10 sm:px-10 lg:px-12">
        <div className="absolute right-[-120px] top-[-140px] h-80 w-80 rounded-full bg-[#5a4df4]/8 blur-3xl" />
        <div className="absolute bottom-[-150px] left-[-100px] h-72 w-72 rounded-full bg-[#ff5738]/8 blur-3xl" />

        <div className="relative w-full max-w-[480px]">
          <div className="mb-10 lg:hidden">
            <StellarLogo href="/login" />
          </div>
          <div className="rounded-[26px] border border-[#dfded8] bg-white p-6 shadow-[0_24px_80px_rgba(26,26,36,0.09)] sm:p-9">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#f0eeff] text-[#5549dd]">
              <SparkIcon className="h-5 w-5" />
            </div>
            <p className="mt-6 font-mono text-[11px] font-semibold uppercase tracking-[0.2em] text-[#5549dd]">
              Stellar workspace
            </p>
            <h2 className="mt-3 text-4xl font-semibold tracking-[-0.045em] text-[#14151d]">
              Welcome back
            </h2>
            <p className="mt-3 leading-7 text-[#6b6a73]">
              Sign in to access your agents, saved audits, and reports.
            </p>
            <LoginForm />
            <div className="mt-6 flex items-center justify-center gap-2 border-t border-[#eceae6] pt-5 text-xs text-[#85848b]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#45a47a]" />
              Your audit workspace is ready
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
