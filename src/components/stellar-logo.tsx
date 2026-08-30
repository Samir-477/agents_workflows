import Link from "next/link";

interface StellarLogoProps {
  href?: string;
  inverse?: boolean;
}

export function StellarLogo({ href = "/agents", inverse = false }: StellarLogoProps) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-2 rounded-md text-2xl font-black tracking-[-0.05em] ${inverse ? "text-white" : "text-[#12131a]"}`}
      aria-label="Stellar agents home"
    >
      <span>Stellar</span>
      <span className="relative inline-block h-5 w-5" aria-hidden="true">
        <span className="absolute inset-x-0 top-0 h-2.5 rounded-sm bg-[#ff5738]" />
        <span className="absolute bottom-0 right-0 h-3.5 w-3.5 -skew-x-12 rounded-sm bg-[#5a4df4]" />
      </span>
    </Link>
  );
}
