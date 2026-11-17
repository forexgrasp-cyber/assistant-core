import Link from "next/link";
import { ArrowRight, Check, Sparkles } from "lucide-react";
import LeadForm from "@/components/LeadForm";
import {
  BENEFITS,
  FAQS,
  FEATURE_GROUPS,
  LOOP,
  STATS,
  STEPS,
  TIERS,
} from "@/lib/marketing";

const SECTORS = ["SaaS", "Ecommerce", "Fitness & wellness", "Beauty", "Healthcare", "Agencies"];

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-7xl px-5">
      <section className="pt-10">
        <div className="mk-hero">
          <div className="mk-grid" />
          <div className="mk-hero-content">
            <div className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
              <div>
                <span className="inline-flex items-center gap-2 rounded-full border border-[var(--hero-border)] bg-[var(--surface)]/60 px-3 py-1 text-xs font-medium text-[var(--hero-muted)]">
                  <Sparkles size={13} />
                  Retention analytics platform
                </span>

                <h1
                  className="mt-5 text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl"
                  style={{ color: "var(--hero-text)" }}
                >
                  Stop churn before it happens.
                </h1>

                <p
                  className="mt-4 max-w-xl text-base leading-relaxed"
                  style={{ color: "var(--hero-muted)" }}
                >
                  Snapford Retention turns your customer data into automated retention campaigns —
                  dunning, win-back, health scoring and churn prevention — and shows you the impact
                  before and after, not a guess.
                </p>

                <div className="mt-7 flex flex-wrap gap-3">
                  <Link
                    href="/login"
                    className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500"
                  >
                    Get started
                    <ArrowRight size={16} />
                  </Link>
                  <Link
                    href="/pricing"
                    className="inline-flex items-center gap-2 rounded-xl border border-[var(--hero-border)] bg-[var(--surface)]/60 px-5 py-3 text-sm font-semibold transition"
                    style={{ color: "var(--hero-text)" }}
                  >
                    See pricing
                  </Link>
                </div>

                <dl className="mt-9 grid grid-cols-2 gap-4 sm:grid-cols-4">
                  {STATS.map((stat) => (
                    <div key={stat.label}>
                      <dt className="text-2xl font-extrabold" style={{ color: "var(--hero-text)" }}>
                        {stat.value}
                      </dt>
                      <dd className="mt-1 text-xs leading-snug" style={{ color: "var(--hero-muted)" }}>
                        {stat.label}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>

              <div className="relative">
                <div className="rounded-2xl border border-[var(--hero-border)] bg-[var(--surface)]/80 p-5 shadow-xl backdrop-blur">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-[var(--text-2)]">
                      Campaign impact — retention vs churn
                    </span>
                    <span className="mk-pulse inline-flex items-center gap-1 text-xs text-emerald-500">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      live
                    </span>
                  </div>

                  <svg viewBox="0 0 620 240" className="mt-4 w-full" role="img" aria-label="Retention rising while churn falls">
                    <defs>
                      <linearGradient id="mkFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0" stopColor="#34d399" stopOpacity="0.38" />
                        <stop offset="1" stopColor="#34d399" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    {[40, 80, 120, 160, 200].map((y) => (
                      <line
                        key={y}
                        x1="20"
                        y1={y}
                        x2="600"
                        y2={y}
                        stroke="var(--border)"
                        strokeWidth="1"
                      />
                    ))}
                    <path
                      className="mk-draw"
                      d="M20,190 C160,185 260,120 380,80 C470,50 540,38 600,32"
                      fill="none"
                      stroke="#34d399"
                      strokeWidth="4"
                      strokeLinecap="round"
                    />
                    <path
                      d="M20,190 C160,185 260,120 380,80 C470,50 540,38 600,32 L600,220 L20,220 Z"
                      fill="url(#mkFill)"
                      opacity="0.65"
                    />
                    <path
                      className="mk-draw"
                      style={{ animationDelay: "0.5s" }}
                      d="M20,60 C160,70 300,120 420,160 C490,182 540,196 600,200"
                      fill="none"
                      stroke="#fb7185"
                      strokeWidth="3"
                      strokeDasharray="7 6"
                      strokeLinecap="round"
                    />
                    <circle cx="600" cy="32" r="6" fill="#34d399" />
                    <circle cx="600" cy="200" r="5" fill="#fb7185" />
                    <text x="500" y="22" fill="#34d399" fontSize="13" fontFamily="ui-monospace, monospace">
                      retention
                    </text>
                    <text x="520" y="222" fill="#fb7185" fontSize="13" fontFamily="ui-monospace, monospace">
                      churn
                    </text>
                  </svg>

                  <div className="mt-4 grid grid-cols-3 gap-3 text-center">
                    {["churn-prevention", "dunning-recovery", "win-back"].map((flow, index) => (
                      <div
                        key={flow}
                        className={`rounded-lg border border-[var(--border)] bg-[var(--bg)] px-2 py-2 text-[11px] text-[var(--text-2)] ${
                          index === 1 ? "mk-float-delayed" : "mk-float"
                        }`}
                      >
                        {flow}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-y border-[var(--border)] py-6">
        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-sm text-[var(--text-2)]">
          <span className="text-xs uppercase tracking-wider text-[var(--text-2)]">Built for</span>
          {SECTORS.map((sector) => (
            <span key={sector} className="font-medium">
              {sector}
            </span>
          ))}
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-extrabold tracking-tight">Why teams choose Snapford Retention</h2>
          <p className="mt-3 text-[var(--text-2)]">
            The benefits you get from the platform — not a list of module names.
          </p>
        </div>

        <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {BENEFITS.map((benefit) => (
            <div
              key={benefit.title}
              className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 transition hover:border-indigo-300 hover:shadow-md"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                <benefit.icon size={18} />
              </div>
              <h3 className="mt-4 text-lg font-semibold">{benefit.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--text-2)]">{benefit.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-extrabold tracking-tight">Everything in one retention loop</h2>
          <p className="mt-3 text-[var(--text-2)]">
            Five groups of capabilities, wired to each other. Open any group in the portal and it is
            already connected to the rest.
          </p>
        </div>

        <div className="mt-10 space-y-6">
          {FEATURE_GROUPS.map((group) => (
            <div
              key={group.id}
              className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 lg:p-8"
            >
              <div className="flex flex-col gap-6 lg:flex-row">
                <div className="lg:w-72">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white">
                    <group.icon size={18} />
                  </div>
                  <h3 className="mt-4 text-xl font-bold">{group.name}</h3>
                  <p className="mt-2 text-sm text-[var(--text-2)]">{group.tagline}</p>
                  <Link
                    href="/features"
                    className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-500"
                  >
                    Full feature list
                    <ArrowRight size={14} />
                  </Link>
                </div>

                <div className="grid flex-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {group.items.map((item) => (
                    <div key={item.name} className="rounded-xl border border-[var(--border)] bg-[var(--bg)] p-4">
                      <h4 className="text-sm font-semibold">{item.name}</h4>
                      <p className="mt-1 text-xs leading-relaxed text-[var(--text-2)]">
                        {item.description}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-extrabold tracking-tight">From data to measurable outcome</h2>
          <p className="mt-3 text-[var(--text-2)]">
            Four steps, one loop. Nothing is configured twice.
          </p>
        </div>

        <div className="mt-10 grid gap-5 md:grid-cols-4">
          {STEPS.map((item) => (
            <div key={item.step} className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6">
              <span className="text-xs font-bold tracking-widest text-indigo-600">{item.step}</span>
              <h3 className="mt-3 text-lg font-semibold">{item.name}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[var(--text-2)]">{item.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 overflow-x-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6">
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
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-extrabold tracking-tight">Simple pricing, real capability</h2>
          <p className="mt-3 text-[var(--text-2)]">
            Start with one retention loop, scale to every client you serve.
          </p>
        </div>

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {TIERS.slice(0, 3).map((tier) => (
            <div
              key={tier.id}
              className={`relative rounded-2xl border p-6 ${
                tier.featured
                  ? "border-indigo-500 bg-[var(--surface)] shadow-lg"
                  : "border-[var(--border)] bg-[var(--surface)]"
              }`}
            >
              {tier.featured && (
                <span className="absolute -top-3 left-6 rounded-full bg-indigo-600 px-3 py-1 text-xs font-semibold text-white">
                  Most popular
                </span>
              )}
              <h3 className="text-lg font-bold">{tier.name}</h3>
              <p className="mt-1 text-sm text-[var(--text-2)]">{tier.summary}</p>
              <p className="mt-5">
                <span className="text-4xl font-extrabold tracking-tight">{tier.price}</span>
                <span className="ml-2 text-sm text-[var(--text-2)]">{tier.cadence}</span>
              </p>
              <ul className="mt-5 space-y-2 text-sm text-[var(--text-2)]">
                {tier.features.slice(0, 5).map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <Check size={15} className="mt-0.5 shrink-0 text-emerald-500" />
                    {feature}
                  </li>
                ))}
              </ul>
              <Link
                href="/login"
                className={`mt-6 block rounded-lg px-4 py-2.5 text-center text-sm font-semibold transition ${
                  tier.featured
                    ? "bg-indigo-600 text-white hover:bg-indigo-500"
                    : "border border-[var(--border)] text-[var(--text)] hover:bg-[var(--surface-2)]"
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>

        <div className="mt-8 text-center">
          <Link
            href="/pricing"
            className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-500"
          >
            Compare every plan
            <ArrowRight size={14} />
          </Link>
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-center text-3xl font-extrabold tracking-tight">Questions before you start</h2>
          <div className="mt-10 space-y-3">
            {FAQS.map((faq) => (
              <details
                key={faq.question}
                className="group rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-5 py-4"
              >
                <summary className="flex cursor-pointer items-center justify-between gap-4 text-sm font-semibold">
                  {faq.question}
                  <span className="text-lg text-[var(--text-2)] transition group-open:rotate-45">+</span>
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-[var(--text-2)]">{faq.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section id="access" className="pb-20 scroll-mt-24">
        <div className="grid items-center gap-10 rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-8 lg:grid-cols-2 lg:p-12">
          <div>
            <h2 className="text-3xl font-extrabold tracking-tight">
              Ready to keep more customers?
            </h2>
            <p className="mt-3 text-[var(--text-2)]">
              Get a workspace, import one customer list and run your first retention campaign. We
              will help you wire the data.
            </p>
            <ul className="mt-6 space-y-2 text-sm text-[var(--text-2)]">
              <li className="flex items-center gap-2">
                <Check size={15} className="text-emerald-500" /> 20-minute walkthrough
              </li>
              <li className="flex items-center gap-2">
                <Check size={15} className="text-emerald-500" /> Import help included
              </li>
              <li className="flex items-center gap-2">
                <Check size={15} className="text-emerald-500" /> No card required
              </li>
            </ul>
            <Link
              href="/login"
              className="mt-7 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500"
            >
              Sign in to the portal
              <ArrowRight size={16} />
            </Link>
          </div>

          <LeadForm source="landing" />
        </div>
      </section>

      <section className="border-t border-[var(--border)] py-12">
        <div className="flex flex-col items-center justify-between gap-6 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 text-center md:flex-row md:text-left">
          <div>
            <h2 className="text-xl font-bold">Looking for a different Snapford product?</h2>
            <p className="mt-2 max-w-xl text-sm text-[var(--text-2)]">
              Retention sits next to DMARC, books, janitorial, SEO, newsletter, geo and community —
              the full catalogue lives on the Snapford home page.
            </p>
          </div>
          <a
            href="https://snapford.com"
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-[var(--border)] px-5 py-3 text-sm font-semibold transition hover:bg-[var(--surface-2)]"
          >
            Browse all Snapford products
            <ArrowRight size={15} />
          </a>
        </div>
      </section>
    </div>
  );
}
