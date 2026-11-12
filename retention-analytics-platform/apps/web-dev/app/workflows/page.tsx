"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

interface Workflow {
  id: string;
  name: string;
  trigger_event: string;
  steps: { id: string; service: string; action: string }[];
  active: boolean;
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selected, setSelected] = useState<Workflow | null>(null);
  const [ctx, setCtx] = useState(`{"email": "dev@example.com", "cart_id": "cart-001"}`);
  const [result, setResult] = useState<any>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    apiGet("/workflows").then((d: any) => {
      const wfs = d.workflows ?? [];
      setWorkflows(wfs);
      if (wfs[0]) setSelected(wfs[0]);
    }).catch(() => {});
  }, []);

  const run = async () => {
    if (!selected) return;
    setRunning(true);
    setResult(null);
    try {
      let context: any = {};
      try { context = JSON.parse(ctx); } catch { throw new Error("Invalid JSON context"); }
      const data = await apiPost(`/workflows/${selected.id}/run`, { context });
      setResult({ ok: true, data });
    } catch (e: any) {
      setResult({ ok: false, error: e.message });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Workflows</h1>
        <p className="text-gray-500 text-sm mt-1">
          Pipelines that compose services. Event triggers the workflow → engine runs steps in order → results persisted.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-2">
          {workflows.map((w) => (
            <button
              key={w.id}
              onClick={() => { setSelected(w); setResult(null); }}
              className={`w-full text-left p-4 rounded-lg border transition ${
                selected?.id === w.id ? "border-emerald-500 bg-emerald-50" : "border-gray-200 bg-white hover:border-gray-300"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${w.active ? "bg-green-500" : "bg-gray-300"}`} />
                <span className="font-medium text-sm">{w.name}</span>
              </div>
              <p className="text-xs text-gray-400 font-mono mt-1">⚡ {w.trigger_event}</p>
            </button>
          ))}
        </div>

        <div className="lg:col-span-2 space-y-4">
          {selected && (
            <>
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
                <h2 className="font-semibold text-gray-900">{selected.name}</h2>
                <p className="text-xs text-gray-400 font-mono mb-4">POST /api/v1/workflows/{selected.id}/run</p>

                <div className="space-y-2">
                  <div className="bg-amber-50 border border-amber-200 rounded px-3 py-2 text-xs font-mono text-amber-700">
                    ⚡ event: {selected.trigger_event}
                  </div>
                  {selected.steps.map((s, i) => (
                    <div key={s.id} className="flex items-center gap-2">
                      <span className="text-gray-300 w-4 text-center">{i > 0 ? "↓" : ""}</span>
                      <div className="bg-slate-100 border border-gray-200 rounded px-3 py-2 font-mono text-xs flex-1">
                        <span className="text-emerald-600 font-semibold">{s.service}</span>
                        <span className="text-gray-400 mx-1">→</span>
                        <span className="text-gray-700">{s.action}</span>
                        <span className="text-gray-400 ml-2">#{s.id}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-3">
                <label className="block text-xs font-medium text-gray-500 uppercase">Context (JSON)</label>
                <textarea
                  value={ctx}
                  onChange={(e) => setCtx(e.target.value)}
                  rows={3}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-xs font-mono"
                />
                <button
                  onClick={run}
                  disabled={running}
                  className="px-4 py-2 bg-emerald-600 text-white rounded text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
                >
                  {running ? "Running…" : "Run Workflow"}
                </button>
              </div>

              {result && (
                <div className={`rounded-lg border p-4 ${result.ok ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                  <p className="text-sm font-medium mb-2">
                    Status: <span className={result.ok ? "text-green-600" : "text-red-600"}>{result.data?.status ?? result.error}</span>
                  </p>
                  {result.ok && (
                    <pre className="text-xs bg-white p-3 rounded border overflow-x-auto max-h-80">
                      {JSON.stringify(result.data?.step_outputs ?? result.data, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
