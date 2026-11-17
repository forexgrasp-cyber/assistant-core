"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

export default function CustomersPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [due, setDue] = useState<any>(null);
  const [selected, setSelected] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [nba, setNba] = useState<any>(null);
  const [actions, setActions] = useState<any[]>([]);
  const [scanMsg, setScanMsg] = useState("");
  const [importText, setImportText] = useState("");
  const [importMapping, setImportMapping] = useState<Record<string, string>>({});
  const [importCols, setImportCols] = useState<string[]>([]);
  const [importResult, setImportResult] = useState<any>(null);
  const [showImport, setShowImport] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", phone: "", plan: "", mrr: "", service_name: "", last_service_date: "", service_interval_days: "" });

  const load = () => {
    apiGet("/analysis/profiles").then((d: any) => setRows(d.profiles ?? [])).catch(() => {});
    apiGet("/service-due?within_days=14").then(setDue).catch(() => {});
    apiGet("/analysis/next-best-action").then((d: any) => setActions(d.recommendations ?? [])).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const create = async () => {
    try {
      await apiPost("/customers", {
        ...form,
        mrr: parseFloat(form.mrr || "0"),
        service_interval_days: parseInt(form.service_interval_days || "0"),
        last_service_date: form.last_service_date || null,
      });
      setForm({ name: "", email: "", phone: "", plan: "", mrr: "", service_name: "", last_service_date: "", service_interval_days: "" });
      load();
    } catch (e: any) { setScanMsg("Error: " + e.message); }
  };

  const openProfile = async (id: string) => {
    const r: any = await apiGet(`/customers/${id}`);
    setSelected(r.profile);
    const t: any = await apiGet(`/customers/${id}/timeline`);
    setTimeline(t.timeline ?? []);
    const n: any = await apiGet(`/analysis/next-best-action?customer_id=${id}`);
    setNba(n.recommendation ?? null);
  };

  const scanDue = async () => {
    setScanMsg("Scanning…");
    try {
      const scan: any = await apiGet("/service-due?within_days=14");
      const r: any = await apiPost("/service-due/reminders?within_days=14");
      setScanMsg(`Scanned ${scan.scanned} customers: ${scan.due_soon_count} due soon, ${scan.overdue_count} overdue → ${r.count} reminders scheduled (the service-due-reminder flow acts on them).`);
      load();
    } catch (e: any) {
      setScanMsg("Scan failed: " + e.message);
    }
  };

  const runAutoApproach = async () => {
    setScanMsg("Running the automatic approach…");
    try {
      const scan: any = await apiPost("/auto-approach/scan");
      const r: any = await apiPost("/auto-approach/run", {});
      setScanMsg(`Auto-approach: ${scan.total_customers} customers scanned → ${r.campaigns_created} campaigns created and run.`);
      load();
    } catch (e: any) {
      setScanMsg("Auto-approach failed: " + e.message);
    }
  };

  const onCsvText = async (text: string) => {
    setImportText(text);
    const cols = (text.split("\n")[0] || "").split(",").map((c) => c.trim()).filter(Boolean);
    setImportCols(cols);
    if (cols.length) {
      try {
        const r: any = await apiPost("/customers/map-columns", cols);
        setImportMapping(r.mapping ?? {});
      } catch {}
    }
  };

  const runImport = async () => {
    try {
      const r: any = await apiPost("/customers/import", { csv: importText, mapping: importMapping });
      setImportResult(r.import);
      load();
    } catch (e: any) { setImportResult({ error: e.message }); }
  };

  const exportCsv = async () => {
    const r: any = await apiGet("/customers/export?format=csv");
    const blob = new Blob([r.csv ?? ""], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "customers.csv";
    a.click();
  };

  const healthBadge = (tier: string) =>
    tier === "critical" ? "bg-red-100 text-red-700" : tier === "at_risk" ? "bg-amber-100 text-amber-700" : tier === "watch" ? "bg-sky-100 text-sky-700" : "bg-green-100 text-green-700";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customers</h1>
          <p className="text-gray-500 text-sm mt-1">
            Customer records with computed analysis: days until due, health/LTV/value tiers, churn risk, next best action.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowImport(!showImport)} className="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Import CSV</button>
          <button onClick={exportCsv} className="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Export CSV</button>
          <button onClick={scanDue} className="px-3 py-2 bg-amber-600 text-white rounded text-sm hover:bg-amber-700">Scan due services</button>
          <button onClick={runAutoApproach} className="px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Auto-approach</button>
        </div>
      </div>

      {scanMsg && <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-2 rounded text-sm">{scanMsg}</div>}

      {showImport && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5 space-y-3">
          <h3 className="font-semibold text-gray-900 text-sm">Import customers from CSV</h3>
          <textarea value={importText} onChange={(e) => onCsvText(e.target.value)} rows={5}
            placeholder={"name,email,plan,mrr,service_name,last_service_date,service_interval_days\nJane,jane@x.com,premium,120,oil change,2026-05-15,180"}
            className="w-full border border-gray-300 rounded px-3 py-2 text-xs font-mono" />
          {importCols.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {importCols.map((c) => <span key={c} className="text-xs bg-gray-100 px-2 py-1 rounded font-mono">{c} → {importMapping[c] ?? "skip"}</span>)}
            </div>
          )}
          <button onClick={runImport} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Import</button>
          {importResult && (
            <p className={`text-sm ${importResult.error ? "text-red-600" : "text-green-700"}`}>
              {importResult.error ? importResult.error : `Imported: ${importResult.created} created, ${importResult.updated} updated`}
            </p>
          )}
        </div>
      )}

      {/* Next best actions */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <h3 className="font-semibold text-gray-900 text-sm mb-3">Next best action ({actions.length})</h3>
        {actions.length === 0 && <p className="text-sm text-gray-400">No customers need action right now.</p>}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
          {actions.slice(0, 9).map((a, i) => (
            <button key={i} onClick={() => openProfile(a.customer_id)}
              className="text-left p-3 bg-gray-50 rounded border border-gray-100 hover:border-indigo-300">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-gray-900">{a.name || a.email}</p>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${a.priority <= 2 ? "bg-red-100 text-red-700" : a.priority <= 4 ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600"}`}>P{a.priority}</span>
              </div>
              <p className="text-xs text-indigo-600 mt-1">{a.action.replace(/_/g, " ")}</p>
              <p className="text-xs text-gray-500">{a.reason}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Due service summary */}
      {due && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">{due.scanned ?? 0}</p><p className="text-xs text-gray-400">customers scanned</p>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-amber-700">{due.due_soon_count ?? 0}</p><p className="text-xs text-gray-500">due within 14 days</p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-red-700">{due.overdue_count ?? 0}</p><p className="text-xs text-gray-500">overdue</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">Add customer</h3>
          <div className="space-y-2">
            {[
              { k: "name", l: "Name" }, { k: "email", l: "Email" }, { k: "phone", l: "Phone" },
              { k: "plan", l: "Plan / tier" }, { k: "mrr", l: "Value ($)" },
              { k: "service_name", l: "Recurring service (e.g. oil change)" },
              { k: "last_service_date", l: "Last service date", t: "date" },
              { k: "service_interval_days", l: "Interval (days)", t: "number" },
            ].map((f) => (
              <div key={f.k}>
                <label className="text-xs text-gray-500">{f.l}</label>
                <input type={f.t ?? "text"} value={(form as any)[f.k]} onChange={(e) => setForm({ ...form, [f.k]: e.target.value })}
                  className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-0.5" />
              </div>
            ))}
          </div>
          <button onClick={create} className="mt-3 w-full px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Save customer</button>
          <p className="text-xs text-gray-400 mt-2">Next due date is computed from last date + interval.</p>
        </div>

        <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">All customers ({rows.length})</h3>
          {rows.length === 0 && <p className="text-sm text-gray-400">No customers yet — add one, import a CSV, or run the demo.</p>}
          <div className="overflow-x-auto max-h-[420px]">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b text-xs text-gray-400">
                <th className="py-2">Customer</th><th className="py-2">Plan</th><th className="py-2">MRR</th>
                <th className="py-2">Next due</th><th className="py-2">Health</th><th className="py-2">Churn risk</th><th className="py-2">Value</th>
              </tr></thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} onClick={() => openProfile(c.id)} className="border-b last:border-0 hover:bg-gray-50 cursor-pointer">
                    <td className="py-2">
                      {c.name || c.email}
                      <p className="text-xs text-gray-400">{c.service_name}</p>
                    </td>
                    <td className="py-2 capitalize">{c.plan || "-"}</td>
                    <td className="py-2">${c.mrr}</td>
                    <td className="py-2 text-xs">
                      {c.next_due_date ? c.next_due_date.slice(0, 10) : "-"}
                      {c.days_until_due != null && (
                        <span className={`ml-1 px-1 rounded ${c.overdue ? "bg-red-100 text-red-700" : c.due_soon ? "bg-amber-100 text-amber-700" : "text-gray-400"}`}>
                          {c.overdue ? `${-c.days_until_due}d late` : `${c.days_until_due}d`}
                        </span>
                      )}
                    </td>
                    <td className="py-2"><span className={`text-[10px] px-1.5 py-0.5 rounded ${healthBadge(c.health_tier)}`}>{c.health_score}</span></td>
                    <td className="py-2 text-xs">{c.churn_risk ?? "-"} <span className="text-gray-400">{c.churn_risk_tier ?? ""}</span></td>
                    <td className="py-2 text-xs">{c.ltv_tier} <span className="text-gray-400">#{c.value_rank}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {selected && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-900 text-sm">Customer 360 — {selected.name || selected.email}</h3>
            <button onClick={() => { setSelected(null); setTimeline([]); setNba(null); }} className="text-gray-400 text-xs hover:underline">Close</button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-4">
            <div><p className="text-xs text-gray-400">Value</p><p className="font-bold">${selected.mrr}</p></div>
            <div><p className="text-xs text-gray-400">LTV</p><p className="font-bold">${selected.ltv}</p></div>
            <div><p className="text-xs text-gray-400">Health</p><p className="font-bold">{selected.health_score}/100</p></div>
            <div><p className="text-xs text-gray-400">Next service</p><p className="font-bold">{selected.next_due_date?.slice(0,10) ?? "-"}</p></div>
          </div>
          {nba && (
            <div className="bg-indigo-50 border border-indigo-200 rounded p-3 mb-4 text-sm">
              <b>Next best action:</b> {nba.action.replace(/_/g, " ")} (priority {nba.priority}, channel {nba.channel})
              <p className="text-xs text-gray-600">{nba.reason}{nba.flow ? ` · flow: ${nba.flow}` : ""}{nba.offer ? ` · offer: ${nba.offer}` : ""}</p>
            </div>
          )}
          <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Timeline ({timeline.length})</h4>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {timeline.map((t, i) => (
              <div key={i} className="flex gap-2 text-xs py-1 border-b last:border-0">
                <span className="text-gray-400 w-40 shrink-0">{String(t.at).slice(0, 16).replace("T", " ")}</span>
                <span className="font-medium w-32 shrink-0">{t.type}</span>
                <span className="text-gray-600 truncate">{t.detail}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
