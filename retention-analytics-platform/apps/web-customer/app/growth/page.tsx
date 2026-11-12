"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

export default function GrowthPage() {
  const [churnResult, setChurnResult] = useState<any>(null);
  const [offerResult, setOfferResult] = useState<any>(null);
  const [feedbackResult, setFeedbackResult] = useState<any>(null);
  const [saasResult, setSaasResult] = useState<any>(null);
  const [alerts, setAlerts] = useState<any>(null);
  const [cmdCenter, setCmdCenter] = useState<any>(null);
  const [benchmarks, setBenchmarks] = useState<any>(null);
  const [benchCompare, setBenchCompare] = useState<any>(null);
  const [goals, setGoals] = useState<any[]>([]);
  const [anomaly, setAnomaly] = useState<any>(null);
  const [attribution, setAttribution] = useState<any>(null);
  const [voc, setVoc] = useState<any[]>([]);
  const [nps, setNps] = useState<any>(null);
  const [newGoal, setNewGoal] = useState("");
  const [vocTitle, setVocTitle] = useState("");

  const predictChurn = async () => {
    const r = await apiPost("/ai/churn/predict?client_id=demo&usage_drop_pct=70&open_tickets=3&payment_failures=1&logins_last_30d=2&nps_score=4");
    setChurnResult(r.prediction);
  };

  const recommendOffer = async () => {
    const r = await apiPost("/ai/offers/recommend?churn_reason=pricing&churn_probability=0.75&mrr=800");
    setOfferResult(r.recommendation);
  };

  const classifyFeedback = async () => {
    const r = await apiPost("/ai/feedback/classify?text=Love the product but pricing is too high for our team&mrr=600");
    setFeedbackResult(r.classification);
  };

  const computeSaas = async () => {
    const r = await apiPost("/metrics/saas", {
      subscriptions: [{ status: "active", amount: 100, is_new: true }, { status: "active", amount: 300, expansion: 50 }],
      starting_mrr: 5000, churned_mrr: 200, expansion_mrr: 300, contraction_mrr: 50,
      arpu: 62.5, monthly_churn_rate: 0.04, sales_marketing_spend: 10000, new_customers: 40,
      active_customers: 80, cac: 250, starting_customers: 80, churned_customers: 3, new_mrr: 100,
    });
    setSaasResult(r.metrics);
  };

  const loadOps = async () => {
    const [a, c] = await Promise.all([apiGet("/cs/alerts/open"), apiGet("/cs/command-center")]);
    setAlerts(a);
    setCmdCenter(c.overview);
  };

  const loadGrowth = async () => {
    apiGet("/benchmarks").then(setBenchmarks).catch(() => {});
    apiGet("/goals").then((d: any) => setGoals(d.goals ?? [])).catch(() => {});
    apiGet("/attribution/campaigns").then(setAttribution).catch(() => {});
    apiGet("/feedback/board").then((d: any) => setVoc(d.items ?? [])).catch(() => {});
    apiGet("/surveys/nps-score").then(setNps).catch(() => {});
    apiPost("/benchmarks/compare", { industry: "saas", metrics: { churn_rate: 0.03, ltv_cac_ratio: 3.2, nps: 35 } })
      .then(setBenchCompare).catch(() => {});
    apiPost("/anomalies/detect", { series: [100, 102, 98, 101, 100, 99, 101, 160], metric: "churn_rate" })
      .then(setAnomaly).catch(() => {});
  };

  useEffect(() => { loadGrowth(); }, []);

  const createGoal = async () => {
    await apiPost("/goals", { name: newGoal, metric: "mrr", target: 100000, current: 10000 });
    setNewGoal("");
    apiGet("/goals").then((d: any) => setGoals(d.goals ?? []));
  };

  const submitVoc = async () => {
    await apiPost("/feedback/board", { title: vocTitle, body: "" });
    setVocTitle("");
    apiGet("/feedback/board").then((d: any) => setVoc(d.items ?? []));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Growth & AI</h1>
        <p className="text-gray-500 text-sm mt-1">
          Predictive churn scoring, feedback AI, offer recommendations, SaaS metrics, and CS command center.
          Competitor parity: Churnkey, ChurnZero, Vitally, Baremetrics.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Churn prediction */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Predictive Churn Score</h3>
          <p className="text-xs text-gray-400 mb-3">Feature-weighted ML scoring (usage, support, payments, NPS)</p>
          <button onClick={predictChurn} className="px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Predict for demo client</button>
          {churnResult && (
            <div className="mt-3 text-sm">
              <p>Risk: <span className={`font-bold ${churnResult.risk_level === "critical" ? "text-red-600" : "text-amber-600"}`}>{churnResult.risk_level}</span></p>
              <p>Probability: <span className="font-bold">{(churnResult.churn_probability * 100).toFixed(1)}%</span></p>
              <div className="h-2 bg-gray-100 rounded mt-1"><div className="h-2 bg-red-500 rounded" style={{ width: `${churnResult.churn_probability * 100}%` }} /></div>
            </div>
          )}
        </div>

        {/* Offer recommendation */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">AI Offer Recommendation</h3>
          <p className="text-xs text-gray-400 mb-3">Best retention offer per churn reason (Churnkey Adaptive Offers)</p>
          <button onClick={recommendOffer} className="px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Recommend offer</button>
          {offerResult && (
            <div className="mt-3 text-sm">
              <p>Offer: <span className="font-bold text-indigo-600">{offerResult.offer_type}</span> — {offerResult.discount_pct}% off</p>
              <p className="text-gray-500 text-xs">{offerResult.description}</p>
              <p className="text-gray-500 text-xs">Save probability: {(offerResult.expected_save_probability * 100).toFixed(0)}%</p>
            </div>
          )}
        </div>

        {/* Feedback AI */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Feedback AI</h3>
          <p className="text-xs text-gray-400 mb-3">Auto-categorize freeform feedback by theme + MRR impact (Churnkey Feedback AI)</p>
          <button onClick={classifyFeedback} className="px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Classify sample</button>
          {feedbackResult && (
            <p className="mt-3 text-sm">Category: <span className="font-bold">{feedbackResult.category}</span> (confidence {feedbackResult.confidence})</p>
          )}
        </div>

        {/* SaaS metrics */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">SaaS Metrics Suite</h3>
          <p className="text-xs text-gray-400 mb-3">MRR · ARR · GRR · NRR · LTV · CAC · ARPU · Payback · Logo retention (Baremetrics)</p>
          <button onClick={computeSaas} className="px-3 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Compute all</button>
          {saasResult && (
            <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
              <div><p className="text-gray-400">MRR</p><p className="font-bold">${saasResult.mrr.mrr}</p></div>
              <div><p className="text-gray-400">ARR</p><p className="font-bold">${saasResult.arr.arr}</p></div>
              <div><p className="text-gray-400">GRR</p><p className="font-bold">{saasResult.grr.grr}%</p></div>
              <div><p className="text-gray-400">NRR</p><p className="font-bold">{saasResult.nrr.nrr}%</p></div>
              <div><p className="text-gray-400">LTV</p><p className="font-bold">${saasResult.ltv.ltv}</p></div>
              <div><p className="text-gray-400">CAC</p><p className="font-bold">${saasResult.cac.cac}</p></div>
            </div>
          )}
        </div>
      </div>

      {/* Benchmarks, goals, anomaly, attribution, VoC, NPS */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Benchmarks vs industry</h3>
          {benchCompare && benchCompare.comparison?.map((r: any) => (
            <p key={r.metric} className="text-xs py-0.5">{r.metric}: you <b>{r.your_value}</b> vs benchmark {r.benchmark} → <span className={r.verdict === "better" ? "text-green-600" : "text-red-500"}>{r.verdict} ({r.difference_pct}%)</span></p>
          ))}
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Goals ({goals.length})</h3>
          <div className="flex gap-2 mb-2">
            <input value={newGoal} onChange={(e) => setNewGoal(e.target.value)} placeholder="New goal (e.g. Reach 100k MRR)" className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm" />
            <button onClick={createGoal} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm">Add</button>
          </div>
          {goals.map((g) => (
            <div key={g.goal_id} className="mb-2">
              <p className="text-xs">{g.name}: {g.current}/{g.target} ({g.progress_pct}%)</p>
              <div className="h-1.5 bg-gray-100 rounded"><div className="h-1.5 bg-indigo-500 rounded" style={{ width: `${g.progress_pct}%` }} /></div>
            </div>
          ))}
          {anomaly && anomaly.count > 0 && <p className="text-xs text-amber-600 mt-2">⚠ anomaly detected: {anomaly.anomalies[0].direction} {anomaly.anomalies[0].deviation_pct}%</p>}
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Attribution — value saved per campaign</h3>
          {(attribution?.campaigns ?? []).map((c: any) => (
            <p key={c.campaign_id} className="text-xs py-0.5"><code className="font-mono">{c.campaign_id.slice(0, 16)}</code> — saved <b>${c.value_saved}</b> · save rate {c.save_rate}%</p>
          ))}
          {(attribution?.campaigns ?? []).length === 0 && <p className="text-xs text-gray-400">Run a campaign with outcomes to see attribution.</p>}
          {nps && <p className="text-xs mt-2">NPS: <b>{nps.nps ?? "no responses"}</b> ({nps.responses} responses)</p>}
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Voice of customer ({voc.length})</h3>
          <div className="flex gap-2 mb-2">
            <input value={vocTitle} onChange={(e) => setVocTitle(e.target.value)} placeholder="Feature request…" className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm" />
            <button onClick={submitVoc} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm">Submit</button>
          </div>
          {voc.slice(0, 5).map((i) => (
            <div key={i.id} className="flex justify-between text-xs py-1 border-b last:border-0">
              <span>{i.title}</span><span className="text-gray-400">👍 {i.votes} · {i.status}</span>
            </div>
          ))}
        </div>
      </div>

      {/* CS Command center */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900 text-sm">Command Center (ChurnZero parity)</h3>
          <button onClick={loadOps} className="px-3 py-1.5 border border-gray-300 rounded text-xs hover:bg-gray-50">Refresh</button>
        </div>
        {cmdCenter && (
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="bg-red-50 rounded p-3"><p className="text-xl font-bold text-red-600">{cmdCenter.open_alerts}</p><p className="text-xs text-gray-500">Open alerts</p></div>
            <div className="bg-amber-50 rounded p-3"><p className="text-xl font-bold text-amber-600">{cmdCenter.at_risk_clients}</p><p className="text-xs text-gray-500">At-risk clients</p></div>
            <div className="bg-green-50 rounded p-3"><p className="text-xl font-bold text-green-600">${cmdCenter.renewal_forecast_arr ?? 0}</p><p className="text-xs text-gray-500">Renewal forecast ARR</p></div>
          </div>
        )}
      </div>
    </div>
  );
}
