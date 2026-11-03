"use client";

import { useEffect, useState } from "react";
import { Play, List, Zap } from "lucide-react";

const API = "/api";

export default function WorkflowDesigner() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/workflows`)
      .then((r) => r.json())
      .then((data) => { setWorkflows(data.workflows ?? []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const run = async (id: string) => {
    const res = await fetch(`${API}/workflows/${id}/run`, { method: "POST", body: JSON.stringify({}) });
    setResult(await res.json());
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Workflow Designer</h1>
          <p className="text-gray-500 text-sm">Design durable pipelines that compose services end-to-end.</p>
        </div>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading workflows…</p>
      ) : (
        <div className="space-y-3">
          {workflows.map((w) => (
            <div key={w.id} className="bg-white p-5 rounded border border-gray-200 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-gray-900">{w.name}</h3>
                  <p className="text-xs text-gray-500">{w.trigger_event ?? "manual trigger"}</p>
                </div>
                <button
                  onClick={() => run(w.id)}
                  className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700"
                >
                  <Play className="w-4 h-4 mr-1 inline" /> Run
                </button>
              </div>
              <div className="text-xs text-gray-600 space-y-1 mb-3">
                {w.steps?.map((s: any, i: number) => (
                  <div key={s.id} className="flex items-center gap-2">
                    <span className="text-gray-300">{i + 1}</span>
                    <span className="font-mono text-indigo-600">{s.service}</span>
                    <span className="text-gray-400 text-xs">·</span>
                    <span className="font-mono text-gray-600">{s.action}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {workflows.length === 0 && <p className="text-gray-500">No workflows defined.</p>}
        </div>
      )}

      {result && (
        <div className="bg-white p-5 rounded border border-gray-200 shadow-sm mt-6">
          <h3 className="font-semibold text-gray-900 mb-2">Execution result</h3>
          <p className="text-sm text-gray-600 mb-2">Status: <span className="font-mono">{result.status}</span></p>
          <pre className="text-xs text-gray-600 bg-gray-50 p-3 rounded overflow-x-auto">{JSON.stringify(result.step_outputs ?? result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
