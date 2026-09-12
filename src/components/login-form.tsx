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
      const response = await fetch("/auth/login", {
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
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      <div>
        <label htmlFor="email" className="text-xs font-semibold uppercase tracking-[.12em] text-[#626b70]">
          Username or email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          required
          defaultValue="demo@stellar.ai"
          className="mt-2 h-12 w-full rounded-xl border border-[#d9dedd] bg-white px-4 text-sm text-[#171b1d] shadow-sm outline-none transition hover:border-[#bcc6c2] focus:border-[#07814d] focus:ring-4 focus:ring-[#07814d]/10"
        />
      </div>

      <div>
        <label htmlFor="password" className="text-xs font-semibold uppercase tracking-[.12em] text-[#626b70]">
          Password
        </label>
        <div className="relative mt-2">
          <input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
          required
            defaultValue="stellar123"
            className="h-12 w-full rounded-xl border border-[#d9dedd] bg-white px-4 pr-11 text-sm text-[#171b1d] shadow-sm outline-none transition hover:border-[#bcc6c2] focus:border-[#07814d] focus:ring-4 focus:ring-[#07814d]/10"
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
        className="flex h-12 w-full items-center justify-center gap-3 rounded-xl bg-[#007846] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00663c] disabled:cursor-wait disabled:opacity-70"
      >
        {isSubmitting ? "Signing in..." : "Sign in to dashboard"}
        {!isSubmitting ? <ArrowIcon className="h-5 w-5" /> : null}
      </button>
    </form>
  );
}
