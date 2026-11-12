import Link from "next/link";

const features = [
  {
    title: "Automated Retention Workflows",
    desc: "Churn prevention, cart abandonment recovery, welcome series, and win-back — triggered by real customer events, executed durably step-by-step through registered services.",
    detail: "Input: customer event (e.g. client.churn_risk). Output: rendered email/SMS sent to the customer + retention metric updated.",
  },
  {
    title: "Multi-Channel Campaigns",
    desc: "Send email, SMS, and push from one place. Every send goes through a registered service action, so it's traceable, idempotent, and auditable.",
    detail: "Input: recipient + subject + body. Output: queued message with message_id, persisted to the outbox.",
  },
  {
    title: "Real-Time Analytics",
    desc: "30-day retention rate, churn rate, RFM segmentation, and cohort analysis — computed on demand from your event data.",
    detail: "Input: tenant_id. Output: retention_rate_30d, churn_rate_30d, RFM segment counts, cohort table.",
  },
  {
    title: "Event-Driven Pipelines",
    desc: "Ingest any event (client created, order placed, cart abandoned, subscription cancelled) and the matching workflow fires automatically.",
    detail: "Input: event type + payload + idempotency_key. Output: workflow run with step outputs; replay returns the same result.",
  },
  {
    title: "Reports & Exports",
    desc: "Generate retention reports as PDF, HTML, CSV, or JSON. Download or share with your team.",
    detail: "Input: report name + format. Output: generated report with download_url.",
  },
  {
    title: "Multi-Tenant by Design",
    desc: "Every request is scoped to your authenticated tenant. Cross-tenant access is blocked at the API boundary — your data is isolated.",
    detail: "Input: JWT token. Output: tenant-scoped data only. 403 on any cross-tenant attempt.",
  },
];

const dataFlow = [
  { step: "1. Event", desc: "Customer action ingested via POST /api/v1/events (idempotent)" },
  { step: "2. Trigger", desc: "Event matches a workflow trigger (e.g. client.churn_risk → churn-prevention)" },
  { step: "3. Pipeline", desc: "Workflow engine runs steps in order: render template → send email → compute metric" },
  { step: "4. Service", desc: "Each step invokes a registered service action (email.send, analytics.metric.compute_retention)" },
  { step: "5. Persist", desc: "Results written to durable storage (outbox, metrics, audit log with hash chain)" },
  { step: "6. Report", desc: "Analytics and reports surface the outcome in the dashboard" },
];

export default function Landing() {
  return (
    <div className="max-w-5xl mx-auto">
      {/* Hero */}
      <section className="text-center py-16">
        <div className="inline-block bg-indigo-100 text-indigo-700 text-xs font-semibold px-3 py-1 rounded-full mb-4">
          Multi-tenant retention platform
        </div>
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Stop churn before it happens.
        </h1>
        <p className="text-lg text-gray-500 mb-8 max-w-2xl mx-auto">
          Automated retention workflows, multi-channel campaigns, and real-time analytics —
          every service wired into pipelines, not silos. 24 services. 4 workflows. 41 API endpoints.
        </p>
        <div className="flex justify-center gap-3">
          <Link href="/campaigns" className="px-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition">
            Create a Campaign
          </Link>
          <Link href="/how-it-works" className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition">
            How it works
          </Link>
          <Link href="/dashboard" className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition">
            Open Dashboard
          </Link>
        </div>
      </section>

      {/* The unified model */}
      <section className="py-10">
        <h2 className="text-2xl font-bold text-gray-900 mb-2 text-center">The unified model</h2>
        <p className="text-gray-500 text-center mb-6 max-w-2xl mx-auto">
          One loop connects everything. You don't manage services in isolation — you run campaigns that tie targets, automations, and measurement together.
        </p>
        <div className="bg-slate-900 rounded-xl p-6 text-white">
          <div className="flex flex-wrap items-center justify-center gap-2 text-xs font-mono">
            <span className="bg-blue-500/20 border border-blue-400/50 px-3 py-2 rounded">SEGMENT<br/><span className="text-slate-400">who — criteria</span></span>
            <span className="text-slate-500 text-lg">→</span>
            <span className="bg-indigo-500/20 border border-indigo-400/50 px-3 py-2 rounded">CAMPAIGN<br/><span className="text-slate-400">goal · flows · schedule · metrics</span></span>
            <span className="text-slate-500 text-lg">→</span>
            <span className="bg-emerald-500/20 border border-emerald-400/50 px-3 py-2 rounded">FLOWS<br/><span className="text-slate-400">event → steps</span></span>
            <span className="text-slate-500 text-lg">→</span>
            <span className="bg-amber-500/20 border border-amber-400/50 px-3 py-2 rounded">SERVICES<br/><span className="text-slate-400">email · sms · dunning · AI…</span></span>
            <span className="text-slate-500 text-lg">→</span>
            <span className="bg-pink-500/20 border border-pink-400/50 px-3 py-2 rounded">OUTCOMES<br/><span className="text-slate-400">per member</span></span>
            <span className="text-slate-500 text-lg">→</span>
            <span className="bg-purple-500/20 border border-purple-400/50 px-3 py-2 rounded">ANALYTICS<br/><span className="text-slate-400">before/after</span></span>
            <span className="text-slate-500 text-lg">→</span>
            <span className="bg-cyan-500/20 border border-cyan-400/50 px-3 py-2 rounded">REPORTS<br/><span className="text-slate-400">saved & shared</span></span>
          </div>
          <p className="text-slate-400 text-xs text-center mt-4">
            Loop back: report insights refine the segment criteria for the next campaign.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          {dataFlow.map((f) => (
            <div key={f.step} className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm">
              <div className="text-sm font-semibold text-indigo-600 mb-1">{f.step}</div>
              <p className="text-sm text-gray-600">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="py-10">
        <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">What you get</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {features.map((f) => (
            <div key={f.title} className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
              <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
              <p className="text-sm text-gray-600 mb-3">{f.desc}</p>
              <p className="text-xs text-gray-400 font-mono bg-gray-50 p-2 rounded">{f.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Quick links */}
      <section className="py-10 text-center">
        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/analytics" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:border-indigo-300 transition">Analytics</Link>
          <Link href="/campaigns" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:border-indigo-300 transition">Send a campaign</Link>
          <Link href="/events" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:border-indigo-300 transition">Ingest an event</Link>
          <Link href="/reports" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:border-indigo-300 transition">Generate report</Link>
        </div>
      </section>
    </div>
  );
}
