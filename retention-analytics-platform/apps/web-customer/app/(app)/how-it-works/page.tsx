import Link from "next/link";

async function getPains() {
  // Server component fetch — API base from env or default
  try {
    const base = process.env.API_BACKEND_URL || "http://127.0.0.1:47319";
    const res = await fetch(`${base}/api/v1/pains`, {
      headers: { Authorization: "Bearer dev-token" },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

const layers = [
  {
    n: "1",
    name: "Customer records",
    what: "Your customers, with whatever fields you have: name, email, plan, value, health, last service date, interval, tags, anything.",
    why: "Everything else reads from here. No fields, no segmentation.",
    link: "/customers",
  },
  {
    n: "2",
    name: "Segments",
    what: "Live filters over those records — “next service due within 7 days”, “health below 50”, “value over 500”.",
    why: "Answers WHO to target, using your actual data.",
    link: "/campaigns",
  },
  {
    n: "3",
    name: "Campaigns",
    what: "An initiative you run: goal + target segment + which flows to run + schedule + what to measure.",
    why: "Answers WHAT and WHEN. Runs once, daily, weekly, or on event.",
    link: "/campaigns",
  },
  {
    n: "4",
    name: "Flows",
    what: "Reusable automation recipes: “when X happens → do A, then B, then C”. 24 built in, reusable across any campaign.",
    why: "Answers HOW. Build once, use in many campaigns.",
    link: "/flows",
  },
  {
    n: "5",
    name: "Events",
    what: "Customer actions: payment failed, service due, churn risk, cart abandoned, trial ending.",
    why: "Real-time triggers. Feed them by API, form, or CSV import.",
    link: "/events",
  },
  {
    n: "6",
    name: "Services",
    what: "The actions that actually do something: send email/SMS/push, start dunning, score health, alert team, run A/B test.",
    why: "46 registered services. Flows call them by name.",
    link: "/settings",
  },
  {
    n: "7",
    name: "Analytics & Reports",
    what: "Retention, churn, MRR/NRR/LTV, RFM, cohorts, NPS, benchmarks — plus before/after per campaign.",
    why: "Answers WHETHER IT WORKED.",
    link: "/analytics",
  },
];

const example = [
  { step: "Customer record", detail: "Maria — oil change every 180 days, last done 175 days ago, plan = premium" },
  { step: "Computed field", detail: "next_due_date = today + 5, days_until_due = 5" },
  { step: "Segment", detail: "“Oil change due soon” = days_until_due between 0 and 7" },
  { step: "Campaign", detail: "“October oil change push” — goal: reactivate, target: that segment, flow: service-due-reminder, schedule: daily" },
  { step: "Flow runs", detail: "For Maria: render template → email her → schedule SMS for day 3" },
  { step: "Measured", detail: "Campaign result: 42 members, 42 emails sent, 9 bookings (21% save rate) vs 12% baseline" },
  { step: "Feed back", detail: "Report shows 21% → you refine the segment (add 10-day window) for November" },
];

export default async function HowItWorks() {
  const pains = await getPains();
  return (
    <div className="max-w-4xl mx-auto space-y-10">
      <section className="text-center py-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">How it all fits together</h1>
        <p className="text-gray-500 max-w-2xl mx-auto">
          One loop. You never manage services in isolation — a campaign ties your customer data, target group,
          automations, and measurement together.
        </p>
      </section>

      {/* The loop diagram */}
      <div className="bg-slate-900 text-white rounded-xl p-6">
        <div className="flex flex-wrap items-center justify-center gap-2 text-xs font-mono">
          <span className="bg-blue-500/20 border border-blue-400/50 px-3 py-2 rounded">CUSTOMERS</span>
          <span className="text-slate-500">→</span>
          <span className="bg-cyan-500/20 border border-cyan-400/50 px-3 py-2 rounded">SEGMENTS</span>
          <span className="text-slate-500">→</span>
          <span className="bg-indigo-500/20 border border-indigo-400/50 px-3 py-2 rounded">CAMPAIGNS</span>
          <span className="text-slate-500">→</span>
          <span className="bg-emerald-500/20 border border-emerald-400/50 px-3 py-2 rounded">FLOWS</span>
          <span className="text-slate-500">→</span>
          <span className="bg-amber-500/20 border border-amber-400/50 px-3 py-2 rounded">SERVICES</span>
          <span className="text-slate-500">→</span>
          <span className="bg-pink-500/20 border border-pink-400/50 px-3 py-2 rounded">RESULTS</span>
        </div>
        <p className="text-slate-400 text-xs text-center mt-3">
          …and back around: analytics → better segments → better campaigns.
        </p>
      </div>

      {/* Layer breakdown */}
      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-4">The seven pieces</h2>
        <div className="space-y-3">
          {layers.map((l) => (
            <div key={l.n} className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 flex gap-4">
              <div className="text-xl font-bold text-gray-200">{l.n}</div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900">{l.name}</h3>
                  <Link href={l.link} className="text-xs text-indigo-600 hover:underline">Open →</Link>
                </div>
                <p className="text-sm text-gray-600 mt-1">{l.what}</p>
                <p className="text-xs text-gray-400 mt-1">{l.why}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Concrete example */}
      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Concrete example: an oil change business</h2>
        <p className="text-sm text-gray-500 mb-4">
          Same engine works for beauty treatments, gym memberships, prescriptions, maintenance contracts — anything with a date and an interval.
        </p>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm divide-y divide-gray-100">
          {example.map((e, i) => (
            <div key={i} className="p-4 flex gap-4">
              <span className="text-xs font-semibold text-indigo-600 w-32 shrink-0">{e.step}</span>
              <span className="text-sm text-gray-700">{e.detail}</span>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ: the confusing questions */}
      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-4">Common questions</h2>
        <div className="space-y-3">
          {[
            ["What's the difference between a Campaign and a Flow?",
             "A Flow is a recipe (event → steps). A Campaign is a run of that recipe against a group of customers. You build flows once and reuse them in many campaigns."],
            ["Do I need to pick an industry?",
             "No. Industry presets are optional shortcuts. Everything works on any customer records. Apply the automotive preset to a gym if your records have next-due dates — or ignore presets entirely."],
            ["Where do campaigns get their target list?",
             "From a segment: a filter over your customer records. You can use a saved segment or write criteria inline."],
            ["How is a campaign measured?",
             "When it runs, we compute your success metrics before and after and store the delta. Campaign results show member count, executions, and metric changes."],
            ["Can campaigns run automatically?",
             "Yes — schedule daily/weekly/monthly, or trigger on an event (payment failed, service due, churn risk)."],
            ["What if my data doesn't have the fields a preset needs?",
             "Add the fields to your customer records (any field works) or build your own segment criteria. The engine doesn't care what the fields are called."],
          ].map(([q, a]) => (
            <div key={q} className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <h3 className="font-semibold text-gray-900 text-sm">{q}</h3>
              <p className="text-sm text-gray-600 mt-1.5">{a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pain coverage */}
      {pains && (
        <section>
          <h2 className="text-xl font-bold text-gray-900 mb-2">User pains we fix automatically</h2>
          <p className="text-sm text-gray-500 mb-4">
            {pains.covered}/{pains.total_pains} end-user pains are covered by a registered workflow.
            When the event fires, the customer gets the fix without anyone lifting a finger.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pains.categories.map((cat: string) => (
              <div key={cat} className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
                <h3 className="font-semibold text-gray-900 text-sm capitalize mb-2">{cat} ({pains.by_category[cat].length})</h3>
                <div className="space-y-1.5">
                  {pains.by_category[cat].map((p: any) => (
                    <div key={p.id} className="text-xs">
                      <p className="font-medium text-gray-800">"{p.pain}"</p>
                      <p className="text-gray-400">→ {p.workflows.join(", ")} · gets: {p.customer_gets}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="flex justify-center gap-3 pb-8">
        <Link href="/campaigns" className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700">Create a campaign</Link>
        <Link href="/presets" className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50">Browse presets</Link>
        <Link href="/customers" className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50">Add customers</Link>
      </section>
    </div>
  );
}
