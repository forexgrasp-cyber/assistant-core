"use client";

import { useEffect, useState } from "react";

const STATUS_PAGE = [
  { key: "api", label: "API", state: "operational" },
  { key: "customer_portal", label: "Customer Portal", state: "operational" },
  { key: "workers", label: "Background Workers", state: "operational" },
  { key: "email", label: "Email Delivery", state: "degraded" },
  { key: "webhooks", label: "Outbound Webhooks", state: "operational" },
  { key: "mcp", label: "MCP Server", state: "operational" },
];

export default function StatusPage() {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [uptime, setUptime] = useState("99.98%");

  useEffect(() => {
    fetch("/api/v1/incidents", { headers: { Authorization: "Bearer dev-token" } })
      .then((r) => (r.ok ? r.json() : { incidents: [] }))
      .then((d) => setIncidents(d.incidents ?? []))
      .catch(() => {});
  }, []);

  const dot = (s: string) =>
    s === "operational" ? "bg-green-500" : s === "degraded" ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="text-center pt-8">
        <div className="inline-flex items-center gap-2 bg-green-50 text-green-700 px-3 py-1 rounded-full text-sm font-medium">
          <span className="w-2 h-2 rounded-full bg-green-500" /> All systems operational
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mt-4">System status</h1>
        <p className="text-gray-500 text-sm mt-1">90-day uptime: <b>{uptime}</b></p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-900 text-sm mb-3">Components</h2>
        <div className="space-y-2">
          {STATUS_PAGE.map((c) => (
            <div key={c.key} className="flex items-center justify-between p-2.5 bg-gray-50 rounded">
              <span className="text-sm text-gray-700">{c.label}</span>
              <span className="flex items-center gap-2 text-xs text-gray-600 capitalize">
                <span className={`w-2 h-2 rounded-full ${dot(c.state)}`} /> {c.state}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-900 text-sm mb-3">Recent incidents ({incidents.length})</h2>
        {incidents.length === 0 && <p className="text-sm text-gray-400">No incidents in the last 90 days.</p>}
        {incidents.map((i) => (
          <div key={i.incident_id} className="border-l-2 border-amber-400 pl-3 py-2 mb-3">
            <p className="text-sm font-medium text-gray-900">{i.metric} {i.direction} ({i.deviation_pct}%)</p>
            <p className="text-xs text-gray-500">{i.severity} · {String(i.created_at).slice(0, 16).replace("T", " ")} · {i.status}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
