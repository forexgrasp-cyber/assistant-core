"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

export default function OpsPage() {
  const [alerts, setAlerts] = useState<any>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [playbooks, setPlaybooks] = useState<any[]>([]);
  const [renewals, setRenewals] = useState<any>(null);
  const [center, setCenter] = useState<any>(null);
  const [journeys, setJourneys] = useState<any[]>([]);
  const [sequences, setSequences] = useState<any[]>([]);
  const [walls, setWalls] = useState<any[]>([]);
  const [dunning, setDunning] = useState<any>(null);
  const [catalog, setCatalog] = useState<any>(null);
  const [msg, setMsg] = useState("");

  const load = () => {
    apiGet("/cs/alerts/open").then((d: any) => setAlerts(d)).catch(() => {});
    apiGet("/cs/plans").then((d: any) => setPlans(d.plans ?? [])).catch(() => {});
    apiGet("/cs/playbooks").then(() => {}).catch(() => {});
    apiGet("/cs/renewals/forecast").then(setRenewals).catch(() => {});
    apiGet("/cs/command-center").then((d: any) => setCenter(d.overview)).catch(() => {});
    apiGet("/journeys").then((d: any) => setJourneys(d.journeys ?? [])).catch(() => {});
    apiGet("/sequences").then((d: any) => setSequences(d.sequences ?? [])).catch(() => {});
    apiGet("/walls").then((d: any) => setWalls(d.walls ?? [])).catch(() => {});
    apiGet("/dunning/active").then(setDunning).catch(() => {});
    apiGet("/catalog/products").then((d: any) => setCatalog(d)).catch(() => {});
    apiGet("/cs/playbooks").then((d: any) => setPlaybooks(d.playbooks ?? [])).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const fireAlert = async () => {
    await apiPost("/cs/alerts/fire?title=Manual test alert&severity=high&type=risk");
    setMsg("Alert fired"); load();
  };

  const createPlan = async () => {
    await apiPost("/cs/plans?name=Onboarding plan&client_id=demo-c0");
    setMsg("Plan created"); load();
  };

  const createPlaybook = async () => {
    await apiPost("/cs/playbooks", { name: "Churn save playbook", trigger: "client.churn_risk", actions: [{ service: "email", action: "send" }] });
    setMsg("Playbook created"); load();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Success Ops</h1>
        <p className="text-gray-500 text-sm mt-1">Alerts, success plans, playbooks, renewals, journeys, drip sequences, walls, dunning, catalog — the operating layer.</p>
      </div>

      {msg && <div className="bg-indigo-50 border border-indigo-200 text-indigo-800 px-4 py-2 rounded text-sm">{msg}</div>}

      {center && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center"><p className="text-2xl font-bold text-red-600">{center.open_alerts}</p><p className="text-xs text-gray-500">open alerts</p></div>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-center"><p className="text-2xl font-bold text-amber-600">{center.at_risk_clients}</p><p className="text-xs text-gray-500">at-risk clients</p></div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center"><p className="text-2xl font-bold text-green-600">${center.renewal_forecast_arr ?? 0}</p><p className="text-xs text-gray-500">renewal forecast ARR</p></div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card title={`Open alerts (${alerts?.count ?? 0})`} action={<button onClick={fireAlert} className="text-xs text-indigo-600 hover:underline">fire test</button>}>
          {(alerts?.alerts ?? []).slice(0, 5).map((a: any) => <p key={a.alert_id} className="text-xs py-0.5"><b>{a.title}</b> <span className="text-gray-400">{a.severity}</span></p>)}
        </Card>
        <Card title={`Success plans (${plans.length})`} action={<button onClick={createPlan} className="text-xs text-indigo-600 hover:underline">+ new</button>}>
          {plans.slice(0, 5).map((p) => <p key={p.plan_id} className="text-xs py-0.5">{p.name} <span className="text-gray-400">{p.status}</span></p>)}
        </Card>
        <Card title={`Playbooks (${playbooks.length})`} action={<button onClick={createPlaybook} className="text-xs text-indigo-600 hover:underline">+ new</button>}>
          {playbooks.slice(0, 5).map((p) => <p key={p.playbook_id} className="text-xs py-0.5">{p.name} <span className="text-gray-400 font-mono">⚡{p.trigger}</span></p>)}
        </Card>
        <Card title="Renewals">
          {renewals && <p className="text-xs">Forecast ARR: <b>${renewals.forecast_arr}</b> of ${renewals.total_arr_up_for_renewal} up for renewal ({renewals.renewals} renewals)</p>}
        </Card>
        <Card title={`Journeys (${journeys.length})`}>
          {journeys.slice(0, 5).map((j) => <p key={j.journey_id} className="text-xs py-0.5">{j.name} — {j.stages?.length} stages</p>)}
        </Card>
        <Card title={`Drip sequences (${sequences.length})`}>
          {sequences.slice(0, 5).map((s) => <p key={s.sequence_id} className="text-xs py-0.5">{s.name} — {s.steps?.length} steps</p>)}
        </Card>
        <Card title={`Walls (${walls.length})`}>
          {walls.slice(0, 5).map((w) => <p key={w.wall_id} className="text-xs py-0.5">{w.type} wall · {w.customer_id} · {w.active ? "active" : "resolved"}</p>)}
        </Card>
        <Card title="Dunning">
          {dunning && <p className="text-xs">{dunning.count} active campaigns</p>}
        </Card>
        <Card title={`Catalog (${catalog?.products?.length ?? 0} products)`}>
          {(catalog?.products ?? []).slice(0, 5).map((p: any) => <p key={p.product_id} className="text-xs py-0.5">${p.price} {p.name}</p>)}
        </Card>
      </div>
    </div>
  );
}

function Card({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-semibold text-gray-900 text-sm">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}
