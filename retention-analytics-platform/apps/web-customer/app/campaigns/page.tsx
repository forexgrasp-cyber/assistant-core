"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost, authHeaders } from "@/lib/api";
import { useToast } from "@/components/ToastProvider";

interface Goal { label: string; default_flows: string[]; default_metrics: string[]; }
interface Campaign {
  campaign_id: string; name: string; description: string; goal: string; goal_label: string;
  segment: { id: string; name: string; criteria: any }; flows: string[]; schedule: any;
  success_metrics: string[]; status: string; created_at: string; results: any; runs: any[];
}
interface Workflow { id: string; name: string; trigger_event: string; steps: any[]; active: boolean; }

const SCHEDULE_TYPES = [
  { id: "once", label: "Run once now" },
  { id: "on_event", label: "On event (real-time)" },
  { id: "daily", label: "Daily" },
  { id: "weekly", label: "Weekly" },
];

export default function Campaigns() {
  const { toast } = useToast();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [goals, setGoals] = useState<Record<string, Goal>>({});
  const [segments, setSegments] = useState<any[]>([]);
  const [selected, setSelected] = useState<Campaign | null>(null);
  const [results, setResults] = useState<any>(null);

  // Builder state
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [goal, setGoal] = useState("reduce_churn");
  const [segmentId, setSegmentId] = useState("all");
  const [customCriteria, setCustomCriteria] = useState("");
  const [selectedFlows, setSelectedFlows] = useState<string[]>([]);
  const [schedule, setSchedule] = useState("once");
  const [metrics, setMetrics] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [runningId, setRunningId] = useState<string | null>(null);

  const load = () => {
    apiGet("/campaigns").then((d: any) => setCampaigns(d.campaigns ?? [])).catch(() => {});
    apiGet("/workflows").then((d: any) => setWorkflows(d.workflows ?? [])).catch(() => {});
    apiGet("/campaigns/goals").then((d: any) => setGoals(d.goals ?? {})).catch(() => {});
    apiGet("/segments").then((d: any) => setSegments(d.segments ?? [])).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const g = goals[goal];
    if (g) {
      setSelectedFlows(g.default_flows);
      setMetrics(g.default_metrics);
    }
  }, [goal, goals]);

  const create = async () => {
    setCreating(true);
    try {
      const seg = segmentId === "all"
        ? { id: "all", name: "All customers", criteria: {} }
        : segments.find((s: any) => s.segment_id === segmentId) ?? { id: segmentId, name: segmentId, criteria: {} };
      let criteria = seg.criteria ?? {};
      if (customCriteria) { try { criteria = JSON.parse(customCriteria); } catch {} }
      const r: any = await apiPost("/campaigns", {
        name, description, goal,
        segment: { ...seg, criteria },
        flows: selectedFlows, schedule: { type: schedule }, success_metrics: metrics,
      });
      setStep(1); setName(""); setDescription("");
      load();
      setSelected(r.campaign);
    } catch (e: any) {
      toast(String(e.message), "error");
    } finally {
      setCreating(false);
    }
  };
  const activate = async (id: string) => {
    await apiPost(`/campaigns/${id}/activate`);
    load();
  };

  const run = async (id: string) => {
    setRunningId(id);
    setResults(null);
    try {
      const r: any = await apiPost(`/campaigns/${id}/run`, { clients: [
        { id: "c1", client_email: "alice@acme.com", plan: "growth", health_score: 35, mrr: 500 },
        { id: "c2", client_email: "bob@acme.com", plan: "starter", health_score: 70, mrr: 100 },
      ]});
      setResults(r.results);
      load();
    } catch (e: any) {
      setResults({ error: e.message });
    } finally {
      setRunningId(null);
    }
  };

  const del = async (id: string) => {
    await fetch(`/api/v1/campaigns/${id}`, { method: "DELETE", headers: authHeaders() });
    if (selected?.campaign_id === id) setSelected(null);
    load();
  };

  const toggleFlow = (fid: string) => {
    setSelectedFlows((prev) => prev.includes(fid) ? prev.filter((f) => f !== fid) : [...prev, fid]);
  };

  const goalInfo = goals[goal];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
        <p className="text-gray-500 text-sm mt-1 max-w-2xl">
          A campaign ties everything together: <b>pick a goal → choose WHO (segment) → choose the flows → schedule → measure</b>.
          When you run it, the segment is evaluated, each flow executes per member, and before/after metrics show the impact.
        </p>
      </div>

      {/* The model diagram */}
      <div className="bg-slate-900 text-white rounded-lg p-4 flex flex-wrap items-center gap-2 text-xs font-mono">
        <span className="bg-blue-500/20 border border-blue-400/40 px-2 py-1 rounded">SEGMENT (who)</span>
        <span className="text-slate-400">→</span>
        <span className="bg-indigo-500/20 border border-indigo-400/40 px-2 py-1 rounded">CAMPAIGN (goal+flows+schedule)</span>
        <span className="text-slate-400">→</span>
        <span className="bg-emerald-500/20 border border-emerald-400/40 px-2 py-1 rounded">FLOWS run per member</span>
        <span className="text-slate-400">→</span>
        <span className="bg-amber-500/20 border border-amber-400/40 px-2 py-1 rounded">SERVICES act</span>
        <span className="text-slate-400">→</span>
        <span className="bg-pink-500/20 border border-pink-400/40 px-2 py-1 rounded">RESULTS measured</span>
        <span className="text-slate-400">→</span>
        <span className="bg-purple-500/20 border border-purple-400/40 px-2 py-1 rounded">REPORTS</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: campaign list */}
        <div className="space-y-2">
          <h3 className="font-semibold text-gray-900 text-sm">Your campaigns ({campaigns.length})</h3>
          {campaigns.length === 0 && <p className="text-sm text-gray-400">None yet — build one below.</p>}
          {campaigns.map((c) => (
            <button key={c.campaign_id} onClick={() => { setSelected(c); setResults(c.results); }}
              className={`w-full text-left p-3 rounded-lg border transition ${selected?.campaign_id === c.campaign_id ? "border-indigo-500 bg-indigo-50" : "border-gray-200 bg-white hover:border-gray-300"}`}>
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm">{c.name}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${c.status === "active" ? "bg-green-100 text-green-700" : c.status === "completed" ? "bg-blue-100 text-blue-700" : c.status === "paused" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-500"}`}>{c.status}</span>
              </div>
              <p className="text-xs text-gray-400 mt-1">{c.goal_label} · {c.flows.length} flows · target: {c.segment?.name}</p>
            </button>
          ))}
        </div>

        {/* Middle: builder */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-gray-900 text-sm">New campaign — step {step}/4</h3>
            <div className="flex gap-1">{[1, 2, 3, 4].map((s) => <span key={s} className={`w-2 h-2 rounded-full ${s <= step ? "bg-indigo-600" : "bg-gray-200"}`} />)}</div>
          </div>

          {step === 1 && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Campaign name</label>
                <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Q4 churn save" className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Description</label>
                <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Goal and context" className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Goal — what should this campaign achieve?</label>
                <div className="grid grid-cols-2 gap-1">
                  {Object.entries(goals).map(([id, g]) => (
                    <button key={id} onClick={() => setGoal(id)} className={`text-left px-2 py-2 rounded text-xs border ${goal === id ? "border-indigo-500 bg-indigo-50 text-indigo-700" : "border-gray-200 text-gray-600"}`}>{g.label}</button>
                  ))}
                </div>
              </div>
              <button onClick={() => setStep(2)} disabled={!name} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50">Next: target →</button>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-3">
              <label className="block text-xs text-gray-500">WHO — target segment</label>
              <select value={segmentId} onChange={(e) => setSegmentId(e.target.value)} className="w-full border border-gray-300 rounded px-3 py-2 text-sm">
                <option value="all">All customers</option>
                {segments.map((s: any) => <option key={s.segment_id} value={s.segment_id}>{s.name}</option>)}
              </select>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Custom criteria (JSON, optional) — e.g. {"{\"health_score\": {\"lt\": 50}}"}</label>
                <textarea value={customCriteria} onChange={(e) => setCustomCriteria(e.target.value)} rows={2} className="w-full border border-gray-300 rounded px-2 py-1.5 text-xs font-mono" placeholder='{"health_score": {"lt": 50}}' />
              </div>
              <div className="flex gap-2">
                <button onClick={() => setStep(1)} className="px-3 py-2 border border-gray-300 rounded text-sm">← Back</button>
                <button onClick={() => setStep(3)} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Next: flows →</button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-3">
              <label className="block text-xs text-gray-500">HOW — pick the flows this campaign runs (suggested for your goal are pre-selected)</label>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {workflows.map((w) => (
                  <label key={w.id} className="flex items-center gap-2 p-2 rounded border border-gray-100 hover:bg-gray-50 cursor-pointer">
                    <input type="checkbox" checked={selectedFlows.includes(w.id)} onChange={() => toggleFlow(w.id)} />
                    <div>
                      <p className="text-sm font-medium">{w.name}</p>
                      <p className="text-xs text-gray-400 font-mono">⚡ {w.trigger_event} · {w.steps.length} steps</p>
                    </div>
                  </label>
                ))}
              </div>
              <div className="flex gap-2">
                <button onClick={() => setStep(2)} className="px-3 py-2 border border-gray-300 rounded text-sm">← Back</button>
                <button onClick={() => setStep(4)} disabled={selectedFlows.length === 0} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50">Next: schedule →</button>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">WHEN — schedule</label>
                <div className="grid grid-cols-2 gap-1">
                  {SCHEDULE_TYPES.map((s) => (
                    <button key={s.id} onClick={() => setSchedule(s.id)} className={`px-2 py-2 rounded text-xs border ${schedule === s.id ? "border-indigo-500 bg-indigo-50 text-indigo-700" : "border-gray-200"}`}>{s.label}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">MEASURE — success metrics (auto from goal, editable)</label>
                <div className="flex flex-wrap gap-1">
                  {metrics.map((m) => <span key={m} className="bg-purple-50 text-purple-700 px-2 py-1 rounded text-xs font-mono">{m}</span>)}
                </div>
              </div>
              <p className="text-xs text-gray-400">Summary: <b>{name}</b> · {goalInfo?.label} · target: {segmentId === "all" ? "All customers" : segmentId} · {selectedFlows.length} flows · {schedule}</p>
              <div className="flex gap-2">
                <button onClick={() => setStep(3)} className="px-3 py-2 border border-gray-300 rounded text-sm">← Back</button>
                <button onClick={create} disabled={creating} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50">{creating ? "Creating…" : "Create campaign"}</button>
              </div>
            </div>
          )}
        </div>

        {/* Right: selected campaign detail + results */}
        <div className="space-y-4">
          {selected && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-gray-900 text-sm">{selected.name}</h3>
                <span className={`text-xs px-2 py-0.5 rounded-full ${selected.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>{selected.status}</span>
              </div>
              <p className="text-xs text-gray-500 mb-3">{selected.description || selected.goal_label}</p>
              <div className="text-xs space-y-1 mb-3">
                <p><b>Goal:</b> {selected.goal_label}</p>
                <p><b>Target:</b> {selected.segment?.name} ({selected.segment?.criteria && Object.keys(selected.segment.criteria).length > 0 ? JSON.stringify(selected.segment.criteria) : "all"})</p>
                <p><b>Flows:</b> {selected.flows.join(", ")}</p>
                <p><b>Schedule:</b> {selected.schedule?.type}</p>
                <p><b>Metrics:</b> {selected.success_metrics.join(", ")}</p>
              </div>
              <div className="flex gap-2">
                {selected.status !== "active" && <button onClick={() => activate(selected.campaign_id)} className="px-3 py-1.5 bg-green-600 text-white rounded text-xs hover:bg-green-700">Activate</button>}
                <button onClick={() => run(selected.campaign_id)} disabled={runningId === selected.campaign_id} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-xs hover:bg-indigo-700 disabled:opacity-50">
                  {runningId === selected.campaign_id ? "Running…" : "Run now"}
                </button>
                <button onClick={() => del(selected.campaign_id)} className="px-3 py-1.5 border border-red-200 text-red-600 rounded text-xs hover:bg-red-50">Delete</button>
              </div>
            </div>
          )}

          {results && !results.error && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-3">Results</h3>
              <div className="grid grid-cols-2 gap-2 text-center mb-3">
                <div className="bg-blue-50 rounded p-2"><p className="text-lg font-bold text-blue-700">{results.segment_size}</p><p className="text-xs text-gray-500">segment members</p></div>
                <div className="bg-green-50 rounded p-2"><p className="text-lg font-bold text-green-700">{results.outcomes_count}</p><p className="text-xs text-gray-500">flow executions</p></div>
              </div>
              {results.deltas && Object.keys(results.deltas).length > 0 && (
                <div className="mb-2">
                  <p className="text-xs text-gray-400 mb-1">Metric deltas (after − before)</p>
                  {Object.entries(results.deltas).map(([k, v]: [string, any]) => (
                    <p key={k} className="text-xs font-mono">{k}: <span className={v >= 0 ? "text-green-600" : "text-red-600"}>{v > 0 ? "+" : ""}{v}</span></p>
                  ))}
                </div>
              )}
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto max-h-40">{JSON.stringify(results.baseline ?? {}, null, 2).slice(0, 500)}</pre>
            </div>
          )}
          {results?.error && <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded text-sm">{results.error}</div>}
        </div>
      </div>
    </div>
  );
}
