"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ArrowIcon, EyeIcon } from "@/components/icons";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
        }),
      });
      if (!response.ok) {
        const payload = (await response.json()) as { error?: string };
        throw new Error(payload.error ?? "Unable to sign in.");
      }
      router.push("/agents");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-7 space-y-5" noValidate>
      <div>
        <label htmlFor="email" className="text-sm font-semibold text-[#24252d]">
          Email address
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          required
          placeholder="you@company.com"
          className="mt-2 h-13 w-full rounded-xl border border-[#d9d8d4] bg-[#fcfbf9] px-4 text-[#171820] outline-none transition placeholder:text-[#aaa9af] hover:border-[#c7c5bf] focus:border-[#5a4df4] focus:bg-white focus:ring-4 focus:ring-[#5a4df4]/10"
        />
      </div>

      <div>
        <label htmlFor="password" className="text-sm font-semibold text-[#24252d]">
          Password
        </label>
        <div className="relative mt-2">
          <input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            required
            placeholder="Enter your password"
            className="h-13 w-full rounded-xl border border-[#d9d8d4] bg-[#fcfbf9] px-4 pr-12 text-[#171820] outline-none transition placeholder:text-[#aaa9af] hover:border-[#c7c5bf] focus:border-[#5a4df4] focus:bg-white focus:ring-4 focus:ring-[#5a4df4]/10"
          />
          <button
            type="button"
            onClick={() => setShowPassword((visible) => !visible)}
            className="absolute right-3 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-[#85848b] transition hover:bg-[#efede9] hover:text-[#393a43]"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            <EyeIcon className="h-5 w-5" />
          </button>
        </div>
      </div>

      {error ? (
        <p role="alert" className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="flex h-13 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] px-5 font-semibold text-white shadow-[0_10px_26px_rgba(255,87,56,0.2)] transition hover:-translate-y-0.5 hover:bg-[#e9482b] hover:shadow-[0_14px_30px_rgba(255,87,56,0.24)] disabled:cursor-wait disabled:opacity-70"
      >
        {isSubmitting ? "Signing in..." : "Continue to workspace"}
        {!isSubmitting ? <ArrowIcon className="h-5 w-5" /> : null}
      </button>
    </form>
  );
}
