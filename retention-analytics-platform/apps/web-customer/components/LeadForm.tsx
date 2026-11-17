"use client";

import { useState } from "react";

type State = "idle" | "submitting" | "done" | "error";

export default function LeadForm({ source = "landing" }: { source?: string }) {
  const [state, setState] = useState<State>("idle");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setState("submitting");
    setError("");
    try {
      const res = await fetch("/api/v1/public/leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, company, message, source }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Request failed (${res.status})`);
      }
      setState("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setState("error");
    }
  }

  if (state === "done") {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 text-center">
        <p className="text-lg font-semibold text-[var(--text)]">Request received</p>
        <p className="mt-2 text-sm text-[var(--text-2)]">
          We will reply to {email || "your inbox"} with a portal invite and a walkthrough of the
          retention loop.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={submit}
      className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm"
    >
      <p className="text-sm font-semibold text-[var(--text)]">Get access</p>
      <p className="mt-1 text-sm text-[var(--text-2)]">
        Tell us where to send your workspace invite.
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs text-[var(--text-2)]">
          Work email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-indigo-500"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-[var(--text-2)]">
          Company
          <input
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Acme Inc."
            className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-indigo-500"
          />
        </label>
      </div>

      <label className="mt-3 flex flex-col gap-1 text-xs text-[var(--text-2)]">
        What are you trying to fix? (optional)
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={3}
          placeholder="We keep losing subscription renewals in month two…"
          className="rounded-lg border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm text-[var(--text)] outline-none focus:border-indigo-500"
        />
      </label>

      {state === "error" && (
        <p className="mt-3 text-sm text-red-500">{error}</p>
      )}

      <button
        type="submit"
        disabled={state === "submitting"}
        className="mt-4 w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-60"
      >
        {state === "submitting" ? "Sending…" : "Request access"}
      </button>
      <p className="mt-2 text-center text-xs text-[var(--text-2)]">
        No card required. We reply with access and a 20-minute walkthrough.
      </p>
    </form>
  );
}
