"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { ArrowIcon } from "@/components/icons";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

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
    <form onSubmit={handleSubmit} className="mt-8 space-y-5" noValidate>
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
          defaultValue="admin@gmail.com"
          className="mt-2 h-13 w-full rounded-xl border border-[#d9d8d4] bg-white px-4 text-[#171820] outline-none transition placeholder:text-[#a0a0a8] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10"
        />
      </div>
      <div>
        <label htmlFor="password" className="text-sm font-semibold text-[#24252d]">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          defaultValue="admin123"
          className="mt-2 h-13 w-full rounded-xl border border-[#d9d8d4] bg-white px-4 text-[#171820] outline-none transition placeholder:text-[#a0a0a8] focus:border-[#5a4df4] focus:ring-4 focus:ring-[#5a4df4]/10"
        />
      </div>

      {error ? (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="flex h-13 w-full items-center justify-center gap-2 rounded-xl bg-[#ff5738] px-5 font-semibold text-white shadow-[0_8px_24px_rgba(255,87,56,0.22)] transition hover:bg-[#e9482b] disabled:cursor-wait disabled:opacity-70"
      >
        {isSubmitting ? "Signing in…" : "Sign in to Stellar"}
        {!isSubmitting ? <ArrowIcon className="h-5 w-5" /> : null}
      </button>
    </form>
  );
}
