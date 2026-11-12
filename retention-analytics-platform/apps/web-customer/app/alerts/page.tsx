"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [incidents, setIncidents] = useState<any[]>([]);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState("medium");

  const load = () => {
    apiGet("/cs/alerts/open").then((d: any) => setAlerts(d.alerts ?? [])).catch(() => {});
    apiGet("/incidents").then((d: any) => setIncidents(d.incidents ?? [])).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const fire = async () => {
    await apiPost(`/cs/alerts/fire?title=${encodeURIComponent(title)}&severity=${severity}&type=risk`);
    setTitle("");
    load();
  };

  const ack = async (id: string) => {
    await apiPost(`/actions/cs.alerts/acknowledge`, { alert_id: id });
    load();
  };

  const sevColor = (s: string) =>
    s === "critical" ? "bg-red-100 text-red-700" : s === "high" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alerts & Incidents</h1>
          <p className="text-gray-500 text-sm mt-1">Real-time alerts from workflows, health engine, and anomaly detection.</p>
        </div>
        <div className="flex gap-2">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Alert title" className="border border-gray-300 rounded px-3 py-2 text-sm" />
          <select value={severity} onChange={(e) => setSeverity(e.target.value)} className="border border-gray-300 rounded px-2 py-2 text-sm">
            <option value="low">low</option><option value="medium">medium</option><option value="high">high</option><option value="critical">critical</option>
          </select>
          <button onClick={fire} className="px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Fire alert</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">Open alerts ({alerts.length})</h3>
          {alerts.length === 0 && <p className="text-sm text-gray-400">No open alerts — nice.</p>}
          <div className="space-y-2">
            {alerts.map((a) => (
              <div key={a.alert_id} className="flex items-start justify-between p-3 bg-gray-50 rounded border border-gray-100">
                <div>
                  <p className="text-sm font-medium text-gray-900">{a.title}</p>
                  <p className="text-xs text-gray-500">{a.detail}</p>
                  <span className={`inline-block text-[10px] px-1.5 py-0.5 rounded mt-1 ${sevColor(a.severity)}`}>{a.severity}</span>
                </div>
                <button onClick={() => ack(a.alert_id)} className="text-xs text-indigo-600 hover:underline">Ack</button>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">Incidents ({incidents.length})</h3>
          {incidents.length === 0 && <p className="text-sm text-gray-400">No incidents.</p>}
          <div className="space-y-2">
            {incidents.map((i) => (
              <div key={i.incident_id} className="p-3 bg-gray-50 rounded border border-gray-100">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-900">{i.metric} {i.direction}</p>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${sevColor(i.severity)}`}>{i.status}</span>
                </div>
                <p className="text-xs text-gray-500">deviation {i.deviation_pct}% · {String(i.created_at).slice(0, 16).replace("T", " ")}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
