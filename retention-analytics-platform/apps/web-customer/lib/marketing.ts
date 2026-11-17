import {
  BarChart3,
  Bell,
  Blocks,
  GitBranch,
  LineChart,
  Plug,
  Send,
  ShieldCheck,
  Sparkles,
  Users,
  Wallet,
  Workflow,
} from "lucide-react";

export type FeatureItem = { name: string; description: string };

export type FeatureGroup = {
  id: string;
  name: string;
  tagline: string;
  icon: typeof Users;
  items: FeatureItem[];
};

export const FEATURE_GROUPS: FeatureGroup[] = [
  {
    id: "customers",
    name: "Know your customers",
    tagline: "One live record of every customer, with the signals that predict churn.",
    icon: Users,
    items: [
      {
        name: "Customer 360",
        description: "Plan, MRR, LTV, health, tags, service history and a full timeline per customer.",
      },
      {
        name: "Live segments",
        description: "Filter on plan, value tier, health, churn risk, RFM band or next service due.",
      },
      {
        name: "Computed fields",
        description: "Days until due, LTV band, value tier and risk level recalculated as data changes.",
      },
      {
        name: "Health scores",
        description: "Usage, support and payment signals combined into a 0–100 health score.",
      },
      {
        name: "Churn prediction",
        description: "Risk ranking from usage drop, open tickets, payment failures and NPS.",
      },
      {
        name: "Import & map",
        description: "Bring customers in by CSV, API or connector and map the columns you already have.",
      },
    ],
  },
  {
    id: "automation",
    name: "Act automatically",
    tagline: "Retention campaigns that fire on real events and finish every step durably.",
    icon: Workflow,
    items: [
      {
        name: "Campaigns",
        description: "Goal, target segment, flows, schedule and success metrics — run once, daily or on event.",
      },
      {
        name: "37 ready-made flows",
        description: "Churn prevention, cart recovery, dunning, win-back, welcome, NPS and renewal reminders.",
      },
      {
        name: "Visual flow builder",
        description: "Event to steps to services, with validation and publish before it goes live.",
      },
      {
        name: "Email, SMS & push",
        description: "Every send goes through a registered service, so it is traceable and auditable.",
      },
      {
        name: "Dunning & payment recovery",
        description: "Retry ladders, reminders and saved offers for failed subscription payments.",
      },
      {
        name: "Save & cancel flows",
        description: "Exit surveys, downgrade offers and cancel confirmations that keep the customer.",
      },
      {
        name: "Journeys & sequences",
        description: "Multi-step journeys for onboarding, expansion and reactivation.",
      },
      {
        name: "Experiments & A/B tests",
        description: "Test subject lines, offers and timing, then pick the winner automatically.",
      },
    ],
  },
  {
    id: "analytics",
    name: "Prove the impact",
    tagline: "Retention, revenue and per-campaign outcomes measured before and after.",
    icon: LineChart,
    items: [
      {
        name: "Retention & churn",
        description: "30-day retention rate, churn rate and movement over time.",
      },
      {
        name: "Revenue metrics",
        description: "MRR, ARR, GRR, NRR, ARPU, LTV and CAC with cohort breakdowns.",
      },
      {
        name: "Cohorts & RFM",
        description: "Cohort retention tables and recency-frequency-monument movement.",
      },
      {
        name: "Campaign attribution",
        description: "What each campaign did for revenue, with multi-touch attribution.",
      },
      {
        name: "Benchmarks",
        description: "Compare churn, NRR and LTV against industry baselines.",
      },
      {
        name: "Reports & exports",
        description: "Saved reports as PDF, HTML, CSV or JSON, shareable with your team or clients.",
      },
      {
        name: "White-label client views",
        description: "Tokenised dashboards your clients can open without a login.",
      },
    ],
  },
  {
    id: "operations",
    name: "Run the business",
    tagline: "A command centre for customer success, renewals and alerts.",
    icon: Bell,
    items: [
      {
        name: "Success Ops command center",
        description: "Renewal risk, open alerts, churned customers and plan coverage in one view.",
      },
      {
        name: "Alerts & playbooks",
        description: "Automated playbooks fire when a health, payment or usage threshold is crossed.",
      },
      {
        name: "Renewal forecasting",
        description: "Forecast renewals, expansion and risk before the quarter closes.",
      },
      {
        name: "Anomaly detection",
        description: "Spot spikes and drops in usage, spend and churn before they reach the board.",
      },
      {
        name: "Goals & presets",
        description: "Track retention goals and apply proven segment presets in one click.",
      },
      {
        name: "Agency roster",
        description: "Manage client rosters, roles and platform access for an agency team.",
      },
    ],
  },
  {
    id: "integrations",
    name: "Connect everything",
    tagline: "Your data in, your tools out — with an auditable path in between.",
    icon: Plug,
    items: [
      {
        name: "REST API",
        description: "Every registered action is callable, so your stack can drive retention directly.",
      },
      {
        name: "MCP server",
        description: "Expose retention analytics to AI agents over the Model Context Protocol.",
      },
      {
        name: "Webhooks",
        description: "Outbound webhooks with retry and a dead-letter queue for every important event.",
      },
      {
        name: "Connectors",
        description: "Pull customer and event data from the tools you already run.",
      },
      {
        name: "Integrations catalog",
        description: "Slack, marketing platforms and payment providers from one catalog.",
      },
      {
        name: "API keys & audit log",
        description: "Scoped keys, rate limits and a hash-chained audit trail for every change.",
      },
      {
        name: "Multi-tenant isolation",
        description: "Every request is scoped to the authenticated tenant, enforced at the API boundary.",
      },
    ],
  },
];

