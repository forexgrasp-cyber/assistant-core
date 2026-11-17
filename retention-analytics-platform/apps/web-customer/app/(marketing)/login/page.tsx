"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { login } from "@/lib/auth";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
      const next = params.get("next");
      router.replace(next && next.startsWith("/") ? next : "/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <label className="flex flex-col gap-1 text-xs text-[var(--text-2)]">
        Work email
        <input
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
          className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2.5 text-sm text-[var(--text)] outline-none focus:border-indigo-500"
        />
      </label>

      <label className="flex flex-col gap-1 text-xs text-[var(--text-2)]">
        Password
        <input
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••••"
          className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2.5 text-sm text-[var(--text)] outline-none focus:border-indigo-500"
        />
      </label>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={busy}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-60"
      >
        {busy ? <Loader2 size={16} className="animate-spin" /> : null}
        {busy ? "Signing in…" : "Sign in"}
      </button>

      <p className="text-center text-xs text-[var(--text-2)]">
        No account yet?{" "}
        <Link href="/#access" className="font-medium text-indigo-600 hover:text-indigo-500">
          Request access
        </Link>
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-16 lg:grid-cols-2">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Welcome back</h1>
        <p className="mt-3 max-w-md text-[var(--text-2)]">
          Sign in to run your retention campaigns, watch customer health and see the before-and-after
          for every campaign.
        </p>

        <ul className="mt-8 space-y-3 text-sm text-[var(--text-2)]">
          <li className="flex items-start gap-2">
            <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-indigo-500" />
            Segments, campaigns and flows in one place
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-indigo-500" />
            Retention, churn and revenue measured before and after
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-indigo-500" />
            37 ready-made flows and 400+ automatable actions
          </li>
        </ul>

        <Link
          href="/features"
          className="mt-8 inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-500"
        >
          Explore the feature set
          <ArrowRight size={14} />
        </Link>
      </div>

      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-7 shadow-sm">
        <h2 className="text-lg font-bold">Sign in to your workspace</h2>
        <p className="mt-1 mb-6 text-sm text-[var(--text-2)]">
          Use the account your workspace was provisioned with.
        </p>
        <Suspense fallback={<div className="h-40" />}>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}
