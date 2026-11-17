"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [answer, setAnswer] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [role, setRole] = useState("leadership");
  const [view, setView] = useState<any>(null);
  const [roles, setRoles] = useState<string[]>([]);

  useEffect(() => {
    apiGet("/agency/questions").then((d: any) => setSuggestions(d.questions ?? [])).catch(() => {});
    apiGet("/agency/roles").then((d: any) => setRoles(d.roles ?? [])).catch(() => {});
  }, []);

  const ask = async (q?: string) => {
    const text = q ?? question;
    if (!text.trim()) return;
    setQuestion(text);
    setLoading(true);
    setAnswer(null);
    try {
      const r: any = await apiPost("/agency/ask", { question: text, agency_id: "default" });
      setAnswer(r);
    } catch (e: any) {
      setAnswer({ answer: "Error: " + e.message, intent: "error" });
    } finally {
      setLoading(false);
    }
  };

  const loadView = async (r?: string) => {
    const chosen = r ?? role;
    setRole(chosen);
    try {
      const v: any = await apiGet(`/agency/view?role=${chosen}`);
      setView(v);
    } catch {}
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Ask</h1>
        <p className="text-gray-500 text-sm mt-1">
          Plain-English questions answered from live roster data — the same thing Hiro calls "Ask Hiro".
        </p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="Which clients are behind their revenue goal this month?"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-3 text-sm"
          />
          <button onClick={() => ask()} disabled={loading}
            className="px-5 py-3 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            {loading ? "Thinking…" : "Ask"}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {suggestions.map((s) => (
            <button key={s} onClick={() => ask(s)}
              className="text-xs bg-gray-100 hover:bg-indigo-50 border border-gray-200 hover:border-indigo-300 px-2 py-1 rounded">
              {s}
            </button>
          ))}
        </div>
      </div>

      {answer && (
        <div className="bg-white rounded-lg border border-indigo-200 shadow-sm p-5">
          <p className="text-xs font-semibold text-indigo-600 uppercase mb-1">Answer · intent: {answer.intent}</p>
          <p className="text-gray-800">{answer.answer}</p>
          {answer.data?.behind_goal && (
            <table className="w-full text-left text-sm mt-3">
              <thead><tr className="border-b text-xs text-gray-400"><th className="py-2">Client</th><th className="py-2">To date</th><th className="py-2">Goal</th><th className="py-2">Pacing</th></tr></thead>
              <tbody>
                {answer.data.behind_goal.map((c: any, i: number) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-2 font-medium">{c.client}</td>
                    <td className="py-2">${(c.to_date ?? 0).toLocaleString()}</td>
                    <td className="py-2">${(c.goal ?? 0).toLocaleString()}</td>
                    <td className="py-2">{c.pacing_pct ?? "-"}% of goal</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Role views */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-900 text-sm">View as</h2>
          <div className="flex gap-1">
            {roles.map((r) => (
              <button key={r} onClick={() => loadView(r)}
                className={`px-3 py-1.5 text-xs rounded ${role === r ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600"}`}>
                {r.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>
        {!view && <p className="text-sm text-gray-400">Pick a role to load its view.</p>}
        {view?.role === "leadership" && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Metric label="Revenue MTD" value={`$${view.headline.revenue_mtd.toLocaleString()}`} />
            <Metric label="Behind goal" value={view.headline.behind_goal} warn />
            <Metric label="Need attention" value={view.headline.needs_attention} warn />
            <Metric label="Churn risk" value={view.headline.churn_risk} warn />
            <Metric label="MRR at risk" value={`$${Math.round(view.headline.mrr_at_risk).toLocaleString()}`} warn />
          </div>
        )}
        {view?.role === "account_manager" && view.client && (
          <div className="space-y-2">
            <p className="font-medium">{view.client.name} — {view.client.status_label}</p>
            <p className="text-sm text-gray-600">Revenue MTD ${(view.client.revenue_mtd ?? 0).toLocaleString()} · pacing {view.client.pacing_pct}% · churn risk {view.client.churn_risk} · alerts {view.client.open_alerts}</p>
          </div>
        )}
        {view?.role === "copywriter" && (
          <div className="space-y-2 text-sm">
            <p>Best slot: <b>{view.headline.best_slot ? `${view.headline.best_slot.day} ${view.headline.best_slot.hour}:00` : "—"}</b></p>
            <p>Best subject: <b>{view.headline.best_subject ?? "—"}</b></p>
            {view.subjects?.slice(0, 5).map((s: any, i: number) => (
              <p key={i} className="text-gray-600">{s.subject} — {s.open_rate}% open</p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value, warn }: { label: string; value: any; warn?: boolean }) {
  return (
    <div className="bg-gray-50 rounded p-3 text-center">
      <p className={`text-lg font-bold ${warn ? "text-amber-600" : "text-gray-900"}`}>{value}</p>
      <p className="text-[10px] text-gray-400">{label}</p>
    </div>
  );
}
