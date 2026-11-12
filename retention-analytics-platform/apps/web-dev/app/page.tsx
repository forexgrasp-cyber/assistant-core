"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/lib/api";

const architecture = [
  { layer: "API Gateway", desc: "41 FastAPI routes — auth, tenancy, idempotency, rate limiting, audit, metrics middleware", detail: "apps/api/main.py" },
  { layer: "Service Registry", desc: "24 services register actions; workflows invoke them by name — no silos", detail: "retention_analytics_core/service_registry.py" },
  { layer: "Workflow Engine", desc: "Durable step-by-step execution with event triggers and run history", detail: "retention_analytics_core/workflows/engine.py" },
  { layer: "Canonical Adapters", desc: "Secrets, idempotency, audit, rate limit, metrics, health — all consume shared-canonical-services", detail: "retention_analytics_core/canonical.py" },
  { layer: "Entity Kernel", desc: "Schema-as-data CRUD with tenant scoping on SQLAlchemy/PostgreSQL", detail: "retention_analytics_core/entities/kernel.py" },
  { layer: "Workers + MCP", desc: "Celery background tasks + FastMCP tools for AI assistants", detail: "apps/workers, apps/mcp_server" },
];

export default function Overview() {
  const [health, setHealth] = useState<any>(null);
  const [services, setServices] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);

  useEffect(() => {
    apiGet("/health").then(setHealth).catch(() => {});
    apiGet("/services").then((d: any) => setServices(d.services ?? [])).catch(() => {});
    apiGet("/workflows").then((d: any) => setWorkflows(d.workflows ?? [])).catch(() => {});
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-10">
      {/* Hero */}
      <section className="text-center py-12">
        <div className="inline-block bg-emerald-100 text-emerald-700 text-xs font-semibold px-3 py-1 rounded-full mb-4">
          Platform internals
        </div>
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Developer Console</h1>
        <p className="text-lg text-gray-500 max-w-2xl mx-auto">
          Explore the platform: {services.length || "…"} services, {workflows.length || "…"} workflows,
          41 API endpoints. Invoke any service action, run any pipeline, inspect entities.
        </p>
      </section>

      {/* Live stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Services" value={services.length} />
        <Stat label="Workflows" value={workflows.length} />
        <Stat label="API Endpoints" value={41} />
        <Stat label="Status" value={health?.status ?? "…"} green />
      </div>

      {/* Architecture */}
      <section>
        <h2 className="text-xl font-bold text-gray-900 mb-4">Architecture</h2>
        <div className="space-y-3">
          {architecture.map((a, i) => (
            <div key={a.layer} className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 flex gap-4">
              <div className="text-2xl font-bold text-gray-200 w-8">{i + 1}</div>
              <div>
                <h3 className="font-semibold text-gray-900">{a.layer}</h3>
                <p className="text-sm text-gray-600">{a.desc}</p>
                <p className="text-xs text-gray-400 font-mono mt-1">{a.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Quick nav */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Link href="/services" className="bg-white border border-gray-200 rounded-lg p-4 hover:border-emerald-400 transition">
          <p className="font-medium text-gray-900 text-sm">Service Explorer</p>
          <p className="text-xs text-gray-400 mt-1">Invoke any action with JSON input</p>
        </Link>
        <Link href="/workflows" className="bg-white border border-gray-200 rounded-lg p-4 hover:border-emerald-400 transition">
          <p className="font-medium text-gray-900 text-sm">Workflow Runner</p>
          <p className="text-xs text-gray-400 mt-1">See pipelines, run them live</p>
        </Link>
        <Link href="/api-explorer" className="bg-white border border-gray-200 rounded-lg p-4 hover:border-emerald-400 transition">
          <p className="font-medium text-gray-900 text-sm">API Explorer</p>
          <p className="text-xs text-gray-400 mt-1">All 41 endpoints by domain</p>
        </Link>
        <a href="http://127.0.0.1:47319/docs" target="_blank" className="bg-slate-900 text-white rounded-lg p-4 hover:bg-slate-800 transition">
          <p className="font-medium text-sm">Swagger UI</p>
          <p className="text-xs text-slate-400 mt-1">Interactive OpenAPI docs ↗</p>
        </a>
      </section>
    </div>
  );
}

function Stat({ label, value, green }: { label: string; value: any; green?: boolean }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 text-center">
      <p className={`text-2xl font-bold ${green ? "text-green-600" : "text-gray-900"}`}>{value}</p>
      <p className="text-xs text-gray-400 uppercase tracking-wide mt-1">{label}</p>
    </div>
  );
}
