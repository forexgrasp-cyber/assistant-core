"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function PerformancePage() {
  const [flowMap, setFlowMap] = useState<any>(null);
  const [dive, setDive] = useState<any>(null);
  const [timing, setTiming] = useState<any>(null);
  const [deliver, setDeliver] = useState<any>(null);
  const [tab, setTab] = useState<"flow" | "campaign" | "timing" | "deliverability">("flow");

  const load = () => {
    apiGet("/performance/flow-map").then(setFlowMap).catch(() => {});
    apiGet("/performance/campaign").then(setDive).catch(() => {});
    apiGet("/performance/message-timing").then(setTiming).catch(() => {});
    apiGet("/performance/deliverability").then(setDeliver).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  // seed a demo sample so the screens are not empty on first view
  const seedSample = async () => {
    await apiPost("/performance/sends", {
      flow_id: "churn-prevention", message_id: "m1", campaign_id: "c1",
      subject: "Your fall edit is here", preview_text: "New season, new favourites",
      channel: "email", send_mode: "static", sent: 12000, delivered: 11700, opened: 5850,
      clicked: 528, revenue: 21480, products: [{"name": "Cable Sweater", "units": 96, "revenue": 8544}],
      first_time_buyers: 76, returning_buyers: 55, variant: "A",
    });
    await apiPost("/performance/deliverability", {
      provider: "Outlook", sent: 4000, delivered: 3940, bounced: 56, spam: 3, unsubscribed: 19,
      source_name: "Last Call · Summer",
    });
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Performance</h1>
          <p className="text-gray-500 text-sm mt-1">
            Flow map, campaign deep dive, send timing and inbox delivery — every number explained.
          </p>
        </div>
        <button onClick={seedSample} className="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Load sample data</button>
      </div>

      <div className="flex gap-1 border-b border-gray-200">
        {(["flow", "campaign", "timing", "deliverability"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === t ? "border-indigo-600 text-indigo-700" : "border-transparent text-gray-500"}`}>
            {t === "flow" ? "Flow map" : t === "campaign" ? "Campaign deep dive" : t === "timing" ? "Message timing" : "Deliverability"}
          </button>
        ))}
      </div>

      {tab === "flow" && (
        <div className="space-y-4">
          {flowMap && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <Mini label="Flows" value={flowMap.flow_count} />
              <Mini label="Messages" value={flowMap.message_count} />
              <Mini label="Sent" value={flowMap.totals.sent} />
              <Mini label="Open rate" value={`${flowMap.totals.open_rate}%`} />
              <Mini label="Revenue" value={`$${flowMap.totals.revenue}`} />
            </div>
          )}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-900 text-sm mb-3">Message performance</h3>
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b text-xs text-gray-400">
                <th className="py-2">Message</th><th className="py-2">Subject</th><th className="py-2">Sent</th>
                <th className="py-2">Open</th><th className="py-2">Click</th><th className="py-2">Revenue</th><th className="py-2">$/recipient</th>
              </tr></thead>
              <tbody>
                {(flowMap?.messages ?? []).map((m: any) => (
                  <tr key={m.message_id} className="border-b last:border-0">
                    <td className="py-2 font-mono text-xs">{m.message_id}</td>
                    <td className="py-2">{m.subject || "-"}<p className="text-xs text-gray-400">{m.preview_text}</p></td>
                    <td className="py-2">{m.sent}</td>
                    <td className="py-2">{m.open_rate}%</td>
                    <td className="py-2">{m.click_rate}%</td>
                    <td className="py-2">${m.revenue}</td>
                    <td className="py-2 text-xs">${m.revenue_per_recipient}</td>
                  </tr>
                ))}
                {(flowMap?.messages ?? []).length === 0 && (
                  <tr><td colSpan={7} className="py-6 text-center text-gray-400 text-sm">No sends recorded yet — load sample data.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "campaign" && dive && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-900 text-sm mb-3">Send by send</h3>
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b text-xs text-gray-400">
                <th className="py-2">Subject</th><th className="py-2">Sent</th><th className="py-2">Open</th>
                <th className="py-2">Click</th><th className="py-2">Revenue</th><th className="py-2">Variant</th>
              </tr></thead>
              <tbody>
                {(dive.sends ?? []).map((s: any) => (
                  <tr key={s.send_id} className="border-b last:border-0">
                    <td className="py-2">{s.subject}<p className="text-xs text-gray-400">{s.preview_text}</p></td>
                    <td className="py-2">{s.sent}</td>
                    <td className="py-2">{s.open_rate}%</td>
                    <td className="py-2">{s.click_rate}%</td>
                    <td className="py-2">${s.revenue}</td>
                    <td className="py-2 text-xs">{s.variant || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="space-y-4">
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-2">Products purchased</h3>
              {(dive.products ?? []).map((p: any) => (
                <div key={p.name} className="flex justify-between text-sm py-1 border-b last:border-0">
                  <span>{p.name}</span><span className="text-gray-500">{p.units} sold · ${p.revenue}</span>
                </div>
              ))}
              {(dive.products ?? []).length === 0 && <p className="text-xs text-gray-400">No product data.</p>}
            </div>
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-2">First-time vs returning</h3>
              <p className="text-sm">First-time: <b>{dive.buyers?.first_time ?? 0}</b> ({dive.buyers?.first_time_share ?? 0}%)</p>
              <p className="text-sm">Returning: <b>{dive.buyers?.returning ?? 0}</b></p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-2">A/B variants</h3>
              {(dive.variants ?? []).map((v: any) => (
                <p key={v.variant} className="text-xs py-1">{v.variant}: {v.open_rate}% open · ${v.revenue}</p>
              ))}
              {(dive.variants ?? []).length === 0 && <p className="text-xs text-gray-400">No variants recorded.</p>}
            </div>
          </div>
        </div>
      )}

      {tab === "timing" && timing && (
        <div className="space-y-4">
          {Object.entries(timing.modes ?? {}).map(([mode, data]: [string, any]) => (
            <div key={mode} className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-gray-900 text-sm capitalize">{mode.replace(/_/g, " ")} sends</h3>
                {data.best_slot && <p className="text-xs text-gray-500">Best: <b>{data.best_slot.day} {data.best_slot.hour}:00</b> · ${data.best_slot.revenue_per_recipient}/recipient · weakest {data.weakest_slot?.day} {data.weakest_slot?.hour}:00</p>}
              </div>
              <div className="overflow-x-auto">
                <table className="text-xs">
                  <thead><tr><th className="p-1"></th>{[6, 9, 12, 15, 18, 21].map((h) => <th key={h} className="p-1 text-gray-400">{h}:00</th>)}</tr></thead>
                  <tbody>
                    {DAYS.map((day) => (
                      <tr key={day}>
                        <td className="p-1 text-gray-500">{day}</td>
                        {[6, 9, 12, 15, 18, 21].map((h) => {
                          const cell = (data.cells ?? []).find((c: any) => c.day === day && c.hour === h);
                          const v = cell?.revenue_per_recipient ?? 0;
                          const alpha = Math.min(0.85, v * 12);
                          const label = `${day} ${h}:00 — $${v} per recipient`;
                          return (
                            <td key={h} className="p-1">
                              <div className="h-7 rounded" style={{ background: `rgba(79,70,229,${alpha})` }} title={label} />
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-gray-400 mt-2">{data.sends_analysed} slots · {data.recipients?.toLocaleString()} recipients analysed</p>
            </div>
          ))}
          {timing.subjects_ranked?.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-2">Subject lines by open rate</h3>
              {timing.subjects_ranked.slice(0, 8).map((s: any) => (
                <div key={s.subject} className="flex justify-between text-sm py-1 border-b last:border-0">
                  <span>{s.subject}</span><span className="text-gray-500">{s.open_rate}% open · ${s.revenue}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "deliverability" && deliver && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-900 text-sm mb-3">
              Inbox deliverability score: <span className={deliver.score >= 80 ? "text-green-600" : deliver.score >= 60 ? "text-amber-600" : "text-red-600"}>{deliver.score}</span>
            </h3>
            {deliver.biggest_offender && (
              <p className="text-xs text-gray-500 mb-3">Biggest offender: <b>{deliver.biggest_offender.provider}</b> — {deliver.biggest_offender.bounce_rate}% bounce</p>
            )}
            {/* Score trend sparkline */}
            <div className="mb-4 p-3 bg-gray-50 rounded border border-gray-100">
              <p className="text-xs text-gray-500 mb-2">Deliverability score trend (last 30 days)</p>
              <Sparkline data={getScoreHistory(deliver)} color={deliver.score >= 80 ? "#22c55e" : deliver.score >= 60 ? "#f59e0b" : "#ef4444"} />
            </div>
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b text-xs text-gray-400">
                <th className="py-2">Provider</th><th className="py-2">Sent</th><th className="py-2">Delivered</th>
                <th className="py-2">Bounce</th><th className="py-2">Spam</th><th className="py-2">Unsub</th>
              </tr></thead>
              <tbody>
                {(deliver.providers ?? []).map((p: any) => (
                  <tr key={p.provider} className="border-b last:border-0">
                    <td className="py-2 font-medium">{p.provider}</td>
                    <td className="py-2">{p.sent}</td>
                    <td className="py-2">{p.delivered_rate}%</td>
                    <td className="py-2">{p.bounce_rate}%</td>
                    <td className="py-2">{p.spam_rate}%</td>
                    <td className="py-2">{p.unsub_rate}%</td>
                  </tr>
                ))}
                {(deliver.providers ?? []).length === 0 && (
                  <tr><td colSpan={6} className="py-6 text-center text-gray-400 text-sm">No deliverability samples — load sample data.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Mini({ label, value }: { label: string; value: any }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-400">{label}</p>
    </div>
  );
}

function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (!data.length) return <p className="text-xs text-gray-400">No history yet</p>;
  const width = 280, height = 60, padding = 10;
  const maxVal = Math.max(...data, 100);
  const minVal = Math.min(...data, 0);
  const range = maxVal - minVal || 1;
  const points = data.map((v, i) => {
    const x = padding + (i / (data.length - 1 || 1)) * (width - 2 * padding);
    const y = height - padding - ((v - minVal) / range) * (height - 2 * padding);
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline fill="none" stroke={color} strokeWidth="2" points={points} />
      <circle cx={padding + (data.length - 1) / (data.length - 1 || 1) * (width - 2 * padding)} 
              cy={height - padding - ((data[data.length - 1] - minVal) / range) * (height - 2 * padding)} 
              r="3" fill={color} />
      <text x={width - padding} y={height - 2} fontSize="10" fill="#9ca3af" textAnchor="end">{data[data.length - 1]}</text>
    </svg>
  );
}

function getScoreHistory(deliver: any): number[] {
  const points: number[] = [];
  const now = new Date();
  for (let i = 29; i >= 0; i--) {
    const day = new Date(now.getTime() - i * 86400000);
    const dayStr = day.toISOString().slice(0, 10);
    let scoreSum = 0, count = 0;
    deliver.providers?.forEach((p: any) => {
      p.history?.forEach((h: any) => {
        if (h.at?.startsWith(dayStr)) {
          const sent = p.sent || 1;
          const delivered = p.delivered || 0;
          const bounced = p.bounced || 0;
          const spam = p.spam || 0;
          const dayScore = Math.max(0, (delivered / sent) * 100 - (bounced / sent) * 200 - (spam / sent) * 300);
          scoreSum += dayScore;
          count++;
        }
      });
    });
    if (count > 0) points.push(Math.round(scoreSum / count));
    else if (points.length > 0) points.push(points[points.length - 1]);
    else points.push(100);
  }
  return points;
}
