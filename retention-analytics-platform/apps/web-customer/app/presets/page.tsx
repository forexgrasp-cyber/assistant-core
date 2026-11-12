"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";

export default function PresetsPage() {
  const { toast } = useToast();
  const [presets, setPresets] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [applied, setApplied] = useState<any[]>([]);

  const load = () => {
    apiGet("/presets").then((d: any) => {
      setPresets(d.presets ?? []);
      if (d.presets?.length && !selected) openPreset(d.presets[0].id);
    }).catch(() => {});
    apiGet("/presets/applied").then((d: any) => setApplied(d.applications ?? [])).catch(() => {});
  };

  const openPreset = async (id: string) => {
    const r: any = await apiGet(`/presets/${id}`);
    setSelected(r.preset);
  };

  const apply = async (id: string) => {
    const r: any = await apiPost(`/presets/${id}/apply`);
    toast(`Applied: ${r.application.campaigns_created} campaigns, ${r.application.sequences_created} sequences created. Edit them in Campaigns / Flows.`);
    load();
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Industry Presets</h1>
        <p className="text-gray-500 text-sm mt-1 max-w-3xl">
          Optional shortcuts, not restrictions. A preset bundles customer fields, segments, campaigns, and drip sequences.
          Apply any of them to <b>any</b> business whose customer records have the needed fields — or ignore them and build your own.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-2">
          {presets.map((p) => (
            <button key={p.id} onClick={() => openPreset(p.id)}
              className={`w-full text-left p-4 rounded-lg border transition ${selected?.id === p.id ? "border-indigo-500 bg-indigo-50" : "border-gray-200 bg-white hover:border-gray-300"}`}>
              <p className="font-medium text-sm">{p.name}</p>
              <p className="text-xs text-gray-400 mt-1">{p.segments} segments · {p.campaigns} campaigns · {p.sequences} sequences</p>
            </button>
          ))}
        </div>

        {selected && (
          <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <div>
              <h2 className="font-semibold text-gray-900">{selected.name}</h2>
              <p className="text-sm text-gray-600 mt-1">{selected.description}</p>
            </div>

            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Customer record fields this needs</h3>
              <div className="flex flex-wrap gap-1">
                {Object.entries(selected.customer_fields ?? {}).map(([k, v]) => (
                  <span key={k} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-mono">{k}: {String(v)}</span>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Segments included</h3>
              <div className="space-y-1">
                {(selected.segments ?? []).map((s: any) => (
                  <div key={s.name} className="text-xs bg-gray-50 rounded px-2 py-1.5">
                    <span className="font-medium">{s.name}</span>
                    <span className="text-gray-400 font-mono ml-2">{JSON.stringify(s.criteria)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Campaigns included</h3>
              <div className="space-y-2">
                {(selected.campaigns ?? []).map((c: any) => (
                  <div key={c.name} className="text-xs bg-indigo-50 border border-indigo-100 rounded p-3">
                    <p className="font-medium text-indigo-900">{c.name}</p>
                    <p className="text-gray-600 mt-0.5">{c.message}</p>
                    <p className="text-gray-400 font-mono mt-1">flows: {c.flows?.join(", ")} · metrics: {c.metrics?.join(", ")}</p>
                  </div>
                ))}
              </div>
            </div>

            {(selected.sequences ?? []).length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Drip sequences included</h3>
                <div className="space-y-2">
                  {selected.sequences.map((s: any) => (
                    <div key={s.name} className="text-xs bg-emerald-50 border border-emerald-100 rounded p-3">
                      <p className="font-medium text-emerald-900">{s.name}</p>
                      <ol className="mt-1 space-y-0.5">
                        {s.steps.map((st: any, i: number) => (
                          <li key={i} className="text-gray-600">Day {st.delay_days}: {st.channel} — {st.subject || st.body?.slice(0, 60)}</li>
                        ))}
                      </ol>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button onClick={() => apply(selected.id)} className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
              Apply this preset
            </button>
            <p className="text-xs text-gray-400">Applies segments + draft campaigns + sequences. Everything stays editable.</p>
          </div>
        )}
      </div>

      {applied.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Applied presets ({applied.length})</h3>
          {applied.map((a) => (
            <p key={a.application_id} className="text-xs text-gray-600">
              {a.preset_id}: {a.campaigns_created} campaigns, {a.sequences_created} sequences — {a.applied_at?.slice(0, 10)}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
