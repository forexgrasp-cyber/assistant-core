"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost, authHeaders } from "@/lib/api";

const WIDGETS = [
  { id: "retention", label: "Retention & Churn" },
  { id: "rfm", label: "RFM Segments" },
  { id: "cohorts", label: "Cohorts" },
  { id: "saas", label: "SaaS Metrics (MRR/NRR/LTV)" },
  { id: "nps", label: "NPS Score" },
];

const TIME_RANGES = ["7d", "30d", "90d", "12m", "all"];

export default function Reports() {
  const [saved, setSaved] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [format, setFormat] = useState("json");
  const [timeRange, setTimeRange] = useState("30d");
  const [campaign, setCampaign] = useState("");
  const [segment, setSegment] = useState("");
  const [selectedWidgets, setSelectedWidgets] = useState<string[]>(["retention", "saas"]);
  const [schedule, setSchedule] = useState("");
  const [lastRun, setLastRun] = useState<any>(null);
  const [running, setRunning] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<string[]>([]);
  const [exportDs, setExportDs] = useState("customers");
  const [exportFmt, setExportFmt] = useState("csv");
  const [exportInfo, setExportInfo] = useState("");
  const [importHistory, setImportHistory] = useState<any[]>([]);

  const load = () => {
    apiGet("/reports/saved").then((d: any) => setSaved(d.reports ?? [])).catch(() => {});
    apiGet("/export/datasets").then((d: any) => setDatasets(d.datasets ?? [])).catch(() => {});
    apiGet("/data-transfer/history").then((d: any) => setImportHistory(d.imports ?? [])).catch(() => {});
  };

  const doExport = async () => {
    const r: any = await apiPost("/export", { dataset: exportDs, format: exportFmt });
    if (exportFmt === "csv" && r.csv) {
      const blob = new Blob([r.csv], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${exportDs}.csv`;
      a.click();
    }
    setExportInfo(`Exported ${r.count} ${exportDs} rows (${exportFmt})`);
  };

  const exportCampaigns = async () => {
    const r: any = await apiGet("/campaigns/export?format=csv");
    const blob = new Blob([r.csv ?? ""], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "campaigns.csv";
    a.click();
    setExportInfo(`Exported ${r.count} campaigns`);
  };

  useEffect(() => { load(); }, []);

  const saveReport = async () => {
    if (!name) return;
    await apiPost("/reports/saved", {
      name, description, format,
      filters: { time_range: timeRange, campaign: campaign || null, segment: segment || null },
      widgets: selectedWidgets,
      schedule: schedule ? { frequency: schedule, email_to: "team@company.com" } : null,
    });
    setName(""); setDescription("");
    load();
  };

  const runReport = async (reportId: string) => {
    setRunning(reportId);
    try {
      const r: any = await apiPost(`/reports/saved/${reportId}/run`);
      setLastRun(r.result);
    } catch (e: any) {
      setLastRun({ error: e.message });
    } finally {
      setRunning(null);
      load();
    }
  };

  const deleteReport = async (reportId: string) => {
    await fetch(`/api/v1/reports/saved/${reportId}`, { method: "DELETE", headers: authHeaders() });
    load();
  };

  const toggleWidget = (id: string) => {
    setSelectedWidgets((prev) => prev.includes(id) ? prev.filter((w) => w !== id) : [...prev, id]);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-500 text-sm mt-1">
          Build a report from analytics widgets, filter by time/campaign/target, save it, re-run anytime, download.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Builder */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
          <h3 className="font-semibold text-gray-900 text-sm">New report</h3>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Report name *</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Q4 Retention Review" className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Description</label>
            <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this report answers" className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Time range</label>
            <div className="flex gap-1">
              {TIME_RANGES.map((t) => (
                <button key={t} onClick={() => setTimeRange(t)} className={`px-2 py-1 rounded text-xs ${timeRange === t ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600"}`}>{t}</button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Campaign filter</label>
              <input value={campaign} onChange={(e) => setCampaign(e.target.value)} placeholder="e.g. win-back-q4" className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Target segment</label>
              <input value={segment} onChange={(e) => setSegment(e.target.value)} placeholder="e.g. at-risk-saas" className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" />
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Include analytics</label>
            <div className="flex flex-wrap gap-1">
              {WIDGETS.map((w) => (
                <button key={w.id} onClick={() => toggleWidget(w.id)} className={`px-2 py-1 rounded text-xs border ${selectedWidgets.includes(w.id) ? "bg-indigo-50 border-indigo-300 text-indigo-700" : "bg-white border-gray-200 text-gray-500"}`}>
                  {selectedWidgets.includes(w.id) ? "✓ " : ""}{w.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Format</label>
              <select value={format} onChange={(e) => setFormat(e.target.value)} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm">
                <option value="json">JSON</option><option value="pdf">PDF</option><option value="csv">CSV</option><option value="html">HTML</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Schedule (optional)</label>
              <select value={schedule} onChange={(e) => setSchedule(e.target.value)} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm">
                <option value="">None</option><option value="daily">Daily email</option><option value="weekly">Weekly email</option><option value="monthly">Monthly email</option>
              </select>
            </div>
          </div>

          <button onClick={saveReport} disabled={!name} className="px-5 py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            Save report
          </button>
        </div>

        {/* Last run result */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">Last run result</h3>
          {!lastRun && <p className="text-sm text-gray-400">Run a saved report to see analytics here.</p>}
          {lastRun && (
            <div className="space-y-3 text-sm">
              {lastRun.retention && (
                <div className="bg-gray-50 rounded p-3">
                  <p className="font-medium text-gray-700 mb-1">Retention</p>
                  <p className="text-xs">30d retention: <b>{((lastRun.retention.retention_rate_30d ?? 0) * 100).toFixed(1)}%</b> · churn: <b>{((lastRun.retention.churn_rate_30d ?? 0) * 100).toFixed(1)}%</b></p>
                </div>
              )}
              {lastRun.saas_metrics && (
                <div className="bg-gray-50 rounded p-3">
                  <p className="font-medium text-gray-700 mb-1">SaaS Metrics</p>
                  <p className="text-xs">MRR: ${lastRun.saas_metrics.mrr?.mrr} · NRR: {lastRun.saas_metrics.nrr?.nrr}% · LTV: ${lastRun.saas_metrics.ltv?.ltv}</p>
                </div>
              )}
              {lastRun.rfm && (
                <div className="bg-gray-50 rounded p-3">
                  <p className="font-medium text-gray-700 mb-1">RFM</p>
                  <p className="text-xs">{Object.entries(lastRun.rfm.segments ?? {}).map(([k, v]) => `${k}: ${v}`).join(" · ")}</p>
                </div>
              )}
              {lastRun.nps && <p className="text-xs">NPS: {lastRun.nps.nps ?? "no responses"}</p>}
              {lastRun.error && <p className="text-red-500 text-xs">{lastRun.error}</p>}
            </div>
          )}
        </div>
      </div>

      {/* Saved reports */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 text-sm mb-3">Saved reports ({saved.length})</h3>
        {saved.length === 0 && <p className="text-sm text-gray-400">No saved reports yet. Build one above.</p>}
        <div className="space-y-2">
          {saved.map((r: any) => (
            <div key={r.report_id} className="flex items-center justify-between p-3 bg-gray-50 rounded border border-gray-100">
              <div>
                <p className="font-medium text-sm text-gray-900">{r.name}</p>
                <p className="text-xs text-gray-400">
                  {r.format} · filters: {r.filters?.time_range}{r.filters?.campaign ? ` · ${r.filters.campaign}` : ""}{r.filters?.segment ? ` · ${r.filters.segment}` : ""} · widgets: {r.widgets?.join(", ")}
                  {r.schedule && ` · 📅 ${r.schedule.frequency}`}
                  {r.last_run_at && ` · last run ${r.last_run_at.slice(0, 10)}`}
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => runReport(r.report_id)} disabled={running === r.report_id} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700 disabled:opacity-50">
                  {running === r.report_id ? "Running…" : "Run"}
                </button>
                <button onClick={() => deleteReport(r.report_id)} className="px-3 py-1.5 border border-red-200 text-red-600 rounded text-xs hover:bg-red-50">Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Data export */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 text-sm mb-3">Export any dataset</h3>
        <div className="flex gap-2 flex-wrap">
          <select value={exportDs} onChange={(e) => setExportDs(e.target.value)} className="border border-gray-300 rounded px-3 py-2 text-sm">
            {datasets.map((d) => <option key={d}>{d}</option>)}
          </select>
          <select value={exportFmt} onChange={(e) => setExportFmt(e.target.value)} className="border border-gray-300 rounded px-3 py-2 text-sm">
            <option value="csv">CSV</option><option value="json">JSON</option>
          </select>
          <button onClick={doExport} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Export</button>
          <button onClick={exportCampaigns} className="px-4 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Export campaigns CSV</button>
        </div>
        {exportInfo && <p className="text-xs text-green-700 mt-2">{exportInfo}</p>}
        {importHistory.length > 0 && (
          <div className="mt-3">
            <p className="text-xs text-gray-400 mb-1">Recent imports:</p>
            {importHistory.map((h) => <p key={h.import_id} className="text-xs font-mono">{h.dataset}: +{h.created} ~{h.updated} · {h.imported_at?.slice(0, 10)}</p>)}
          </div>
        )}
      </div>
    </div>
  );
}
