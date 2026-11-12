"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiGet, apiPost } from "@/lib/api";

const WIDGETS = [
  { id: "stats", label: "Key metrics" },
  { id: "retention", label: "Retention & churn" },
  { id: "workflows", label: "Active workflows" },
  { id: "quick", label: "Quick actions" },
  { id: "alerts", label: "Open alerts" },
  { id: "health", label: "Health watchlist" },
  { id: "renewals", label: "Renewals at risk" },
  { id: "top", label: "Top pains covered" },
];

const ORDER_KEY = "ra_dashboard_layout";

export default function Dashboard() {
  const [health, setHealth] = useState<any>(null);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [services, setServices] = useState<any[]>([]);
  const [retention, setRetention] = useState<any>(null);
  const [alerts, setAlerts] = useState<any>(null);
  const [healthRows, setHealthRows] = useState<any[]>([]);
  const [renewals, setRenewals] = useState<any>(null);
  const [pains, setPains] = useState<any>(null);
  const [order, setOrder] = useState<string[]>(WIDGETS.map((w) => w.id));
  const [editMode, setEditMode] = useState(false);
  const [note, setNote] = useState("");
  const [annotation, setAnnotation] = useState<any>(null);

  useEffect(() => {
    const saved = localStorage.getItem(ORDER_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        const valid = parsed.filter((id: string) => WIDGETS.some((w) => w.id === id));
        const missing = WIDGETS.map((w) => w.id).filter((id) => !valid.includes(id));
        setOrder([...valid, ...missing]);
      } catch {}
    }
    apiGet("/health").then(setHealth).catch(() => {});
    apiGet("/workflows").then((d: any) => setWorkflows(d.workflows ?? [])).catch(() => {});
    apiGet("/services").then((d: any) => setServices(d.services ?? [])).catch(() => {});
    apiPost("/services/analytics.metric/actions/compute_retention", { payload: { tenant_id: "00000000-0000-0000-0000-000000000001" } })
      .then((d: any) => setRetention(d.result ?? d)).catch(() => {});
    apiGet("/cs/alerts/open").then(setAlerts).catch(() => {});
    apiGet("/health/engine").then((d: any) => setHealthRows(d.scores ?? [])).catch(() => {});
    apiGet("/renewals/risk").then(setRenewals).catch(() => {});
    apiGet("/pains").then(setPains).catch(() => {});
  }, []);

  const saveOrder = (next: string[]) => {
    setOrder(next);
    localStorage.setItem(ORDER_KEY, JSON.stringify(next));
  };

  const move = (id: string, dir: -1 | 1) => {
    const i = order.indexOf(id);
    const j = i + dir;
    if (j < 0 || j >= order.length) return;
    const next = [...order];
    [next[i], next[j]] = [next[j], next[i]];
    saveOrder(next);
  };

  const toggleWidget = (id: string) => {
    saveOrder(order.includes(id) ? order.filter((x) => x !== id) : [...order, id]);
  };

  const addAnnotation = async () => {
    const r: any = await apiPost("/analytics/annotations", { metric: "retention", note });
    setAnnotation(r.annotation);
    setNote("");
  };

  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

  const render = (id: string) => {
    switch (id) {
      case "stats":
        return (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Status" value={health?.status ?? "…"} color="text-green-600" />
            <Stat label="Services" value={String(health?.services?.length ?? services.length ?? "…")} />
            <Stat label="Workflows" value={String(workflows.length)} />
            <Stat label="30d Retention" value={retention ? pct(retention.retention_rate_30d) : "…"}
              color={retention && retention.retention_rate_30d > 0.5 ? "text-green-600" : "text-gray-900"} />
          </div>
        );
      case "retention":
        return (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">Retention & churn</h2>
              <div className="flex gap-2">
                <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Annotate this metric…" className="border border-gray-300 rounded px-2 py-1 text-xs" />
                <button onClick={addAnnotation} className="px-2 py-1 bg-indigo-600 text-white rounded text-xs">Note</button>
              </div>
            </div>
            {retention ? (
              <>
                <div className="flex h-3 rounded-full overflow-hidden bg-gray-100">
                  <div className="bg-green-500 h-full" style={{ width: pct(retention.retention_rate_30d) }} />
                  <div className="bg-red-400 h-full" style={{ width: pct(retention.churn_rate_30d) }} />
                </div>
                <div className="grid grid-cols-4 gap-3 mt-4 text-sm">
                  <div><p className="text-xs text-gray-400">Retention</p><p className="font-bold">{pct(retention.retention_rate_30d)}</p></div>
                  <div><p className="text-xs text-gray-400">Churn</p><p className="font-bold text-red-500">{pct(retention.churn_rate_30d)}</p></div>
                  <div><p className="text-xs text-gray-400">Retained</p><p className="font-bold">{retention.retained_customers}</p></div>
                  <div><p className="text-xs text-gray-400">Active</p><p className="font-bold">{retention.current_window_customers}</p></div>
                </div>
                {annotation && <p className="text-xs text-indigo-600 mt-2">Note saved: {annotation.note}</p>}
              </>
            ) : <p className="text-sm text-gray-400">Computing…</p>}
          </div>
        );
      case "workflows":
        return (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-gray-900">Active workflows</h2>
              <Link href="/flows" className="text-sm text-indigo-600 hover:underline">Manage →</Link>
            </div>
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {workflows.map((w) => (
                <div key={w.id} className="flex items-center gap-3 p-2.5 bg-gray-50 rounded">
                  <span className={`w-2 h-2 rounded-full ${w.active ? "bg-green-500" : "bg-gray-300"}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 truncate">{w.name}</p>
                    <p className="text-xs text-gray-400 font-mono truncate">⚡ {w.trigger_event}</p>
                  </div>
                  <span className="text-xs text-gray-400">{w.steps?.length ?? 0} steps</span>
                </div>
              ))}
            </div>
          </div>
        );
      case "quick":
        return (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { href: "/campaigns", t: "New campaign", s: "target + flows" },
              { href: "/flows", t: "Browse flows", s: "37 automations" },
              { href: "/customers", t: "Add customers", s: "CSV import" },
              { href: "/reports", t: "Build report", s: "saved + scheduled" },
              { href: "/segments", t: "New segment", s: "live filter" },
              { href: "/experiments", t: "A/B test", s: "measure variants" },
              { href: "/flow-editor", t: "Visual builder", s: "drag & drop" },
              { href: "/alerts", t: "Alerts inbox", s: "ack & triage" },
            ].map((q) => (
              <Link key={q.href} href={q.href} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-indigo-300 transition">
                <p className="text-sm font-medium text-gray-900">{q.t}</p>
                <p className="text-xs text-gray-400 mt-1">{q.s}</p>
              </Link>
            ))}
          </div>
        );
      case "alerts":
        return (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-900">Open alerts</h2>
              <Link href="/alerts" className="text-sm text-indigo-600 hover:underline">Inbox →</Link>
            </div>
            {alerts?.count ? (
              <div className="space-y-2">
                {alerts.alerts.slice(0, 4).map((a: any) => (
                  <div key={a.alert_id} className="flex justify-between p-2 bg-gray-50 rounded text-sm">
                    <span>{a.title}</span><span className="text-xs text-gray-400">{a.severity}</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-gray-400">No open alerts ✓</p>}
          </div>
        );
      case "health":
        return (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-gray-900">Health watchlist</h2>
              <Link href="/ops" className="text-sm text-indigo-600 hover:underline">Ops →</Link>
            </div>
            {healthRows.length === 0 ? <p className="text-sm text-gray-400">No scored customers yet.</p> : (
              <div className="space-y-2">
                {healthRows.slice(0, 5).map((h: any) => (
                  <div key={h.client_id} className="flex justify-between p-2 bg-gray-50 rounded text-sm">
                    <span className="font-mono text-xs">{h.client_id}</span>
                    <span className={h.score < 50 ? "text-red-600 font-semibold" : "text-green-600"}>{h.score} · {h.tier}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      case "renewals":
        return (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Renewals at risk</h2>
            {renewals?.count ? (
              <div className="space-y-2">
                {renewals.renewals.slice(0, 5).map((r: any) => (
                  <div key={r.renewal_id} className="flex justify-between p-2 bg-gray-50 rounded text-sm">
                    <span className="font-mono text-xs">{r.customer_id}</span>
                    <span className={r.risk_tier === "critical" || r.risk_tier === "high" ? "text-red-600 font-semibold" : "text-gray-600"}>
                      {r.risk_tier} · ${r.arr}
                    </span>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-gray-400">No tracked renewals.</p>}
          </div>
        );
      case "top":
        return (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Pain coverage</h2>
            {pains && (
              <>
                <p className="text-3xl font-bold text-indigo-600">{pains.covered}/{pains.total_pains}</p>
                <p className="text-xs text-gray-400 mb-2">end-user pains covered by a workflow</p>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(pains.by_category).map(([cat, items]: [string, any]) => (
                    <span key={cat} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded">{cat}: {items.length}</span>
                  ))}
                </div>
              </>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">Your retention command center — customize the layout to fit your workflow.</p>
        </div>
        <button onClick={() => setEditMode(!editMode)} className="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">
          {editMode ? "Done" : "Customize layout"}
        </button>
      </div>

      {editMode && (
        <div className="bg-white rounded-lg border border-indigo-200 p-4">
          <p className="text-xs text-gray-500 mb-2">Toggle widgets and reorder them (saved in this browser).</p>
          <div className="flex flex-wrap gap-2">
            {WIDGETS.map((w) => (
              <div key={w.id} className={`flex items-center gap-1 px-2 py-1 rounded border text-xs ${order.includes(w.id) ? "border-indigo-300 bg-indigo-50" : "border-gray-200 bg-gray-50 opacity-60"}`}>
                <button onClick={() => toggleWidget(w.id)} className="font-medium">{w.label}</button>
                {order.includes(w.id) && (
                  <>
                    <button onClick={() => move(w.id, -1)} className="text-gray-400 hover:text-gray-700">↑</button>
                    <button onClick={() => move(w.id, 1)} className="text-gray-400 hover:text-gray-700">↓</button>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {order.map((id) => (
        <div key={id} className="relative group">
          {render(id)}
        </div>
      ))}
    </div>
  );
}

function Stat({ label, value, color = "text-gray-900" }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
    </div>
  );
}
