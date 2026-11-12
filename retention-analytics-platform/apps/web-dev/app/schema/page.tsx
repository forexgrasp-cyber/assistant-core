"use client";

import { useState } from "react";
import { apiPost, apiGet, authHeaders } from "@/lib/api";

const SCHEMA = "client";

export default function EntitiesPage() {
  const [records, setRecords] = useState<any[]>([]);
  const [form, setForm] = useState(`{"name": "Acme Corp", "email": "ops@acme.com", "plan": "growth"}`);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const d: any = await apiGet(`/entities/${SCHEMA}`);
      setRecords(d.records ?? []);
    } catch (e: any) {
      setResult({ error: e.message });
    }
  };

  const create = async () => {
    setBusy(true);
    setResult(null);
    try {
      let data: any;
      try { data = JSON.parse(form); } catch { throw new Error("Invalid JSON"); }
      const r: any = await apiPost(`/entities/${SCHEMA}`, { schema_id: SCHEMA, data });
      setResult({ ok: true, data: r });
      await load();
    } catch (e: any) {
      setResult({ ok: false, error: e.message });
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await fetch(`/api/v1/entities/${SCHEMA}/${id}`, { method: "DELETE", headers: authHeaders() });
      await load();
    } catch {}
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Entities</h1>
        <p className="text-gray-500 text-sm mt-1">
          Schema-as-data CRUD. Schema <code className="font-mono text-xs">{SCHEMA}</code> — create records with any JSON,
          list, delete. All tenant-scoped.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-3">
          <h3 className="font-semibold text-gray-900 text-sm">Create record</h3>
          <textarea
            value={form}
            onChange={(e) => setForm(e.target.value)}
            rows={5}
            className="w-full border border-gray-300 rounded px-3 py-2 text-xs font-mono"
          />
          <div className="flex gap-2">
            <button onClick={create} disabled={busy} className="px-4 py-2 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700 disabled:opacity-50">
              {busy ? "Creating…" : "Create"}
            </button>
            <button onClick={load} className="px-4 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">
              Refresh list
            </button>
          </div>
          <p className="text-xs text-gray-400 font-mono">POST /api/v1/entities/{SCHEMA}</p>
          {result && (
            <pre className={`text-xs p-3 rounded overflow-x-auto ${result.ok ? "bg-green-50" : "bg-red-50"}`}>
              {JSON.stringify(result.ok ? result.data : result, null, 2)}
            </pre>
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">Records ({records.length})</h3>
          {records.length === 0 && <p className="text-sm text-gray-400">No records. Create one or refresh.</p>}
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {records.map((r: any) => (
              <div key={r.id} className="flex items-start justify-between p-3 bg-gray-50 rounded border border-gray-100">
                <pre className="text-xs font-mono text-gray-700 overflow-x-auto">{JSON.stringify(r.data ?? r, null, 2)}</pre>
                <button onClick={() => remove(r.id)} className="text-red-400 hover:text-red-600 text-xs ml-2 shrink-0">✕</button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
