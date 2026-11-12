"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

interface Workflow {
  id: string;
  name: string;
  trigger_event: string;
  steps: { id: string; service: string; action: string }[];
  active: boolean;
}

const FLOW_EXPLAIN: Record<string, { what: string; when: string; who: string; result: string }> = {
  "churn-prevention": { what: "Sends a win-back email when a customer is at risk.", when: "Event: client.churn_risk", who: "All at-risk customers", result: "Email sent + retention metric updated" },
  "cart-abandonment": { what: "Recovers abandoned carts with a reminder email.", when: "Event: order.abandoned_cart", who: "Anyone with an open cart", result: "Cart marked + recovery email queued" },
  "welcome": { what: "Sends a welcome email to new customers.", when: "Event: client.created", who: "All new sign-ups", result: "Welcome email queued" },
  "win-back": { what: "Offers a deal to cancelled subscribers + recomputes retention.", when: "Event: subscription.cancelled", who: "Recently cancelled", result: "Offer email + updated metrics" },
  "dunning-campaign": { what: "Runs a payment-recovery campaign: retries + email/SMS when a payment fails.", when: "Event: payment.failed", who: "Customers with failed payments", result: "Dunning campaign started, retries scheduled" },
  "cancel-flow": { what: "On cancel: exit survey + pause offer + personalized save offer.", when: "Event: cancel.flow_started", who: "Anyone starting to cancel", result: "Survey sent + save offer delivered" },
  "subscription-pause": { what: "Pauses a subscription and confirms by email.", when: "Event: subscription.paused", who: "Customers requesting pause", result: "Subscription paused + confirmation sent" },
  "annual-upsell": { what: "Offers monthly subscribers an annual plan discount.", when: "Event: upsell.annual_eligible", who: "Eligible monthly subscribers", result: "Upsell email sent" },
  "expansion-opportunity": { what: "Detects seat overage and emails an expansion offer.", when: "Event: account.seat_overage", who: "Accounts over seat limit", result: "Health computed + expansion email" },
  "reactivation": { what: "Welcomes back returning customers with what's-new.", when: "Event: client.reactivated", who: "Returning customers", result: "Welcome-back email + return deal" },
  "nps-survey": { what: "Sends an NPS survey and computes the score.", when: "Event: survey.nps_due", who: "Customers due for NPS", result: "Survey sent + NPS computed" },
  "health-score-alert": { what: "When health drops: computes score, alerts team, emails customer.", when: "Event: health.score_low", who: "Low-health accounts", result: "Alert fired + check-in email" },
  "feature-adoption": { what: "Nudges users who haven't used a key feature: email + in-app walkthrough.", when: "Event: feature.unused", who: "Users missing a feature", result: "Tutorial email + walkthrough started" },
  "renewal-reminder": { what: "Reminds about upcoming renewal + upsell.", when: "Event: subscription.renewal_due", who: "Renewing subscriptions", result: "Reminder + upsell rendered" },
  "trial-conversion": { what: "Converts trials: email offer + in-app banner as trial ends.", when: "Event: trial.ending", who: "Trials ending soon", result: "Convert email + banner shown" },
  "downgrade-save": { what: "Saves downgrades with a retention discount.", when: "Event: subscription.downgraded", who: "Downgrading customers", result: "Save email + discount offer" },
  "referral-ask": { what: "Asks happy customers for referrals.", when: "Event: referral.eligible", who: "Eligible advocates", result: "Referral email sent" },
  "onboarding-milestone": { what: "Day-N check-in email + health check during onboarding.", when: "Event: onboarding.milestone", who: "Onboarding customers", result: "Check-in email + health score" },
  "usage-drop-alert": { what: "Detects usage drops: alerts team + win-back email.", when: "Event: usage.dropped", who: "Accounts with dropping usage", result: "Alert + win-back email" },
};

