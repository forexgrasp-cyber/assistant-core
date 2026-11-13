import Link from "next/link";
import AnimBoot from "@/components/AnimBoot";

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

const STATS = [
  { value: 24, suffix: "", label: "registered services" },
  { value: 4, suffix: "", label: "workflows" },
  { value: 41, suffix: "", label: "API endpoints" },
  { value: 92, suffix: "%", label: "avg retention lift" },
];

const LOGOS = ["Acme Retail", "Northwind", "Globex", "Initech", "Umbrella", "Stark Ind.", "Wayne Co", "Soylent"];

export default function Landing() {
  return (
    <div className="max-w-5xl mx-auto ra-landing" data-page-root>
      <AnimBoot />

      <style>{`
        .ra-landing .hero{position:relative;border-radius:24px;padding:56px 40px;margin-top:8px;
          background:linear-gradient(140deg,#0b0d1f 0%,#141031 55%,#1b1140 100%);
          border:1px solid rgba(129,140,248,.25);overflow:hidden}
        .ra-landing .hero::before{content:"";position:absolute;inset:-40% -20% auto;height:70%;
          background:radial-gradient(closest-side,rgba(129,140,248,.35),transparent);pointer-events:none}
        .ra-landing .hero h1{color:#fff;font-size:clamp(2.2rem,5vw,3.6rem);line-height:1.05;letter-spacing:-.02em;font-weight:800;margin:.8rem 0 1rem}
        .ra-landing .hero p{color:#a5b0d8;font-size:1.1rem;max-width:36rem}
        .ra-landing .chart-card{margin-top:28px;background:rgba(10,12,30,.7);border:1px solid rgba(129,140,248,.25);
          border-radius:16px;padding:18px;position:relative;overflow:hidden}
        .ra-landing .chart-video{position:absolute;right:10px;bottom:10px;width:150px;height:84px;object-fit:cover;
          border-radius:10px;border:2px solid rgba(129,140,248,.5);opacity:.9}
        .ra-landing .stat .num{color:#fff;font-size:1.6rem;font-weight:800;font-variant-numeric:tabular-nums}
        .ra-landing .stat .lbl{color:#8b93bd;font-size:.78rem}
        .ra-landing .logo-marquee{border-block:1px solid #e5e7eb;padding:12px 0;margin:40px 0}
        .ra-landing .logo-marquee .dm-item{color:#6b7280;font-weight:700}
        .ra-landing h2{color:#111827}
        .ra-landing .pipe-track{background:#0b0d1f;border-radius:20px;padding:28px;margin-top:8px}
        .ra-landing .pipe-track .chip{background:rgba(129,140,248,.15);border:1px solid rgba(129,140,248,.4);
          color:#e0e4ff;border-radius:10px;padding:10px 14px;font:12px/1.3 ui-monospace,monospace}
        .ra-landing .step-ico{font-size:1.8rem}
        @media (prefers-reduced-motion:reduce){.ra-landing .hero::before{display:none}}
      `}</style>

      {/* Hero */}
      <section className="hero text-left">
        <div className="inline-block text-xs font-semibold px-3 py-1 rounded-full mb-4 anim-glow-box"
          style={{ background: "rgba(129,140,248,.15)", color: "#a5b4fc", border: "1px solid rgba(129,140,248,.4)" }}>
          Multi-tenant retention platform
        </div>
        <h1 data-split-init>Stop churn before it happens.</h1>
        <p data-text-fade-in data-scroll-read>
          Automated retention workflows, multi-channel campaigns, and real-time analytics —
          every service wired into pipelines, not silos. 24 services. 4 workflows. 41 API endpoints.
        </p>
        <div className="flex gap-3 mt-6 flex-wrap">
          <Link href="/campaigns" className="px-6 py-3 rounded-lg font-medium text-white anim-btn" data-btn-hover data-cursor="Go"
            style={{ background: "#6366f1" }}>Create a Campaign</Link>
          <Link href="/how-it-works" className="px-6 py-3 rounded-lg font-medium border border-slate-600 text-slate-200" data-btn-hover>How it works</Link>
          <Link href="/dashboard" className="px-6 py-3 rounded-lg font-medium border border-slate-600 text-slate-200" data-btn-hover>Open Dashboard</Link>
        </div>

        {/* animated retention chart */}
        <div className="chart-card anim-tilt-scene">
          <div className="anim-tilt" data-tilt-max="4">
            <video className="chart-video" src="/brand/intro.mp4" poster="/brand/intro-poster.jpg" muted autoPlay loop playsInline aria-hidden="true" />
            <svg viewBox="0 0 640 220" width="100%" aria-label="Retention rising, churn falling">
              <defs>
                <linearGradient id="retFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="#34d399" stopOpacity=".35" />
                  <stop offset="1" stopColor="#34d399" stopOpacity="0" />
                </linearGradient>
              </defs>
              {[40, 80, 120, 160].map((y) => (
                <line key={y} x1="20" y1={y} x2="620" y2={y} stroke="#232a52" strokeWidth="1" />
              ))}
              <path className="anim-svg-draw" d="M20,190 C160,185 260,120 380,80 C480,50 560,35 620,30"
                fill="none" stroke="#34d399" strokeWidth="4" strokeLinecap="round" />
              <path d="M20,190 C160,185 260,120 380,80 C480,50 560,35 620,30 L620,210 L20,210 Z" fill="url(#retFill)" opacity=".6" />
              <path className="anim-svg-draw" d="M20,60 C160,70 300,120 420,160 C500,185 570,195 620,198"
                fill="none" stroke="#fb7185" strokeWidth="3" strokeDasharray="7 6" strokeLinecap="round" />
              <circle cx="620" cy="30" r="6" fill="#34d399" />
              <circle cx="620" cy="198" r="5" fill="#fb7185" />
              <text x="500" y="20" fill="#34d399" fontSize="13" fontFamily="ui-monospace,monospace">retention 92%</text>
              <text x="470" y="215" fill="#fb7185" fontSize="13" fontFamily="ui-monospace,monospace">churn 8%</text>
            </svg>
          </div>
        </div>

        <div className="flex gap-8 mt-6 flex-wrap">
          {STATS.map((s) => (
            <div className="stat" key={s.label}>
              <div className="num anim-count" data-count={s.value} data-suffix={s.suffix}>0</div>
              <div className="lbl">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* logo marquee */}
      <div className="logo-marquee anim-marquee" aria-hidden="true">
        <div className="anim-marquee-track" style={{ ["--marquee-duration" as string]: "28s" }}>
          {LOGOS.map((l) => (
            <span className="dm-item" key={l}>{l}</span>
          ))}
        </div>
      </div>

      {/* The unified model — pinned story */}
      <section className="py-10">
        <h2 className="text-2xl font-bold mb-2 text-center" data-wipe>The unified model</h2>
        <p className="text-gray-500 text-center mb-6 max-w-2xl mx-auto" data-text-fade-in>
          One loop connects everything. You don't manage services in isolation — you run campaigns that tie targets, automations, and measurement together.
        </p>

        <div className="anim-story" aria-label="Pipeline story">
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <div className="anim-story-progress">
              <span className="anim-story-progress-line" /><span className="anim-story-progress-line" /><span className="anim-story-progress-line" />
            </div>
            <span className="anim-story-counter">1 / 3</span>
          </div>
          {/* Beats flow in normal document order: absolutely stacked steps
              share one bounding box, so every ScrollTrigger fired at the same
              scroll position and all beats activated at once. */}
          <div className="anim-story-track">
            <div className="anim-story-pin pipe-track">
              <div className="anim-story-step">
                <div className="anim-story-step-content" style={{ textAlign: "center" }}>
                  <span className="step-ico">📥</span>
                  <h3 className="anim-glow" style={{ color: "#fff", fontSize: "1.8rem" }}>Events in.</h3>
                  <p style={{ color: "#a5b0d8" }}>Every customer action lands in one idempotent stream.</p>
                </div>
              </div>
              <div className="anim-story-step">
                <div className="anim-story-step-content" style={{ textAlign: "center" }}>
                  <span className="step-ico">⚙️</span>
                  <h3 className="anim-glow" style={{ color: "#fff", fontSize: "1.8rem" }}>Workflows fire.</h3>
                  <p style={{ color: "#a5b0d8" }}>Triggers match events to durable, step-by-step pipelines.</p>
                </div>
              </div>
              <div className="anim-story-step">
                <div className="anim-story-step-content" style={{ textAlign: "center" }}>
                  <span className="step-ico">📈</span>
                  <h3 className="anim-glow" style={{ color: "#fff", fontSize: "1.8rem" }}>Retention climbs.</h3>
                  <p style={{ color: "#a5b0d8" }}>Services send, measure and report — the loop closes.</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="pipe-track">
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="chip">SEGMENT<br /><span style={{ opacity: .6 }}>who — criteria</span></span>
            <span style={{ color: "#64748b" }}>→</span>
            <span className="chip">CAMPAIGN<br /><span style={{ opacity: .6 }}>goal · flows · schedule</span></span>
            <span style={{ color: "#64748b" }}>→</span>
            <span className="chip">FLOWS<br /><span style={{ opacity: .6 }}>event → steps</span></span>
            <span style={{ color: "#64748b" }}>→</span>
            <span className="chip">SERVICES<br /><span style={{ opacity: .6 }}>email · sms · dunning · AI</span></span>
            <span style={{ color: "#64748b" }}>→</span>
            <span className="chip">OUTCOMES<br /><span style={{ opacity: .6 }}>per member</span></span>
            <span style={{ color: "#64748b" }}>→</span>
            <span className="chip">ANALYTICS<br /><span style={{ opacity: .6 }}>before/after</span></span>
            <span style={{ color: "#64748b" }}>→</span>
            <span className="chip">REPORTS<br /><span style={{ opacity: .6 }}>saved & shared</span></span>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4" data-reveal-group>
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
        <h2 className="text-2xl font-bold mb-6 text-center" data-wipe>What you get</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6" data-reveal-group>
          {features.map((f) => (
            <div key={f.title} className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm anim-tilt-scene anim-clip">
              <div className="anim-tilt" data-tilt-max="5">
                <h3 className="font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-600 mb-3">{f.desc}</p>
                <p className="text-xs text-gray-400 font-mono bg-gray-50 p-2 rounded">{f.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Quick links */}
      <section className="py-10 text-center">
        <div className="flex flex-wrap justify-center gap-3">
          <Link href="/analytics" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700" data-btn-hover>Analytics</Link>
          <Link href="/campaigns" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700" data-btn-hover>Send a campaign</Link>
          <Link href="/events" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700" data-btn-hover>Ingest an event</Link>
          <Link href="/reports" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700" data-btn-hover>Generate report</Link>
        </div>
      </section>

      {/* CTA */}
      <section className="py-14 text-center">
        <h2 className="anim-glow text-3xl font-extrabold mb-4" data-split-init>Ready to keep more customers?</h2>
        <Link href="/campaigns" className="px-6 py-3 rounded-lg font-medium text-white" data-btn-hover data-cursor="Start"
          style={{ background: "#6366f1" }}>Create your first campaign</Link>
      </section>
    </div>
  );
}
