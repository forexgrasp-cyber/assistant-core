"use client";

import { useState } from "react";

const endpointGroups = [
  {
    domain: "Observability",
    color: "bg-gray-100 text-gray-700",
    endpoints: [
      { method: "GET", path: "/", desc: "API root — service info, endpoint map" },
      { method: "GET", path: "/health", desc: "Liveness + registered services/workflows" },
      { method: "GET", path: "/health/ready", desc: "Readiness probe (secrets, ledger)" },
      { method: "GET", path: "/health/live", desc: "Liveness only" },
      { method: "GET", path: "/metrics", desc: "Prometheus metrics" },
      { method: "GET", path: "/robots.txt", desc: "SEO robots" },
      { method: "GET", path: "/sitemap.xml", desc: "SEO sitemap" },
      { method: "GET", path: "/llms.txt", desc: "LLM discovery file" },
    ],
  },
  {
    domain: "Entities (CRUD)",
    color: "bg-blue-100 text-blue-700",
    endpoints: [
      { method: "POST", path: "/api/v1/entities/{schema}", desc: "Create record. Body: {schema_id, data}" },
      { method: "GET", path: "/api/v1/entities/{schema}", desc: "List records (tenant-scoped)" },
      { method: "GET", path: "/api/v1/entities/{schema}/{id}", desc: "Get one record" },
      { method: "PATCH", path: "/api/v1/entities/{schema}/{id}", desc: "Update record. Body: {schema_id, record_id, data}" },
      { method: "DELETE", path: "/api/v1/entities/{schema}/{id}", desc: "Delete record" },
    ],
  },
  {
    domain: "Events & Webhooks",
    color: "bg-amber-100 text-amber-700",
    endpoints: [
      { method: "POST", path: "/api/v1/events", desc: "Ingest event → triggers workflows. Idempotent via idempotency_key" },
      { method: "POST", path: "/api/v1/webhooks/{provider}", desc: "Inbound webhook, HMAC-verified, idempotent" },
      { method: "POST", path: "/api/v1/webhooks/payments/{provider}", desc: "Payment webhook (Stripe etc.), signature + idempotency" },
      { method: "POST", path: "/api/v1/webhooks/out/dispatch", desc: "Dispatch outbound webhook with DLQ" },
    ],
  },
  {
    domain: "Services & Workflows",
    color: "bg-emerald-100 text-emerald-700",
    endpoints: [
      { method: "GET", path: "/api/v1/services", desc: "List 24 registered services + actions" },
      { method: "POST", path: "/api/v1/services/{svc}/actions/{action}", desc: "Invoke any service action with JSON payload" },
      { method: "GET", path: "/api/v1/workflows", desc: "List workflow definitions" },
      { method: "POST", path: "/api/v1/workflows/{id}/run", desc: "Run a workflow. Body: {context}" },
      { method: "GET", path: "/api/v1/workflows/runs/{run_id}", desc: "Get workflow run details" },
    ],
  },
  {
    domain: "Commerce & Billing",
    color: "bg-purple-100 text-purple-700",
    endpoints: [
      { method: "GET", path: "/api/v1/payments/providers", desc: "List available payment providers" },
      { method: "POST", path: "/api/v1/payments", desc: "Create payment via provider registry" },
      { method: "GET", path: "/api/v1/entitlements", desc: "List tenant entitlements" },
      { method: "POST", path: "/api/v1/quota/check", desc: "Check quota for a resource" },
    ],
  },
  {
    domain: "Platform Services",
    color: "bg-indigo-100 text-indigo-700",
    endpoints: [
      { method: "GET", path: "/api/v1/feature-flags/{name}", desc: "Check feature flag" },
      { method: "POST", path: "/api/v1/sessions", desc: "Create session" },
      { method: "GET", path: "/api/v1/profile", desc: "Get user profile" },
      { method: "POST", path: "/api/v1/notifications", desc: "Send notification" },
      { method: "GET/POST", path: "/api/v1/organizations/invitations", desc: "List / create org invitations" },
      { method: "POST", path: "/api/v1/support/tickets", desc: "Create support ticket" },
      { method: "POST", path: "/api/v1/feedback", desc: "Submit NPS feedback" },
      { method: "GET", path: "/api/v1/monetization/paths", desc: "List monetization paths" },
      { method: "POST", path: "/api/v1/leads", desc: "Capture a lead" },
    ],
  },
  {
    domain: "Reports",
    color: "bg-pink-100 text-pink-700",
    endpoints: [
      { method: "POST", path: "/api/v1/reports?format=json|pdf|html|csv", desc: "Generate report" },
      { method: "GET", path: "/api/v1/reports/{id}/download", desc: "Download generated report" },
    ],
  },
];

const methodColors: Record<string, string> = {
  GET: "bg-green-100 text-green-700",
  POST: "bg-blue-100 text-blue-700",
  PATCH: "bg-amber-100 text-amber-700",
  DELETE: "bg-red-100 text-red-700",
  "GET/POST": "bg-purple-100 text-purple-700",
};

export default function ApiExplorer() {
  const [open, setOpen] = useState<string | null>("Observability");

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">API Explorer</h1>
        <p className="text-gray-500 text-sm mt-1">
          All 41 endpoints grouped by domain. Base URL: <code className="font-mono text-xs bg-gray-100 px-1 rounded">http://127.0.0.1:47319</code>.
          Interactive docs: <a href="http://127.0.0.1:47319/docs" target="_blank" className="text-emerald-600 hover:underline">Swagger UI ↗</a>
        </p>
      </div>

      <div className="space-y-2">
        {endpointGroups.map((g) => (
          <div key={g.domain} className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <button
              onClick={() => setOpen(open === g.domain ? null : g.domain)}
              className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
            >
              <div className="flex items-center gap-3">
                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${g.color}`}>{g.domain}</span>
                <span className="text-xs text-gray-400">{g.endpoints.length} endpoints</span>
              </div>
              <span className="text-gray-400">{open === g.domain ? "▲" : "▼"}</span>
            </button>
            {open === g.domain && (
              <div className="border-t border-gray-100 divide-y divide-gray-50">
                {g.endpoints.map((e) => (
                  <div key={e.path} className="flex items-start gap-3 px-5 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-bold font-mono shrink-0 ${methodColors[e.method] ?? "bg-gray-100"}`}>
                      {e.method}
                    </span>
                    <div>
                      <code className="text-sm font-mono text-gray-900">{e.path}</code>
                      <p className="text-xs text-gray-500 mt-0.5">{e.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
