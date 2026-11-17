import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Check } from "lucide-react";
import LeadForm from "@/components/LeadForm";
import { FAQS, TIERS } from "@/lib/marketing";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Pricing for Snapford Retention: Starter, Growth, Scale and Enterprise plans for subscription businesses and agencies.",
};

const MATRIX: { label: string; values: (string | boolean)[] }[] = [
  { label: "Tracked customers", values: ["1,000", "10,000", "50,000", "Unlimited"] },
  { label: "Seats", values: ["1", "5", "15", "Unlimited"] },
  { label: "Campaigns", values: ["3", "Unlimited", "Unlimited", "Unlimited"] },
  { label: "Flows", values: ["Core set", "All 37", "All 37", "All 37 + custom"] },
  { label: "Channels", values: ["Email", "Email, SMS, push", "Email, SMS, push", "Email, SMS, push"] },
  { label: "Dunning & cancel-save", values: [false, true, true, true] },
  { label: "Cohorts, RFM & attribution", values: [false, true, true, true] },
  { label: "Experiments & benchmarks", values: [false, true, true, true] },
  { label: "White-label client views", values: [false, false, true, true] },
  { label: "API keys, webhooks & MCP", values: [false, false, true, true] },
  { label: "Data residency", values: [false, false, false, true] },
  { label: "SSO & RBAC", values: [false, false, false, true] },
  { label: "Support", values: ["Community", "Email", "Priority", "Dedicated + SLA"] },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-7xl px-5 py-14">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Pricing</h1>
        <p className="mt-4 text-[var(--text-2)]">
          Every plan includes the full retention model — customers, segments, campaigns, flows and
          analytics. Plans differ in scale, channels and control.
        </p>
      </div>

      <div className="mt-12 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {TIERS.map((tier) => (
          <div
            key={tier.id}
            className={`relative flex flex-col rounded-2xl border p-6 ${
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
            <h2 className="text-lg font-bold">{tier.name}</h2>
            <p className="mt-1 min-h-[40px] text-sm text-[var(--text-2)]">{tier.summary}</p>
            <p className="mt-5">
              <span className="text-4xl font-extrabold tracking-tight">{tier.price}</span>
              <span className="ml-2 text-sm text-[var(--text-2)]">{tier.cadence}</span>
            </p>
            <ul className="mt-5 flex-1 space-y-2 text-sm text-[var(--text-2)]">
              {tier.features.map((feature) => (
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

      <section className="mt-16">
        <h2 className="text-2xl font-extrabold tracking-tight">Compare plans</h2>
        <div className="mt-6 overflow-x-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)]">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left">
                <th className="px-5 py-4 font-semibold">Capability</th>
                {TIERS.map((tier) => (
                  <th key={tier.id} className="px-5 py-4 font-semibold">
                    {tier.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MATRIX.map((row) => (
                <tr key={row.label} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-5 py-3 text-[var(--text-2)]">{row.label}</td>
                  {row.values.map((value, index) => (
                    <td key={`${row.label}-${index}`} className="px-5 py-3">
                      {value === true ? (
                        <Check size={15} className="text-emerald-500" />
                      ) : value === false ? (
                        <span className="text-[var(--text-2)]">—</span>
                      ) : (
                        <span className="text-[var(--text)]">{value}</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-16 grid gap-8 lg:grid-cols-2">
        <div>
          <h2 className="text-2xl font-extrabold tracking-tight">Pricing questions</h2>
          <div className="mt-6 space-y-3">
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

        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6">
          <h2 className="text-xl font-bold">Need a custom plan?</h2>
          <p className="mt-2 text-sm text-[var(--text-2)]">
            Tell us your customer volume, team size and the retention outcome you are chasing. We
            reply with a plan and a pilot.
          </p>
          <div className="mt-5">
            <LeadForm source="pricing" />
          </div>
          <Link
            href="/features"
            className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-500"
          >
            See what each plan unlocks
            <ArrowRight size={14} />
          </Link>
        </div>
      </section>
    </div>
  );
}
