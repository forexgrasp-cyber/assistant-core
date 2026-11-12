"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiGet, apiPost } from "@/lib/api";

interface Health {
  status: string;
  services: string[];
  workflows: string[];
  environment: string;
}

interface WorkflowInfo {
  id: string;
  name: string;
  trigger_event: string;
  steps: { id: string; service: string; action: string }[];
  active: boolean;
}

interface RetentionResult {
  retention_rate_30d: number;
  churn_rate_30d: number;
  retained_customers: number;
  previous_window_customers: number;
  current_window_customers: number;
  computed_at: string;
}

export default function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowInfo[]>([]);
  const [retention, setRetention] = useState<RetentionResult | null>(null);
  const [services, setServices] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet("/health")
      .then((d: Health) => setHealth(d))
      .catch((e) => setError(e.message));
    apiGet("/workflows")
      .then((d: any) => setWorkflows(d.workflows ?? []))
      .catch(() => {});
    apiGet("/services")
      .then((d: any) => setServices(d.services ?? []))
      .catch(() => {});
    apiPost("/services/analytics.metric/actions/compute_retention", {
      payload: { tenant_id: "00000000-0000-0000-0000-000000000001" },
    })
      .then((d: any) => setRetention(d.result))
      .catch(() => {});
  }, []);

  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">
          Live platform status and retention metrics for your tenant.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
          API error: {error}
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Status" value={health?.status ?? "…"} color="text-green-600" />
        <StatCard label="Services" value={String(health?.services?.length ?? services.length ?? "…")} />
        <StatCard label="Workflows" value={String(workflows.length || health?.workflows?.length || "…")} />
        <StatCard
          label="30d Retention"
          value={retention ? pct(retention.retention_rate_30d) : "…"}
          color={retention && retention.retention_rate_30d > 0.5 ? "text-green-600" : "text-gray-900"}
        />
      </div>

      {/* Retention detail */}
      {retention && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Retention (30-day window)</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-400">Retention rate</p>
              <p className="text-xl font-bold text-green-600">{pct(retention.retention_rate_30d)}</p>
            </div>
            <div>
              <p className="text-gray-400">Churn rate</p>
              <p className="text-xl font-bold text-red-500">{pct(retention.churn_rate_30d)}</p>
            </div>
            <div>
              <p className="text-gray-400">Retained customers</p>
              <p className="text-xl font-bold text-gray-900">{retention.retained_customers}</p>
            </div>
            <div>
              <p className="text-gray-400">Active this window</p>
              <p className="text-xl font-bold text-gray-900">{retention.current_window_customers}</p>
            </div>
          </div>
          <div className="mt-4">
            <div className="flex justify-between text-xs text-gray-400 mb-1">
              <span>Retention</span><span>Churn</span>
            </div>
            <div className="flex h-3 rounded-full overflow-hidden bg-gray-100">
              <div
                className="bg-green-500 h-full transition-all"
                style={{ width: pct(retention.retention_rate_30d) }}
              />
              <div
                className="bg-red-400 h-full transition-all"
                style={{ width: pct(retention.churn_rate_30d) }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Active workflows */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">Active Workflows</h2>
          <Link href="/flows" className="text-sm text-indigo-600 hover:underline">View all →</Link>
        </div>
        <div className="space-y-3">
          {workflows.map((w) => (
            <div key={w.id} className="flex items-center gap-4 p-3 bg-gray-50 rounded">
              <span className={`w-2 h-2 rounded-full ${w.active ? "bg-green-500" : "bg-gray-300"}`} />
              <div className="flex-1">
                <p className="font-medium text-sm text-gray-900">{w.name}</p>
                <p className="text-xs text-gray-400 font-mono">trigger: {w.trigger_event}</p>
              </div>
              <div className="flex items-center gap-1 text-xs text-gray-500">
                {w.steps.map((s, i) => (
                  <span key={s.id} className="flex items-center gap-1">
                    {i > 0 && <span className="text-gray-300">→</span>}
                    <span className="bg-white border border-gray-200 px-2 py-0.5 rounded font-mono">
                      {s.service}.{s.action}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          ))}
          {workflows.length === 0 && <p className="text-sm text-gray-400">Loading workflows…</p>}
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Link href="/campaigns" className="bg-white border border-gray-200 rounded-lg p-4 text-center hover:border-indigo-300 transition">
          <p className="text-sm font-medium text-gray-900">Send Campaign</p>
          <p className="text-xs text-gray-400 mt-1">email / sms / push</p>
        </Link>
        <Link href="/events" className="bg-white border border-gray-200 rounded-lg p-4 text-center hover:border-indigo-300 transition">
          <p className="text-sm font-medium text-gray-900">Ingest Event</p>
          <p className="text-xs text-gray-400 mt-1">triggers workflows</p>
        </Link>
        <Link href="/analytics" className="bg-white border border-gray-200 rounded-lg p-4 text-center hover:border-indigo-300 transition">
          <p className="text-sm font-medium text-gray-900">Analytics</p>
          <p className="text-xs text-gray-400 mt-1">retention · RFM · cohorts</p>
        </Link>
        <Link href="/reports" className="bg-white border border-gray-200 rounded-lg p-4 text-center hover:border-indigo-300 transition">
          <p className="text-sm font-medium text-gray-900">Reports</p>
          <p className="text-xs text-gray-400 mt-1">PDF / CSV / JSON</p>
        </Link>
      </div>
    </div>
  );
}

function StatCard({ label, value, color = "text-gray-900" }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}
