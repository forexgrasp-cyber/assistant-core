"use client";

import { useEffect, useState } from "react";
import { Play, Zap } from "lucide-react";

const API = "/api";

export default function Flows() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [runResult, setRunResult] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/workflows`)
      .then((r) => r.json())
      .then((data) => { setWorkflows(data.workflows ?? []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const run = async (id: string) => {
    const res = await fetch(`${API}/workflows/${id}/run`, { method: "POST", body: JSON.stringify({}) });
    setRunResult(await res.json());
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Flows</h1>
          <p className="text-gray-500 text-sm">Durable pipelines that compose services end-to-end.</p>
        </div>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading workflows…</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {workflows.map((w) => (
            <div key={w.id} className="bg-white p-5 rounded border border-gray-200 shadow-sm">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-5 h-5 text-indigo-600" />
                <h3 className="font-semibold text-gray-900">{w.name}</h3>
              </div>
              <p className="text-xs text-gray-500 mb-3">
                Trigger: {w.trigger_event ?? "manual"} &nbsp;•&nbsp; Steps: {w.steps?.length}
              </p>
              <div className="space-y-1 text-xs text-gray-600 mb-4">
                {w.steps?.map((s: any) => (
                  <div key={s.id} className="flex items-center gap-1">
                    <span className="text-gray-400">▸</span>
                    <span>{s.service}</span>
                    <span className="text-gray-300">→</span>
                    <span>{s.action}</span>
                  </div>
                ))}
              </div>
              <button
                onClick={() => run(w.id)}
                className="w-full px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700"
              >
                <Play className="w-4 h-4 mr-2 inline" /> Run Workflow
              </button>
            </div>
          ))}
        </div>
      )}

      {runResult && (
        <div className="bg-white p-4 rounded border border-gray-200 shadow-sm mt-6">
          <h3 className="font-semibold text-gray-900 mb-2">Run Result</h3>
          <p className="text-xs text-gray-500 mb-2">Status: <span className="font-mono">{runResult.status}</span></p>
          <pre className="text-xs text-gray-600 bg-gray-50 p-3 rounded overflow-x-auto">{JSON.stringify(runResult.step_outputs ?? runResult, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