export type Benefit = { title: string; description: string; icon: typeof Users };

export const BENEFITS: Benefit[] = [
  {
    title: "Recover revenue that used to leak",
    description:
      "Failed payments, expiring plans and silent churn are chased automatically — before the customer notices.",
    icon: Wallet,
  },
  {
    title: "Stop churn before it happens",
    description:
      "Health scores and churn risk tell you who needs attention this week, not six months from now.",
    icon: ShieldCheck,
  },
  {
    title: "Prove what actually worked",
    description:
      "Every campaign reports before-and-after outcomes, so retention work is a budget line, not a hunch.",
    icon: BarChart3,
  },
  {
    title: "Replace six disconnected tools",
    description:
      "Segments, campaigns, flows, messaging and analytics share one model, so nothing lives in a silo.",
    icon: Blocks,
  },
  {
    title: "Scale without adding headcount",
    description:
      "37 ready-made flows and 400+ automatable actions run the repetitive retention work for you.",
    icon: GitBranch,
  },
  {
    title: "Serve every client from one platform",
    description:
      "White-label client views, a shared roster and strict tenant isolation keep agency data separate.",
    icon: Send,
  },
];

export type Tier = {
  id: string;
  name: string;
  price: string;
  cadence: string;
  summary: string;
  featured: boolean;
  features: string[];
  cta: string;
};

