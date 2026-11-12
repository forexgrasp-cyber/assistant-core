"use client";

import { useEffect, useState } from "react";
import { apiPost } from "@/lib/api";

const TENANT = "00000000-0000-0000-0000-000000000001";

interface Retention { retention_rate_30d: number; churn_rate_30d: number; retained_customers: number; current_window_customers: number; previous_window_customers: number; }
interface Rfm { segments: Record<string, number> }
interface Cohorts { cohorts: any[]; cohort_months: number }

export default function Analytics() {
  const [retention, setRetention] = useState<Retention | null>(null);
  const [rfm, setRfm] = useState<Rfm | null>(null);
  const [cohorts, setCohorts] = useState<Cohorts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savedMsg, setSavedMsg] = useState("");

  const saveAsReport = async () => {
    setSavedMsg("");
    try {
      const r: any = await apiPost("/reports/saved", {
        name: `Analytics snapshot ${new Date().toISOString().slice(0, 16).replace("T", " ")}`,
        description: "Auto-saved from the Analytics page with live metrics",
        format: "json",
        filters: { time_range: "30d" },
        widgets: ["retention", "rfm", "cohorts", "saas", "nps"],
      });
      // run it immediately so the saved report carries substantiating data
      await apiPost(`/reports/saved/${r.report.report_id}/run`);
      setSavedMsg(`Saved and run — report ${r.report.report_id.slice(0, 12)}… stored with current metrics. See Reports page.`);
    } catch (e: any) {
      setSavedMsg("Save failed: " + e.message);
    }
  };

  const load = () => {
    setLoading(true);
    setError("");
    Promise.all([
      apiPost("/services/analytics.metric/actions/compute_retention", { payload: { tenant_id: TENANT } }),
      apiPost("/services/analytics.metric/actions/compute_rfm", { payload: { tenant_id: TENANT } }),
      apiPost("/services/analytics.cohort/actions/compute_cohorts", { payload: { tenant_id: TENANT, cohort_months: 6 } }),
    ])
      .then(([r, f, c]: any[]) => {
        setRetention(r.result);
        setRfm(f.result);
        setCohorts(c.result);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 text-sm mt-1">
            Retention, churn, RFM segments, cohorts, and the full SaaS suite — computed live from your customer data.
            Save any view as a report.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} disabled={loading} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50">
            {loading ? "Computing…" : "Recompute"}
          </button>
          <button onClick={saveAsReport} disabled={loading} className="px-4 py-2 border border-indigo-300 text-indigo-700 rounded text-sm hover:bg-indigo-50 disabled:opacity-50">
            Save as report
          </button>
        </div>
      </div>

      {savedMsg && <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded text-sm">{savedMsg}</div>}

      {error && <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">{error}</div>}

      {/* Retention + Churn */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MetricCard title="30-Day Retention" value={retention ? pct(retention.retention_rate_30d) : "…"} color="bg-green-500" detail={retention ? `${retention.retained_customers} of ${retention.current_window_customers} retained` : ""} />
        <MetricCard title="30-Day Churn" value={retention ? pct(retention.churn_rate_30d) : "…"} color="bg-red-400" detail={retention ? `${retention.previous_window_customers} in previous window` : ""} />
      </div>

      {/* Retention bar */}
      {retention && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
          <h3 className="font-semibold text-gray-900 mb-3 text-sm">Retention vs Churn</h3>
          <div className="flex h-6 rounded-full overflow-hidden bg-gray-100">
            <div className="bg-green-500 h-full" style={{ width: pct(retention.retention_rate_30d) }} />
            <div className="bg-red-400 h-full" style={{ width: pct(retention.churn_rate_30d) }} />
            <div className="bg-gray-200 h-full flex-1" />
          </div>
          <div className="flex gap-4 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-green-500 rounded-full inline-block" /> Retained {pct(retention.retention_rate_30d)}</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-400 rounded-full inline-block" /> Churned {pct(retention.churn_rate_30d)}</span>
          </div>
        </div>
      )}

      {/* RFM segments */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-3 text-sm">RFM Segments</h3>
        {rfm ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(rfm.segments).map(([seg, count]) => (
              <div key={seg} className="bg-gray-50 rounded p-3 text-center">
                <p className="text-xl font-bold text-gray-900">{count}</p>
                <p className="text-xs text-gray-500 capitalize">{seg.replace("_", " ")}</p>
              </div>
            ))}
          </div>
        ) : <p className="text-sm text-gray-400">Loading…</p>}
        <p className="text-xs text-gray-400 mt-3 font-mono">POST /api/v1/services/analytics.metric/actions/compute_rfm</p>
      </div>

      {/* Cohorts */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-3 text-sm">Cohorts ({cohorts?.cohort_months ?? 6} months)</h3>
        {cohorts && cohorts.cohorts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b text-xs text-gray-400"><th className="py-2">Cohort</th><th className="py-2">Customers</th><th className="py-2">Retained</th></tr></thead>
              <tbody>
                {cohorts.cohorts.map((c: any, i: number) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-2 font-mono text-xs">{c.month ?? c.cohort ?? i}</td>
                    <td className="py-2">{c.size ?? c.customers ?? "-"}</td>
                    <td className="py-2">{c.retained ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-400">No cohort data yet — ingest client.created events to populate.</p>
        )}
        <p className="text-xs text-gray-400 mt-3 font-mono">POST /api/v1/services/analytics.cohort/actions/compute_cohorts</p>
      </div>
    </div>
  );
}

function MetricCard({ title, value, color, detail }: { title: string; value: string; color: string; detail: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{title}</p>
      <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
      {detail && <p className="text-xs text-gray-400 mt-1">{detail}</p>}
    </div>
  );
}
