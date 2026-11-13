"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

const OPS = [
  { id: "gte", label: "≥" }, { id: "lte", label: "≤" }, { id: "gt", label: ">" }, { id: "lt", label: "<" },
  { id: "eq", label: "=" }, { id: "ne", label: "≠" }, { id: "in", label: "in" }, { id: "contains", label: "contains" },
];

type Cond = { field: string; op: string; value: string };

export default function SegmentsPage() {
  const [fields, setFields] = useState<Record<string, string>>({});
  const [computed, setComputed] = useState<Record<string, string>>({});
  const [segments, setSegments] = useState<any[]>([]);
  const [conds, setConds] = useState<Cond[]>([{ field: "days_until_due", op: "lte", value: "7" }]);
  const [logic, setLogic] = useState<"all" | "any">("all");
  const [name, setName] = useState("");
  const [preview, setPreview] = useState<any>(null);
  const [msg, setMsg] = useState("");

  const load = () => {
    apiGet("/analysis/fields").then((d: any) => {
      setComputed(d.computed ?? {});
      setFields(d.types ?? {});
    }).catch(() => {});
    apiGet("/analysis/segments").then((d: any) => setSegments(d.segments ?? [])).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const buildCriteria = () => {
    const c: any = {};
    for (const cond of conds) {
      if (!cond.field || cond.value === "") continue;
      const numeric = ["number"].includes(fields[cond.field]);
      let v: any = cond.value;
      if (numeric) { const n = Number(cond.value); if (!Number.isNaN(n)) v = n; }
      if (cond.op === "in" || cond.op === "not_in") {
        v = cond.value.split(",").map((x) => (numeric ? Number(x) : x.trim())).filter((x) => x !== "");
      }
      if (cond.op === "is_true") v = true;
      if (cond.op === "is_false") v = false;
      if (c[cond.field] === undefined) {
        c[cond.field] = {};
      }
      if (typeof c[cond.field] === "object") {
        c[cond.field][cond.op] = v;
      } else {
        c[cond.field] = { [cond.op]: v };
      }
    }
    return c;
  };

  const runPreview = async () => {
    setMsg("Previewing…");
    try {
      const r: any = await apiPost("/analysis/segments/preview", { criteria: buildCriteria() });
      setPreview(r);
      setMsg("");
    } catch (e: any) { setMsg("Preview failed: " + e.message); }
  };

  const save = async () => {
    if (!name) return;
    await apiPost("/analysis/segments", { name, criteria: buildCriteria() });
    setName("");
    load();
  };

  const allFields = Object.keys(fields);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Segments</h1>
          <p className="text-gray-500 text-sm mt-1 max-w-2xl">
            Build a live filter over your customer records using raw fields (plan, MRR, LTV) and computed ones
            (days until due, health/LTV/value tier, churn risk). Then use a segment as a campaign target.
          </p>
        </div>
        <div className="flex gap-2">
          <select value={logic} onChange={(e) => setLogic(e.target.value as any)} className="border border-gray-300 rounded px-2 py-2 text-sm">
            <option value="all">match ALL</option>
            <option value="any">match ANY</option>
          </select>
        </div>
      </div>

      {msg && <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-2 rounded text-sm">{msg}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 space-y-3 lg:col-span-2">
          <h3 className="font-semibold text-gray-900 text-sm">Conditions</h3>
          {conds.map((c, i) => (
            <div key={i} className="flex flex-wrap gap-2 items-center">
              <select value={c.field} onChange={(e) => setConds(conds.map((x, j) => j === i ? { ...x, field: e.target.value } : x))}
                className="border border-gray-300 rounded px-2 py-1.5 text-sm font-mono min-w-[180px]">
                <optgroup label="computed">
                  {Object.keys(computed).map((f) => <option key={f} value={f}>{f}</option>)}
                </optgroup>
                <optgroup label="record fields">
                  {allFields.filter((f) => !computed[f]).map((f) => <option key={f} value={f}>{f}</option>)}
                </optgroup>
              </select>
              <select value={c.op} onChange={(e) => setConds(conds.map((x, j) => j === i ? { ...x, op: e.target.value } : x))}
                className="border border-gray-300 rounded px-2 py-1.5 text-sm">
                {OPS.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
              </select>
              <input value={c.value} onChange={(e) => setConds(conds.map((x, j) => j === i ? { ...x, value: e.target.value } : x))}
                placeholder="value" className="flex-1 min-w-[120px] border border-gray-300 rounded px-2 py-1.5 text-sm" />
              <button onClick={() => setConds(conds.filter((_, j) => j !== i))} className="text-red-400 px-2">✕</button>
            </div>
          ))}
          <button onClick={() => setConds([...conds, { field: "churn_risk_tier", op: "in", value: "critical,high" }])}
            className="text-xs text-indigo-600 hover:underline">+ add condition</button>

          <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-100">
            <button onClick={runPreview} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Preview match</button>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Segment name" className="border border-gray-300 rounded px-3 py-2 text-sm" />
            <button onClick={save} disabled={!name} className="px-4 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50 disabled:opacity-50">Save segment</button>
          </div>

          {preview && (
            <div className="bg-gray-50 border border-gray-100 rounded p-4 text-sm">
              <p className="font-semibold text-gray-900">{preview.matched} of {preview.total_customers} customers match</p>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-2 mt-3 text-center">
                <div className="bg-white rounded p-2"><p className="text-lg font-bold">${preview.aggregate.total_mrr}</p><p className="text-[10px] text-gray-400">MRR in segment</p></div>
                <div className="bg-white rounded p-2"><p className="text-lg font-bold">${preview.aggregate.total_ltv}</p><p className="text-[10px] text-gray-400">LTV</p></div>
                <div className="bg-white rounded p-2"><p className="text-lg font-bold">{preview.aggregate.avg_health}</p><p className="text-[10px] text-gray-400">avg health</p></div>
                <div className="bg-white rounded p-2"><p className="text-lg font-bold text-amber-600">{preview.aggregate.due_soon}</p><p className="text-[10px] text-gray-400">due soon</p></div>
                <div className="bg-white rounded p-2"><p className="text-lg font-bold text-red-600">{preview.aggregate.overdue}</p><p className="text-[10px] text-gray-400">overdue</p></div>
                <div className="bg-white rounded p-2"><p className="text-lg font-bold text-red-600">${preview.aggregate.mrr_at_risk}</p><p className="text-[10px] text-gray-400">MRR at risk</p></div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                {preview.members.slice(0, 12).map((m: any) => (
                  <span key={m.id} className="text-xs bg-white border border-gray-200 px-2 py-0.5 rounded">{m.name || m.email}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-900 text-sm mb-3">Saved segments ({segments.length})</h3>
            {segments.length === 0 && <p className="text-sm text-gray-400">None yet.</p>}
            {segments.map((s) => (
              <div key={s.segment_id} className="p-3 bg-gray-50 rounded border border-gray-100 mb-2">
                <p className="font-medium text-sm">{s.name}</p>
                <p className="text-xs text-gray-400 font-mono mt-0.5">{JSON.stringify(s.criteria)}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-900 text-sm mb-2">Computed fields</h3>
            <div className="space-y-1">
              {Object.entries(computed).map(([k, v]) => (
                <p key={k} className="text-xs"><code className="font-mono text-indigo-600">{k}</code> <span className="text-gray-500">{v}</span></p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