export default function Flows() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [config, setConfig] = useState<Record<string, any>>({});
  const [selected, setSelected] = useState<Workflow | null>(null);
  const [segments, setSegments] = useState<any[]>([]);
  const [targetSegment, setTargetSegment] = useState("");
  const [runResult, setRunResult] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [ctxEmail, setCtxEmail] = useState("customer@example.com");

  const load = () => {
    apiGet("/workflows").then((d: any) => {
      const wfs = d.workflows ?? [];
      setWorkflows(wfs);
      if (wfs[0] && !selected) setSelected(wfs[0]);
    }).catch(() => {});
    apiGet("/workflows/config").then((d: any) => setConfig(d.config ?? {})).catch(() => {});
    apiGet("/segments").then((d: any) => setSegments(d.segments ?? [])).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const toggleActive = async (wf: Workflow) => {
    const isActive = config[wf.id]?.active ?? wf.active;
    await apiPost(`/workflows/${wf.id}/toggle?active=${!isActive}`);
    load();
  };

  const saveTarget = async () => {
    if (!selected || !targetSegment) return;
    const seg = segments.find((s: any) => s.segment_id === targetSegment);
    await apiPost(`/workflows/${selected.id}/target?segment_id=${targetSegment}&segment_name=${encodeURIComponent(seg?.name ?? "All customers")}`);
    load();
  };

  const run = async () => {
    if (!selected) return;
    setRunning(true);
    setRunResult(null);
    try {
      const r = await apiPost(`/workflows/${selected.id}/run`, { context: { email: ctxEmail, cart_id: "cart-001" } });
      setRunResult(r);
    } catch (e: any) {
      setRunResult({ error: e.message });
    } finally {
      setRunning(false);
    }
  };

  const explain = selected ? FLOW_EXPLAIN[selected.id] : null;
  const wfConfig = selected ? config[selected.id] : null;
  const isActive = wfConfig?.active ?? selected?.active ?? true;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Flows</h1>
        <p className="text-gray-500 text-sm mt-1">
          Flows are automated playbooks: an event triggers them, they run steps (send email, score health, alert team), and persist results.
          Pick a flow to see what it does, who it targets, toggle it on/off, and run it.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Flow list */}
        <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
          {workflows.map((w) => {
            const cfg = config[w.id];
            const active = cfg?.active ?? w.active;
            return (
              <button
                key={w.id}
                onClick={() => { setSelected(w); setRunResult(null); }}
                className={`w-full text-left p-3 rounded-lg border transition ${selected?.id === w.id ? "border-indigo-500 bg-indigo-50" : "border-gray-200 bg-white hover:border-gray-300"}`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm text-gray-900">{w.name}</span>
                  <span className={`w-2 h-2 rounded-full ${active ? "bg-green-500" : "bg-gray-300"}`} title={active ? "active" : "paused"} />
                </div>
                <p className="text-xs text-gray-400 font-mono mt-1">⚡ {w.trigger_event}</p>
              </button>
            );
          })}
        </div>

        {/* Flow detail */}
        <div className="lg:col-span-2 space-y-4">
          {selected && explain && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-900">{selected.name}</h2>
                <button
                  onClick={() => toggleActive(selected)}
                  className={`px-3 py-1.5 rounded text-xs font-medium ${isActive ? "bg-amber-100 text-amber-700 hover:bg-amber-200" : "bg-green-100 text-green-700 hover:bg-green-200"}`}
                >
                  {isActive ? "Pause flow" : "Activate flow"}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                <div className="bg-gray-50 rounded p-3"><p className="text-xs text-gray-400 mb-1">WHAT</p><p className="text-gray-700">{explain.what}</p></div>
                <div className="bg-gray-50 rounded p-3"><p className="text-xs text-gray-400 mb-1">WHEN</p><p className="text-gray-700 font-mono text-xs">{explain.when}</p></div>
                <div className="bg-gray-50 rounded p-3"><p className="text-xs text-gray-400 mb-1">WHO (target)</p><p className="text-gray-700">{wfConfig?.target_segment?.name ?? explain.who}</p></div>
                <div className="bg-gray-50 rounded p-3"><p className="text-xs text-gray-400 mb-1">RESULT</p><p className="text-gray-700">{explain.result}</p></div>
              </div>

              {/* Pipeline */}
              <div className="space-y-1 mb-4">
                <p className="text-xs text-gray-400 mb-1">PIPELINE</p>
                <div className="flex flex-wrap items-center gap-1">
                  <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded font-mono text-xs">⚡ {selected.trigger_event}</span>
                  {selected.steps.map((s) => (
                    <span key={s.id} className="flex items-center gap-1">
                      <span className="text-gray-300">→</span>
                      <span className="bg-slate-100 border border-gray-200 px-2 py-1 rounded font-mono text-xs">{s.service}.{s.action}</span>
                    </span>
                  ))}
                </div>
              </div>

              {/* Target selection */}
              <div className="flex gap-2 items-end mb-4">
                <div className="flex-1">
                  <label className="block text-xs text-gray-400 mb-1">Target segment</label>
                  <select value={targetSegment} onChange={(e) => setTargetSegment(e.target.value)} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm">
                    <option value="">All customers</option>
                    {segments.map((s: any) => <option key={s.segment_id} value={s.segment_id}>{s.name}</option>)}
                  </select>
                </div>
                <button onClick={saveTarget} className="px-3 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50">Set target</button>
              </div>

              {/* Run */}
              <div className="flex gap-2 items-end">
                <div className="flex-1">
                  <label className="block text-xs text-gray-400 mb-1">Test with email</label>
                  <input value={ctxEmail} onChange={(e) => setCtxEmail(e.target.value)} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" />
                </div>
                <button onClick={run} disabled={running} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
                  {running ? "Running…" : "Run now"}
                </button>
              </div>

              {runResult && (
                <div className={`mt-3 rounded border p-3 ${runResult.error ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200"}`}>
                  <p className="text-xs font-medium mb-1">Status: {runResult.status ?? runResult.error}</p>
                  <pre className="text-xs bg-white p-2 rounded overflow-x-auto max-h-48">{JSON.stringify(runResult.step_outputs ?? runResult, null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
