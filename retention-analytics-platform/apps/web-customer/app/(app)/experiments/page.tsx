"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<any[]>([]);
  const [pricing, setPricing] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [name, setName] = useState("");
  const [metric, setMetric] = useState("conversion_rate");
  const [control, setControl] = useState("");
  const [variant, setVariant] = useState("");

  const load = () => {
    apiGet("/experiments").then((d: any) => setExperiments(d.experiments ?? [])).catch(() => {});
    apiGet("/pricing-experiments").then((d: any) => setPricing(d.tests ?? [])).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    await apiPost("/experiments", { name, metric, variants: [
      { id: "A", name: "control", content: control },
      { id: "B", name: "variant", content: variant },
    ]});
    setName(""); load();
  };

  const analyze = async (id: string) => {
    const r: any = await apiGet(`/experiments/${id}/analyze`);
    setAnalysis(r);
    const e: any = await apiGet(`/experiments/${id}`);
    setSelected(e.experiment);
  };

  const record = async (id: string, vid: string) => {
    await apiPost(`/experiments/${id}/results`, { variant_id: vid, sent: 100, converted: vid === "B" ? 24 : 12 });
    analyze(id);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Experiments</h1>
        <p className="text-gray-500 text-sm mt-1">A/B test campaigns and offers, and test price points — measured against real outcomes.</p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 space-y-3">
        <h3 className="font-semibold text-gray-900 text-sm">New A/B experiment</h3>
        <div className="grid grid-cols-2 gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" className="border border-gray-300 rounded px-3 py-2 text-sm" />
          <select value={metric} onChange={(e) => setMetric(e.target.value)} className="border border-gray-300 rounded px-3 py-2 text-sm">
            <option value="conversion_rate">conversion_rate</option><option value="open_rate">open_rate</option><option value="save_rate">save_rate</option><option value="revenue">revenue</option>
          </select>
          <input value={control} onChange={(e) => setControl(e.target.value)} placeholder="Control content (A)" className="border border-gray-300 rounded px-3 py-2 text-sm" />
          <input value={variant} onChange={(e) => setVariant(e.target.value)} placeholder="Variant content (B)" className="border border-gray-300 rounded px-3 py-2 text-sm" />
        </div>
        <button onClick={create} disabled={!name} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50">Create</button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">A/B experiments ({experiments.length})</h3>
          {experiments.map((e) => (
            <div key={e.experiment_id} className={`p-3 rounded border mb-2 cursor-pointer ${selected?.experiment_id === e.experiment_id ? "border-indigo-400 bg-indigo-50" : "border-gray-100 bg-gray-50"}`} onClick={() => analyze(e.experiment_id)}>
              <div className="flex items-center justify-between">
                <p className="font-medium text-sm">{e.name}</p>
                <span className="text-xs text-gray-400 font-mono">{e.metric}</span>
              </div>
              <div className="flex gap-2 mt-2">
                <button onClick={(ev) => { ev.stopPropagation(); record(e.experiment_id, "A"); }} className="text-xs border border-gray-300 rounded px-2 py-1 hover:bg-white">Sim A: 100→12</button>
                <button onClick={(ev) => { ev.stopPropagation(); record(e.experiment_id, "B"); }} className="text-xs border border-gray-300 rounded px-2 py-1 hover:bg-white">Sim B: 100→24</button>
              </div>
            </div>
          ))}
          {experiments.length === 0 && <p className="text-sm text-gray-400">None yet.</p>}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">Analysis</h3>
          {!analysis && <p className="text-sm text-gray-400">Select an experiment and simulate results.</p>}
          {analysis && (
            <div className="space-y-2 text-sm">
              {analysis.variants?.map((v: any) => (
                <div key={v.variant_id} className="flex items-center gap-3">
                  <span className="font-mono font-bold w-8">{v.variant_id}</span>
                  <div className="flex-1 bg-gray-100 rounded h-4"><div className="bg-indigo-500 h-4 rounded" style={{ width: `${v.conversion_rate}%` }} /></div>
                  <span className="text-xs">{v.conversion_rate}% ({v.converted}/{v.sent})</span>
                </div>
              ))}
              {analysis.winner && <p className="text-green-700 font-medium">Winner: variant {analysis.winner.variant_id} at {analysis.winner.conversion_rate}% (lift +{analysis.lift_pct}%)</p>}
            </div>
          )}
          <h4 className="font-semibold text-gray-900 text-sm mt-5 mb-2">Pricing experiments ({pricing.length})</h4>
          {pricing.map((t) => <p key={t.test_id} className="text-xs font-mono py-1">{t.name} — prices: {t.price_points?.join(", ")}</p>)}
        </div>
      </div>
    </div>
  );
}
