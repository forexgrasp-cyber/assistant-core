"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

export default function RosterPage() {
  const [roster, setRoster] = useState<any>(null);
  const [clients, setClients] = useState<any[]>([]);
  const [platforms, setPlatforms] = useState<any>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [tenant, setTenant] = useState("");
  const [share, setShare] = useState<any>(null);
  const [msg, setMsg] = useState("");

  const load = () => {
    apiGet("/agency/roster").then(setRoster).catch(() => {});
    apiGet("/agency/clients").then((d: any) => setClients(d.clients ?? [])).catch(() => {});
    apiGet("/agency/platforms").then(setPlatforms).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const addClient = async () => {
    await apiPost("/agency/clients", {
      name, tenant_id: tenant || "00000000-0000-0000-0000-000000000001",
      monthly_target: parseFloat(target || "0"), goal_metric: "revenue",
    });
    setName(""); setTarget(""); setTenant(""); setShowAdd(false);
    load();
  };

  const createShare = async (clientId: string) => {
    const r: any = await apiPost(`/agency/clients/${clientId}/share`, {});
    setShare(r.share);
  };

  const statusColor = (s: string) =>
    s === "on_track" ? "bg-green-100 text-green-700" :
    s === "behind_goal" ? "bg-amber-100 text-amber-700" :
    s === "deliverability" ? "bg-red-100 text-red-700" : "bg-orange-100 text-orange-700";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Client roster</h1>
          <p className="text-gray-500 text-sm mt-1">
            Every client brand you run, with revenue pacing against goal and what needs attention today.
          </p>
        </div>
        <button onClick={() => setShowAdd(!showAdd)} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">+ Add client</button>
      </div>

      {msg && <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-2 rounded text-sm">{msg}</div>}

      {showAdd && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 flex flex-wrap gap-3 items-end">
          <div><label className="text-xs text-gray-500 block mb-1">Client name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Trendi Apparel" className="border border-gray-300 rounded px-3 py-2 text-sm" /></div>
          <div><label className="text-xs text-gray-500 block mb-1">Monthly revenue goal</label>
            <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="465000" type="number" className="border border-gray-300 rounded px-3 py-2 text-sm w-36" /></div>
          <div><label className="text-xs text-gray-500 block mb-1">Tenant id (their data)</label>
            <input value={tenant} onChange={(e) => setTenant(e.target.value)} placeholder="tenant uuid" className="border border-gray-300 rounded px-3 py-2 text-sm w-56 font-mono text-xs" /></div>
          <button onClick={addClient} disabled={!name} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm disabled:opacity-50">Add</button>
        </div>
      )}

      {/* Roster summary */}
      {roster && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">${roster.summary.total_revenue_mtd.toLocaleString()}</p>
            <p className="text-xs text-gray-400">revenue MTD</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-amber-600">{roster.summary.behind_goal}</p>
            <p className="text-xs text-gray-400">behind goal</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-orange-600">{roster.summary.needs_attention}</p>
            <p className="text-xs text-gray-400">need attention</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-red-600">{roster.summary.total_churn_risk}</p>
            <p className="text-xs text-gray-400">at churn risk</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">${Math.round(roster.summary.total_at_risk_mrr).toLocaleString()}</p>
            <p className="text-xs text-gray-400">MRR at risk</p>
          </div>
        </div>
      )}

      {/* Roster table */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <h3 className="font-semibold text-gray-900 text-sm mb-3">All clients ({roster?.count ?? 0})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead><tr className="border-b text-xs text-gray-400">
              <th className="py-2">Client</th><th className="py-2">Status</th><th className="py-2">Revenue MTD</th>
              <th className="py-2">Goal</th><th className="py-2">Pacing</th><th className="py-2">Churn risk</th>
              <th className="py-2">Alerts</th><th className="py-2">Platforms</th><th className="py-2"></th>
            </tr></thead>
            <tbody>
              {(roster?.clients ?? []).map((c: any) => (
                <tr key={c.client_id} className="border-b last:border-0">
                  <td className="py-2">
                    <span className="font-medium">{c.name}</span>
                    <p className="text-xs text-gray-400">{c.client_id}</p>
                  </td>
                  <td className="py-2"><span className={`text-[10px] px-1.5 py-0.5 rounded ${statusColor(c.status)}`}>{c.status_label}</span></td>
                  <td className="py-2">${(c.revenue_mtd ?? 0).toLocaleString()}</td>
                  <td className="py-2">{c.goal?.monthly_target ? "$" + c.goal.monthly_target.toLocaleString() : "-"}</td>
                  <td className="py-2 text-xs">
                    {c.goal_pct != null ? (
                      <>
                        <div className="flex items-center gap-2 mb-1">
                          <PaceBar goalPct={c.goal_pct} pacingPct={c.pacing_pct} />
                          <span className={c.goal_pct >= c.pacing_pct ? "text-green-600" : "text-red-600"} font-medium text-xs>
                            {c.goal_pct}% of goal
                          </span>
                        </div>
                        <span className="text-gray-400">{c.pacing_pct}% through month</span>
                      </>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td className="py-2 text-xs">{c.churn_risk ?? 0}</td>
                  <td className="py-2 text-xs">{c.open_alerts ?? 0}</td>
                  <td className="py-2 text-xs text-gray-400">{(c.platforms ?? []).join(", ") || "-"}</td>
                  <td className="py-2"><button onClick={() => createShare(c.client_id)} className="text-xs text-indigo-600 hover:underline">Share</button></td>
                </tr>
              ))}
              {(roster?.clients ?? []).length === 0 && (
                <tr><td colSpan={9} className="py-6 text-center text-gray-400 text-sm">No clients yet — add one above.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {share && (
          <div className="mt-3 bg-indigo-50 border border-indigo-200 rounded p-3 text-sm">
            <p className="font-medium text-indigo-900">White-label dashboard link for {share.client_id}</p>
            <code className="text-xs bg-white border border-indigo-100 px-2 py-1 rounded inline-block mt-1">/share/{share.token}</code>
          </div>
        )}
      </div>

      {/* Platform connectors */}
      {platforms && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-1">Connect the platforms your clients run on</h3>
          <p className="text-xs text-gray-400 mb-3">{platforms.configured_count} of {platforms.count} configured in this environment (keys stay in env).</p>
          {Object.entries(platforms.by_category as Record<string, string[]>).map(([cat, names]) => (
            <div key={cat} className="mb-2">
              <p className="text-xs font-semibold text-gray-400 uppercase mb-1">{cat.replace(/_/g, " ")}</p>
              <div className="flex flex-wrap gap-1">
                {names.map((n) => {
                  const meta = (platforms.platforms as any[]).find((x) => x.platform === n);
                  return (
                    <span key={n} className={`text-xs px-2 py-0.5 rounded font-mono border ${meta?.configured ? "bg-green-50 text-green-700 border-green-200" : "bg-gray-50 text-gray-500 border-gray-200"}`}>
                      {n}{meta?.configured ? " ✓" : ""}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PaceBar({ goalPct, pacingPct }: { goalPct: number; pacingPct: number }) {
  const onTrack = goalPct >= pacingPct;
  const fillPct = Math.min(100, Math.max(0, (goalPct / (pacingPct || 1)) * 100));
  return (
    <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden relative" title={`Pacing: ${pacingPct}%, Goal achievement: ${goalPct}%`}>
      <div className="h-full bg-gray-300" style={{ width: `${pacingPct}%` }} />
      <div className={`h-full absolute top-0 left-0 rounded-full ${onTrack ? "bg-green-500" : "bg-red-500"}`} style={{ width: `${fillPct}%` }} />
      <div className="absolute top-0 right-0 h-full w-px bg-gray-400" style={{ left: `${pacingPct}%` }} />
    </div>
  );
}
