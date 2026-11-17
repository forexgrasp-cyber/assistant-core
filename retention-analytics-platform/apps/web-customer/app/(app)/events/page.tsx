"use client";

import { useEffect, useRef, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

interface FieldSchema { field: string; label: string; type: string; required: string; options?: string; }
interface EventSchema { [eventType: string]: FieldSchema[]; }

type Mode = "single" | "bulk";

export default function Events() {
  const [schemas, setSchemas] = useState<EventSchema>({});
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [mode, setMode] = useState<Mode>("single");

  // Single mode
  const [eventType, setEventType] = useState("");
  const [form, setForm] = useState<Record<string, string>>({});
  const [singleResult, setSingleResult] = useState<any>(null);

  // Bulk mode
  const [bulkEventType, setBulkEventType] = useState("");
  const [csvText, setCsvText] = useState("");
  const [csvColumns, setCsvColumns] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [suggested, setSuggested] = useState<Record<string, string>>({});
  const [bulkResult, setBulkResult] = useState<any>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    apiGet("/events/schemas").then((d: any) => {
      setSchemas(d.schemas ?? {});
      const first = Object.keys(d.schemas ?? {})[0];
      setEventType(first); setBulkEventType(first);
      setForm({});
    }).catch(() => {});
    apiGet("/workflows").then((d: any) => setWorkflows(d.workflows ?? [])).catch(() => {});
  }, []);

  const pickType = (t: string) => {
    setEventType(t);
    setForm({});
    setSingleResult(null);
  };

  const schema = schemas[eventType] ?? [];
  const matchingWorkflows = workflows.filter((w) => w.trigger_event === eventType);

  const sendSingle = async () => {
    try {
      const r = await apiPost("/events", {
        type: eventType,
        tenant_id: "00000000-0000-0000-0000-000000000001",
        idempotency_key: `ui-${Date.now()}`,
        payload: form,
      });
      setSingleResult({ ok: true, data: r });
    } catch (e: any) {
      setSingleResult({ ok: false, error: e.message });
    }
  };

  // Bulk: parse CSV
  const parseCsv = (text: string) => {
    const lines = text.trim().split("\n");
    if (lines.length < 2) return { columns: [], rows: [] };
    const columns = lines[0].split(",").map((c) => c.trim());
    const rows = lines.slice(1).map((line) => {
      const values = line.split(",");
      const row: Record<string, string> = {};
      columns.forEach((c, i) => { row[c] = (values[i] ?? "").trim(); });
      return row;
    });
    return { columns, rows };
  };

  const onCsvChange = async (text: string) => {
    setCsvText(text);
    const { columns } = parseCsv(text);
    setCsvColumns(columns);
    if (columns.length > 0 && bulkEventType) {
      try {
        const r: any = await apiPost(`/events/map-fields?event_type=${encodeURIComponent(bulkEventType)}`, { columns });
        setSuggested(r.mapping ?? {});
        setMapping(r.mapping ?? {});
      } catch {}
    }
  };

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => onCsvChange(String(reader.result ?? ""));
    reader.readAsText(file);
  };

  const runBulk = async () => {
    const { rows } = parseCsv(csvText);
    try {
      const r = await apiPost("/events/bulk-import", {
        event_type: bulkEventType,
        rows,
        mapping,
      });
      setBulkResult(r.import);
    } catch (e: any) {
      setBulkResult({ error: e.message });
    }
  };

  const exportCsv = async () => {
    const r: any = await apiGet("/events/export");
    const blob = new Blob([r.csv ?? ""], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "events-export.csv";
    a.click();
  };

  const bulkSchema = schemas[bulkEventType] ?? [];

  return (
    <div className="max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Events</h1>
        <p className="text-gray-500 text-sm mt-1">
          Events are customer actions that trigger workflows. Add one at a time, or bulk-import a CSV with column mapping.
        </p>
      </div>

      {/* Mode tabs */}
      <div className="flex gap-2">
        <button onClick={() => setMode("single")} className={`px-4 py-2 rounded-lg text-sm font-medium ${mode === "single" ? "bg-indigo-600 text-white" : "bg-white border border-gray-200 text-gray-600"}`}>Single event</button>
        <button onClick={() => setMode("bulk")} className={`px-4 py-2 rounded-lg text-sm font-medium ${mode === "bulk" ? "bg-indigo-600 text-white" : "bg-white border border-gray-200 text-gray-600"}`}>Bulk import (CSV)</button>
      </div>

      {mode === "single" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 uppercase mb-1">What happened?</label>
              <select value={eventType} onChange={(e) => pickType(e.target.value)} className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono">
                {Object.keys(schemas).map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            {schema.map((f) => (
              <div key={f.field}>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  {f.label} {f.required === "true" && <span className="text-red-500">*</span>}
                </label>
                {f.type === "select" ? (
                  <select value={form[f.field] ?? ""} onChange={(e) => setForm({ ...form, [f.field]: e.target.value })} className="w-full border border-gray-300 rounded px-3 py-2 text-sm">
                    <option value="">—</option>
                    {(f.options ?? "").split(",").map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input
                    type={f.type === "number" ? "number" : f.type === "email" ? "email" : "text"}
                    value={form[f.field] ?? ""}
                    onChange={(e) => setForm({ ...form, [f.field]: e.target.value })}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                  />
                )}
              </div>
            ))}
            <button onClick={sendSingle} className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">Ingest event</button>
            {singleResult && (
              <pre className={`text-xs p-3 rounded overflow-x-auto ${singleResult.ok ? "bg-green-50" : "bg-red-50"}`}>
                {JSON.stringify(singleResult.ok ? singleResult.data : singleResult, null, 2)}
              </pre>
            )}
          </div>
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
            <h3 className="font-semibold text-gray-900 text-sm mb-3">This triggers:</h3>
            {matchingWorkflows.length > 0 ? matchingWorkflows.map((w) => (
              <div key={w.id} className="bg-indigo-50 border border-indigo-200 rounded p-3 mb-2">
                <p className="font-medium text-sm text-indigo-900">{w.name}</p>
                <div className="flex flex-wrap gap-1 mt-2">
                  {w.steps.map((s: any, i: number) => (
                    <span key={s.id} className="flex items-center gap-1">
                      {i > 0 && <span className="text-gray-300">→</span>}
                      <span className="bg-white border px-2 py-0.5 rounded font-mono text-xs">{s.service}.{s.action}</span>
                    </span>
                  ))}
                </div>
              </div>
            )) : <p className="text-sm text-gray-400">No workflow bound — recorded in audit log only.</p>}
          </div>
        </div>
      )}

      {mode === "bulk" && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Event type</label>
                <select value={bulkEventType} onChange={(e) => { setBulkEventType(e.target.value); onCsvChange(csvText); }} className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono">
                  {Object.keys(schemas).map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Upload CSV or paste</label>
                <input ref={fileRef} type="file" accept=".csv" onChange={onFile} className="text-xs" />
              </div>
            </div>
            <textarea
              value={csvText}
              onChange={(e) => onCsvChange(e.target.value)}
              rows={6}
              placeholder={"email,name,plan\njane@acme.com,Jane,enterprise\nbob@acme.com,Bob,starter"}
              className="w-full border border-gray-300 rounded px-3 py-2 text-xs font-mono"
            />
            <p className="text-xs text-gray-400">{csvColumns.length} columns detected: {csvColumns.join(", ")}</p>
          </div>

          {/* Field mapping */}
          {csvColumns.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
              <h3 className="font-semibold text-gray-900 text-sm mb-1">Map columns → event fields</h3>
              <p className="text-xs text-gray-400 mb-3">Suggested mapping applied — adjust as needed. Target fields: {bulkSchema.map((f) => f.field).join(", ")}</p>
              <div className="space-y-2">
                {csvColumns.map((col) => (
                  <div key={col} className="flex items-center gap-2">
                    <span className="text-xs font-mono bg-gray-100 px-2 py-1 rounded w-40 truncate">{col}</span>
                    <span className="text-gray-400">→</span>
                    <select
                      value={mapping[col] ?? ""}
                      onChange={(e) => setMapping({ ...mapping, [col]: e.target.value })}
                      className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-xs font-mono"
                    >
                      <option value="">— skip —</option>
                      {bulkSchema.map((f) => <option key={f.field} value={f.field}>{f.field} ({f.label})</option>)}
                    </select>
                    {suggested[col] && suggested[col] !== mapping[col] && (
                      <button onClick={() => setMapping({ ...mapping, [col]: suggested[col] })} className="text-xs text-indigo-600 hover:underline">suggested: {suggested[col]}</button>
                    )}
                  </div>
                ))}
              </div>
              <div className="flex gap-2 mt-4">
                <button onClick={runBulk} className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">Import {parseCsv(csvText).rows.length} rows</button>
                <button onClick={exportCsv} className="px-4 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Export CSV</button>
              </div>
              {bulkResult && (
                <div className={`mt-3 p-3 rounded text-sm ${bulkResult.error ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"}`}>
                  {bulkResult.error ? bulkResult.error : `Imported ${bulkResult.imported}/${bulkResult.rows_total} rows for ${bulkResult.event_type}`}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
