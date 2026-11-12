"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

const FIELDS = ["health_score", "mrr", "ltv", "days_until_due", "plan", "classes_remaining", "seats", "nps_score"];
const OPS = [
  { id: "lt", label: "<" }, { id: "lte", label: "≤" }, { id: "gt", label: ">" }, { id: "gte", label: "≥" }, { id: "eq", label: "=" },
];

export default function SegmentsPage() {
  const [segments, setSegments] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [rows, setRows] = useState<{ field: string; op: string; value: string }[]>([{ field: "days_until_due", op: "lte", value: "7" }]);
  const [preview, setPreview] = useState<any>(null);
  const [msg, setMsg] = useState("");

  const load = () => {
    apiGet("/segments").then((d: any) => setSegments(d.segments ?? [])).catch(() => {});
    apiGet("/customers").then((d: any) => setCustomers(d.profiles ?? [])).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const buildCriteria = () => {
    const c: any = {};
    for (const r of rows) {
      if (!r.field || r.value === "") continue;
      const v = isNaN(Number(r.value)) ? r.value : Number(r.value);
      if (r.op === "eq") c[r.field] = v;
      else c[r.field] = { [r.op]: v };
    }
    return c;
  };

  const save = async () => {
    try {
      await apiPost("/segments", { name, criteria: buildCriteria() });
      setMsg(`Saved segment "${name}"`);
      setName("");
      load();
    } catch (e: any) { setMsg("Error: " + e.message); }
  };

  const evaluate = async () => {
    try {
      const r: any = await apiPost("/segments/evaluate", { criteria: buildCriteria(), clients: customers });
      setPreview(r);
    } catch (e: any) { setMsg("Error: " + e.message); }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Segments</h1>
        <p className="text-gray-500 text-sm mt-1">
          A segment is a live filter over your customer records. Build one, preview who matches, then use it as a campaign target.
        </p>
      </div>

      {msg && <div className="bg-indigo-50 border border-indigo-200 text-indigo-800 px-4 py-2 rounded text-sm">{msg}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 space-y-3">
          <h3 className="font-semibold text-gray-900 text-sm">New segment</h3>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Segment name (e.g. Oil change due soon)" className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
          {rows.map((r, i) => (
            <div key={i} className="flex gap-2">
              <select value={r.field} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, field: e.target.value } : x))} className="border border-gray-300 rounded px-2 py-1.5 text-sm font-mono">
                {FIELDS.map((f) => <option key={f}>{f}</option>)}
              </select>
              <select value={r.op} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, op: e.target.value } : x))} className="border border-gray-300 rounded px-2 py-1.5 text-sm">
                {OPS.map((o) => <option key={o.id}>{o.label}</option>)}
              </select>
              <input value={r.value} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, value: e.target.value } : x))} placeholder="value" className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm" />
              <button onClick={() => setRows(rows.filter((_, j) => j !== i))} className="text-red-400 px-2">✕</button>
            </div>
          ))}
          <button onClick={() => setRows([...rows, { field: "mrr", op: "gt", value: "" }])} className="text-xs text-indigo-600 hover:underline">+ add condition</button>
          <div className="flex gap-2">
            <button onClick={evaluate} className="px-4 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Preview match ({customers.length} customers)</button>
            <button onClick={save} disabled={!name} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50">Save segment</button>
          </div>
          {preview && (
            <div className="bg-green-50 border border-green-200 rounded p-3 text-sm">
              <b>{preview.matched}</b> of {preview.total} customers match.
              <div className="mt-1 flex flex-wrap gap-1">
                {(preview.members ?? []).slice(0, 10).map((m: any) => <span key={m.id} className="text-xs bg-white border px-1.5 py-0.5 rounded">{m.name || m.email}</span>)}
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">Saved segments ({segments.length})</h3>
          {segments.length === 0 && <p className="text-sm text-gray-400">None yet.</p>}
          <div className="space-y-2">
            {segments.map((s) => (
              <div key={s.segment_id} className="p-3 bg-gray-50 rounded border border-gray-100">
                <p className="font-medium text-sm">{s.name}</p>
                <p className="text-xs text-gray-400 font-mono">{JSON.stringify(s.criteria)}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
