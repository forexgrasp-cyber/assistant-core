import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Check } from "lucide-react";
import { FEATURE_GROUPS, LOOP, STEPS } from "@/lib/marketing";

export const metadata: Metadata = {
  title: "Features",
  description:
    "Every capability in Snapford Retention: customer intelligence, automated retention campaigns, revenue analytics, success operations and integrations.",
};

export default function FeaturesPage() {
  return (
    <div className="mx-auto max-w-7xl px-5 py-14">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Every feature, grouped your way</h1>
        <p className="mt-4 text-[var(--text-2)]">
          Five groups, one data model. Pick the group you care about — the rest is already wired.
        </p>
        <nav className="mt-6 flex flex-wrap justify-center gap-2">
          {FEATURE_GROUPS.map((group) => (
            <a
              key={group.id}
              href={`#${group.id}`}
              className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--text-2)] transition hover:border-indigo-400 hover:text-[var(--text)]"
            >
              {group.name}
            </a>
          ))}
        </nav>
      </div>

      <div className="mt-14 space-y-8">
        {FEATURE_GROUPS.map((group) => (
          <section key={group.id} id={group.id} className="scroll-mt-24">
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 lg:p-10">
              <div className="flex flex-col gap-6 border-b border-[var(--border)] pb-6 lg:flex-row lg:items-center">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-indigo-600 text-white">
                  <group.icon size={20} />
                </div>
                <div>
                  <h2 className="text-2xl font-extrabold tracking-tight">{group.name}</h2>
                  <p className="mt-1 text-sm text-[var(--text-2)]">{group.tagline}</p>
                </div>
              </div>

              <div className="mt-8 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
                {group.items.map((item) => (
                  <div key={item.name}>
                    <h3 className="flex items-center gap-2 text-sm font-semibold">
                      <Check size={15} className="text-emerald-500" />
                      {item.name}
                    </h3>
                    <p className="mt-1 text-sm leading-relaxed text-[var(--text-2)]">
                      {item.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        ))}
      </div>

      <section id="how-it-works" className="mt-16 scroll-mt-24">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 lg:p-10">
          <h2 className="text-2xl font-extrabold tracking-tight">How it works</h2>
          <p className="mt-1 text-sm text-[var(--text-2)]">
            One loop connects events, triggers, pipelines, services and reports.
          </p>

          <div className="mt-8 grid gap-5 md:grid-cols-4">
            {STEPS.map((item) => (
              <div key={item.step} className="rounded-xl border border-[var(--border)] bg-[var(--bg)] p-5">
                <span className="text-xs font-bold tracking-widest text-indigo-600">{item.step}</span>
                <h3 className="mt-2 text-base font-semibold">{item.name}</h3>
                <p className="mt-1 text-sm text-[var(--text-2)]">{item.description}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 overflow-x-auto">
            <div className="flex min-w-[720px] items-center justify-between gap-3 text-center text-xs">
              {LOOP.map((item, index) => (
                <div key={item.step} className="flex flex-1 items-center gap-3">
                  <div className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--bg)] px-3 py-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                      {item.step}
                    </p>
                    <p className="mt-1 text-xs text-[var(--text-2)]">{item.detail}</p>
                  </div>
                  {index < LOOP.length - 1 && (
                    <span className="text-[var(--text-2)]" aria-hidden="true">
                      →
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="mt-16 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center">
        <h2 className="text-2xl font-extrabold tracking-tight">See it on your own data</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm text-[var(--text-2)]">
          Sign in to explore the platform, or request a workspace and a guided walkthrough.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            href="/login"
            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500"
          >
            Sign in
            <ArrowRight size={15} />
          </Link>
          <Link
            href="/pricing"
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--border)] px-5 py-3 text-sm font-semibold transition hover:bg-[var(--surface-2)]"
          >
            Compare plans
          </Link>
        </div>
      </section>
    </div>
  );
}
