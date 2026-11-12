"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiGet, apiPost } from "@/lib/api";

interface Article { id: string; title: string; tooltip: string; body?: string; related?: { id: string; title: string; tooltip: string }[]; }

export default function HelpPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Article[]>([]);
  const [open, setOpen] = useState<Article | null>(null);
  const [demoRunning, setDemoRunning] = useState(false);
  const [demoResult, setDemoResult] = useState<any>(null);

  useEffect(() => {
    apiGet("/help").then((d: any) => setArticles(d.articles ?? [])).catch(() => {});
  }, []);

  const search = async () => {
    if (!q) { setResults([]); return; }
    const r: any = await apiGet(`/help/search?q=${encodeURIComponent(q)}`);
    setResults(r.results ?? []);
  };

  const openArticle = async (id: string) => {
    const r: any = await apiGet(`/help/${id}`);
    setOpen(r.article);
  };

  const runDemo = async () => {
    setDemoRunning(true);
    setDemoResult(null);
    try {
      const r: any = await apiPost("/demo/run");
      setDemoResult(r);
    } catch (e: any) {
      setDemoResult({ error: e.message });
    } finally {
      setDemoRunning(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Help & Demo</h1>
        <p className="text-gray-500">Learn each feature in one minute, or run the full demo end-to-end.</p>
      </div>

      {/* Demo */}
      <section className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl p-6 text-white">
        <h2 className="text-xl font-bold mb-1">Interactive demo</h2>
        <p className="text-indigo-100 text-sm mb-4">
          Seeds 6 auto-service customers, scans for due/overdue oil changes, creates and runs a campaign,
          schedules reminders, saves a report. One click, full loop.
        </p>
        <button onClick={runDemo} disabled={demoRunning}
          className="px-6 py-3 bg-white text-indigo-700 rounded-lg font-semibold hover:bg-indigo-50 disabled:opacity-50">
          {demoRunning ? "Running demo…" : "▶ Run the demo"}
        </button>
        {demoResult && !demoResult.error && (
          <div className="mt-4 bg-white/10 rounded-lg p-4 text-sm space-y-1">
            <p className="font-semibold">Demo summary</p>
            <p>Customers seeded: <b>{demoResult.summary.customers_seeded}</b> · due soon: <b>{demoResult.summary.due_soon}</b> · overdue: <b>{demoResult.summary.overdue}</b></p>
            <p>Campaign <code className="bg-white/20 px-1 rounded">{demoResult.summary.campaign_id}</code> ran on <b>{demoResult.summary.campaign_segment_size}</b> members</p>
            <p>Reminders scheduled: <b>{demoResult.summary.reminders_scheduled}</b> · report saved</p>
            <div className="flex gap-2 mt-2">
              <Link href="/campaigns" className="text-xs bg-white/20 px-2 py-1 rounded hover:bg-white/30">See the campaign →</Link>
              <Link href="/customers" className="text-xs bg-white/20 px-2 py-1 rounded hover:bg-white/30">See the customers →</Link>
              <Link href="/reports" className="text-xs bg-white/20 px-2 py-1 rounded hover:bg-white/30">See the report →</Link>
            </div>
          </div>
        )}
        {demoResult?.error && <p className="mt-3 text-red-200 text-sm">{demoResult.error}</p>}
      </section>

      {/* Search */}
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder="Search help… (e.g. 'churn', 'campaign', 'service due')"
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 text-sm" />
        <button onClick={search} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700">Search</button>
      </div>

      {results.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 space-y-2">
          <p className="text-xs text-gray-400">{results.length} results for "{q}"</p>
          {results.map((r) => (
            <button key={r.id} onClick={() => openArticle(r.id)} className="block w-full text-left p-2 rounded hover:bg-gray-50">
              <p className="font-medium text-sm">{r.title}</p>
              <p className="text-xs text-gray-500">{r.tooltip}</p>
            </button>
          ))}
        </div>
      )}

      {/* Article grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {articles.map((a) => (
          <button key={a.id} onClick={() => openArticle(a.id)}
            className="text-left bg-white rounded-lg border border-gray-200 shadow-sm p-4 hover:border-indigo-300 transition">
            <h3 className="font-semibold text-gray-900 text-sm">{a.title}</h3>
            <p className="text-xs text-gray-500 mt-1">{a.tooltip}</p>
          </button>
        ))}
      </div>

      {/* Open article */}
      {open && (
        <div className="bg-white rounded-lg border border-indigo-200 shadow-sm p-6">
          <div className="flex items-start justify-between">
            <h2 className="text-lg font-bold text-gray-900">{open.title}</h2>
            <button onClick={() => setOpen(null)} className="text-gray-400 hover:text-gray-600">✕</button>
          </div>
          <p className="text-sm text-indigo-600 mt-1">{open.tooltip}</p>
          <p className="text-sm text-gray-700 mt-3">{open.body}</p>
          {open.related && open.related.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              <span className="text-xs text-gray-400">Related:</span>
              {open.related.map((r) => (
                <button key={r.id} onClick={() => openArticle(r.id)} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-1 rounded hover:bg-indigo-100">
                  {r.title}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
