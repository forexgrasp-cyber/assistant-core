import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { FEATURE_GROUPS, LOOP } from "@/lib/marketing";

const QUICK_LINKS = [
  { href: "/analytics", label: "Analytics" },
  { href: "/campaigns", label: "Send a campaign" },
  { href: "/events", label: "Ingest an event" },
  { href: "/reports", label: "Generate report" },
];

export default function ProductPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-10">
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8">
        <span className="inline-block rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">
          Retention platform
        </span>
        <h1 className="mt-4 text-3xl font-extrabold tracking-tight">
          Your whole retention loop, connected.
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[var(--text-2)]">
          Customer records feed segments, segments feed campaigns, campaigns run flows through
          registered services, and the outcomes land in analytics and reports. Every step is
          durable, idempotent and audited — nothing lives in a silo.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/campaigns"
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500"
          >
            Create a Campaign
            <ArrowRight size={15} />
          </Link>
          <Link
            href="/how-it-works"
            className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] px-5 py-2.5 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)]"
          >
            How it works
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] px-5 py-2.5 text-sm font-medium text-[var(--text)] transition hover:bg-[var(--surface-2)]"
          >
            Open Dashboard
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {QUICK_LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm font-medium text-[var(--text)] transition hover:border-indigo-300 hover:bg-[var(--surface-2)]"
          >
            {link.label}
          </Link>
        ))}
      </section>

      <section>
        <h2 className="text-xl font-bold">Features by group</h2>
        <p className="mt-1 text-sm text-[var(--text-2)]">
          The same groups as the public site, opened inside your workspace.
        </p>
        <div className="mt-6 grid gap-5 lg:grid-cols-2">
          {FEATURE_GROUPS.map((group) => (
            <div
              key={group.id}
              className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
                <group.icon size={18} />
              </div>
              <h3 className="mt-4 text-lg font-semibold">{group.name}</h3>
              <p className="mt-1 text-sm text-[var(--text-2)]">{group.tagline}</p>
              <ul className="mt-4 space-y-1.5 text-sm text-[var(--text-2)]">
                {group.items.map((item) => (
                  <li key={item.name}>• {item.name}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6">
        <h2 className="text-lg font-semibold">The loop</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {LOOP.map((item) => (
            <div key={item.step} className="rounded-xl border border-[var(--border)] bg-[var(--bg)] p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                {item.step}
              </p>
              <p className="mt-1 text-sm text-[var(--text-2)]">{item.detail}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
