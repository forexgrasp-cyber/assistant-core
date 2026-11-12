"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

export default function VerticalsPage() {
  const [presets, setPresets] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [applied, setApplied] = useState<any[]>([]);
  const [services, setServices] = useState<any[]>([]);

  const load = () => {
    apiGet("/presets").then((d: any) => {
      setPresets(d.presets ?? []);
      if (d.presets?.length && !selected) openPreset(d.presets[0].id);
    }).catch(() => {});
    apiGet("/presets/applied").then((d: any) => setApplied(d.applications ?? [])).catch(() => {});
    apiGet("/services").then((d: any) => setServices(d.services ?? [])).catch(() => {});
  };

  const openPreset = async (id: string) => {
    const r: any = await apiGet(`/presets/${id}`);
    setSelected(r.preset);
  };

  const apply = async (id: string) => {
    await apiPost(`/presets/${id}/apply`);
    load();
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Industry Presets</h1>
        <p className="text-gray-500 text-sm mt-1 max-w-3xl">
          <b>Not structural verticals.</b> A preset is a shortcut bundle — customer fields, segments, campaigns, drip sequences.
          Apply any to <b>any</b> business whose customer records have the needed fields. The engine underneath is universal.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-2">
          {presets.map((p) => (
            <button key={p.id} onClick={() => openPreset(p.id)}
              className={`w-full text-left p-3 rounded-lg border transition ${selected?.id === p.id ? "border-emerald-500 bg-emerald-50" : "border-gray-200 bg-white hover:border-gray-300"}`}>
              <p className="font-medium text-sm">{p.name}</p>
              <p className="text-xs text-gray-400 mt-1">{p.segments} segments · {p.campaigns} campaigns · {p.sequences} sequences · {p.fields} fields</p>
            </button>
          ))}
        </div>

        {selected && (
          <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm p-5 space-y-3">
            <div>
              <h2 className="font-semibold text-gray-900">{selected.name}</h2>
              <p className="text-sm text-gray-600 mt-1">{selected.description}</p>
            </div>
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase mb-1">Required customer fields</h3>
              <div className="flex flex-wrap gap-1">
                {Object.entries(selected.customer_fields ?? {}).map(([k, v]) => (
                  <span key={k} className="text-xs bg-gray-100 px-2 py-0.5 rounded font-mono">{k}</span>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase mb-1">Segments</h3>
              {(selected.segments ?? []).map((s: any) => (
                <p key={s.name} className="text-xs font-mono bg-gray-50 px-2 py-1 rounded mb-1">{s.name} — {JSON.stringify(s.criteria)}</p>
              ))}
            </div>
            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase mb-1">Campaigns</h3>
              {(selected.campaigns ?? []).map((c: any) => (
                <p key={c.name} className="text-xs bg-emerald-50 px-2 py-1 rounded mb-1">{c.name} → flows: {c.flows?.join(", ")}</p>
              ))}
            </div>
            <button onClick={() => apply(selected.id)} className="px-4 py-2 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700">Apply preset</button>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <h3 className="font-semibold text-gray-900 text-sm mb-2">Full service surface ({services.length} services)</h3>
        <div className="flex flex-wrap gap-1">
          {services.map((s) => (
            <span key={s.name} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-mono">{s.name}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