export const TIERS: Tier[] = [
  {
    id: "starter",
    name: "Starter",
    price: "$49",
    cadence: "per month",
    summary: "For a single subscription business getting its first retention loop running.",
    featured: false,
    features: [
      "Up to 1,000 tracked customers",
      "3 active campaigns",
      "Core retention flows: churn prevention, welcome, win-back",
      "Email channel with templates",
      "Retention, churn and cohort analytics",
      "Standard PDF and CSV reports",
      "1 seat",
    ],
    cta: "Start with Starter",
  },
  {
    id: "growth",
    name: "Growth",
    price: "$149",
    cadence: "per month",
    summary: "For teams running retention as a channel with real volume and real revenue.",
    featured: true,
    features: [
      "Up to 10,000 tracked customers",
      "Unlimited campaigns and flows",
      "Email, SMS and push channels",
      "Dunning, payment recovery and cancel-save flows",
      "MRR, NRR, LTV, RFM and campaign attribution",
      "Experiments, benchmarks and alerts",
      "5 seats",
    ],
    cta: "Start with Growth",
  },
  {
    id: "scale",
    name: "Scale",
    price: "$399",
    cadence: "per month",
    summary: "For agencies and multi-brand teams running retention for many clients.",
    featured: false,
    features: [
      "Up to 50,000 tracked customers",
      "Everything in Growth",
      "White-label client dashboards",
      "Agency roster and client workspaces",
      "API keys, webhooks and MCP access",
      "Saved report scheduling and exports",
      "15 seats",
    ],
    cta: "Start with Scale",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "Custom",
    cadence: "annual agreement",
    summary: "For regulated teams that need residency, SSO and a contractual SLA.",
    featured: false,
    features: [
      "Unlimited customers and seats",
      "Data residency (EU / US)",
      "SSO and role-based access control",
      "Custom retention workflows and SLAs",
      "Dedicated onboarding and support",
      "Quarterly retention reviews",
    ],
    cta: "Talk to us",
  },
];

export type Step = { step: string; name: string; description: string };

export const STEPS: Step[] = [
  {
    step: "01",
    name: "Connect your data",
    description:
      "Import customers and events by CSV, API or connector. Your existing fields map straight onto the customer model.",
  },
  {
    step: "02",
    name: "Segment your customers",
    description:
      "Build live audiences on plan, value, health, churn risk or next service due — no SQL required.",
  },
  {
    step: "03",
    name: "Automate the response",
    description:
      "Pick a flow, choose a trigger and schedule. Every step is durable, idempotent and audited.",
  },
  {
    step: "04",
    name: "Measure the outcome",
    description:
      "Watch retention, churn and revenue move, and see the before-and-after for each campaign.",
  },
];

export type Faq = { question: string; answer: string };

export const FAQS: Faq[] = [
  {
    question: "How long does it take to launch?",
    answer:
      "Most teams import their customer list, pick one segment and run a first campaign the same day. Flows, integrations and reporting deepen from there.",
  },
  {
    question: "Do we need an engineer to set it up?",
    answer:
      "No. Campaigns, segments and flows are configured in the portal. The API, webhooks and MCP server are there when you want to go deeper.",
  },
  {
    question: "Which tools does this replace?",
    answer:
      "Most teams use it to consolidate campaign tooling, churn dashboards, payment-recovery sequences and reporting into one retention loop.",
  },
  {
    question: "Where does our data live, and is it isolated?",
    answer:
      "Every request is scoped to the authenticated tenant and cross-tenant access is rejected at the API boundary. Enterprise plans add regional data residency.",
  },
  {
    question: "Can we manage several clients?",
    answer:
      "Yes. Scale and Enterprise include an agency roster, per-client workspaces and white-label dashboards clients can open without a login.",
  },
  {
    question: "What happens if we exceed our plan?",
    answer:
      "We contact you before anything is throttled. Limits apply to tracked customers and seats, never to the history you have already collected.",
  },
];

export const STATS = [
  { value: "37", label: "ready-made retention flows" },
  { value: "421", label: "automatable service actions" },
  { value: "100+", label: "connected services" },
  { value: "307", label: "API routes" },
];

export const LOOP = [
  { step: "Event", detail: "A customer action enters one idempotent stream" },
  { step: "Trigger", detail: "The event matches a workflow trigger" },
  { step: "Pipeline", detail: "Steps run in order: render, send, score" },
  { step: "Service", detail: "Each step calls a registered service action" },
  { step: "Persist", detail: "Outbox, metrics and audit log are written" },
  { step: "Report", detail: "The outcome surfaces in analytics and reports" },
];
