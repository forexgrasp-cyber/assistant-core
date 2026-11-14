"use client";

import { useEffect, useState } from "react";

export default function SharePage({ params }: { params: { token: string } }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`/api/v1/share/${params.token}`)
      .then(async (r) => {
        if (!r.ok) throw new Error("This dashboard link is invalid or expired.");
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message));
  }, [params.token]);

  if (error) {
    return <div className="max-w-lg mx-auto py-16 text-center text-gray-500">{error}</div>;
  }
  if (!data) {
    return <div className="max-w-lg mx-auto py-16 text-center text-gray-400">Loading…</div>;
  }

  const brand = data.branding ?? {};
  const accent = brand.primary_color ?? "#4f46e5";
  const saas = data.saas ?? {};
  const retention = data.retention ?? {};
  const campaigns = data.campaigns ?? {};
  const revenue = data.revenue ?? {};
  const attribution = data.attribution ?? {};
  const subscription = data.subscription ?? {};
  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="h-16 flex items-center px-8 bg-white border-b border-gray-200">
        <span className="w-8 h-8 rounded flex items-center justify-center text-white font-bold" style={{ background: accent }}>
          {(brand.company_name ?? "C").slice(0, 1)}
        </span>
        <span className="ml-3 font-bold text-gray-900">{brand.company_name ?? "Your report"}</span>
        <span className="ml-auto text-xs text-gray-400">Shared by Snapford Retention</span>
      </div>

      <div className="max-w-5xl mx-auto p-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Your retention dashboard</h1>
          <p className="text-sm text-gray-500">Generated {data.generated_at?.slice(0, 16).replace("T", " ")}</p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card accent={accent} label="Active subscriptions" value={saas?.mrr?.active_subscriptions ?? 0} />
          <Card accent={accent} label="MRR" value={`$${(saas?.mrr?.mrr ?? 0).toLocaleString()}`} />
          <Card accent={accent} label="30d retention" value={retention?.retention_rate_30d != null ? pct(retention.retention_rate_30d) : "-"} />
          <Card accent={accent} label="30d churn" value={retention?.churn_rate_30d != null ? pct(retention.churn_rate_30d) : "-"} />
        </div>

        {/* Revenue Trend Sparkline */}
        {revenue.monthly?.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 text-sm mb-3">Revenue trend (last 12 months)</h2>
            <RevenueSparkline data={revenue.monthly} color={accent} />
            <p className="text-xs text-gray-400 mt-2">Current: ${(revenue.monthly[revenue.monthly.length - 1] ?? 0).toLocaleString()} · 12m avg: ${Math.round(revenue.monthly.reduce((a: number, b: number) => a + b, 0) / revenue.monthly.length).toLocaleString()}</p>
          </div>
        )}

        {/* Retention Trend */}
        {retention.cohort?.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 text-sm mb-3">Retention by cohort</h2>
            <RetentionCohortChart data={retention.cohort} color={accent} />
          </div>
        )}

        {/* Channel Attribution */}
        {attribution.by_channel && Object.keys(attribution.by_channel).length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 text-sm mb-3">Revenue by channel</h2>
            <AttributionDonut data={attribution.by_channel} color={accent} />
          </div>
        )}

        {/* Subscription Growth */}
        {subscription.growth?.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 text-sm mb-3">Subscription growth</h2>
            <SubscriptionGrowthChart data={subscription.growth} color={accent} />
          </div>
        )}

        {/* SaaS Metrics */}
        {Object.keys(saas).length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 text-sm mb-3">Revenue metrics</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div><p className="text-xs text-gray-400">ARR</p><p className="font-bold">${(saas?.arr?.arr ?? 0).toLocaleString()}</p></div>
              <div><p className="text-xs text-gray-400">Net revenue retention</p><p className="font-bold">{saas?.nrr?.nrr ?? "-"}%</p></div>
              <div><p className="text-xs text-gray-400">Lifetime value</p><p className="font-bold">${(saas?.ltv?.ltv ?? 0).toLocaleString()}</p></div>
              <div><p className="text-xs text-gray-400">Quick ratio</p><p className="font-bold">{saas?.quick_ratio?.quick_ratio ?? "-"}</p></div>
            </div>
          </div>
        )}

        {/* Campaigns */}
        {Object.keys(campaigns).length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 text-sm mb-3">Campaigns that ran for you</h2>
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b text-xs text-gray-400"><th className="py-2">Campaign</th><th className="py-2">Status</th><th className="py-2">Flows</th></tr></thead>
              <tbody>
                {Object.entries(campaigns).map(([key, c]: [string, any]) => (
                  <tr key={key} className="border-b last:border-0">
                    <td className="py-2 font-medium">{c.name}</td>
                    <td className="py-2"><span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{c.status}</span></td>
                    <td className="py-2 text-xs text-gray-500">{(c.flows ?? []).join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function Card({ label, value, accent }: { label: string; value: any; accent: string }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-2xl font-bold mt-1" style={{ color: accent }}>{value}</p>
    </div>
  );
}

function RevenueSparkline({ data, color }: { data: number[]; color: string }) {
  if (!data.length) return <p className="text-xs text-gray-400">No data</p>;
  const width = "100%", height = 80;
  const maxVal = Math.max(...data, 1);
  const minVal = Math.min(...data, 0);
  const range = maxVal - minVal || 1;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1 || 1)) * 100;
    const y = 100 - ((v - minVal) / range) * 80;
    return `${x}%,${y}%`;
  }).join(" ");
  return (
    <svg width={width} height={height} viewBox="0 0 100 100" preserveAspectRatio="none">
      <defs>
        <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`M${points.split(" ").map((p, i) => (i === 0 ? "M" : "L") + p).join(" ")}L100%,100%L0%,100%Z`} fill="url(#revGrad)" />
      <polyline fill="none" stroke={color} strokeWidth="2" points={points} />
      <circle cx={points.split(" ")[points.split(" ").length - 1].split(",")[0].replace("%", "")} cy={points.split(" ")[points.split(" ").length - 1].split(",")[1].replace("%", "")} r="3" fill={color} />
    </svg>
  );
}

function RetentionCohortChart({ data, color }: { data: any[]; color: string }) {
  if (!data.length) return <p className="text-xs text-gray-400">No data</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left">
        <thead>
          <tr className="border-b text-gray-400">
            <th className="py-1 px-2">Cohort</th>
            <th className="py-1 px-2">Size</th>
            {[1, 2, 3, 6, 12].map(m => <th key={m} className="py-1 px-2 text-center">{m}m</th>)}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 8).map((row: any, i: number) => (
            <tr key={i} className="border-b last:border-0">
              <td className="py-1 px-2 font-mono">{row.month}</td>
              <td className="py-1 px-2">{row.size}</td>
              {[1, 2, 3, 6, 12].map(m => (
                <td key={m} className="py-1 px-2 text-center">
                  <div className="w-16 h-4 mx-auto rounded bg-gray-100 overflow-hidden">
                    <div className="h-full" style={{ width: `${row[`retention_${m}m`] ?? 0}%`, background: color }} />
                  </div>
                  <span className="text-[10px]">{row[`retention_${m}m`] ?? 0}%</span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AttributionDonut({ data, color }: { data: Record<string, number>; color: string }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  if (!total) return <p className="text-xs text-gray-400">No data</p>;
  let current = 0;
  const segments = Object.entries(data).map(([channel, value]) => {
    const pct = value / total;
    const start = current * 360;
    const end = (current + pct) * 360;
    current += pct;
    const largeArc = pct > 0.5 ? 1 : 0;
    const x1 = 50 + 40 * Math.cos((start - 90) * Math.PI / 180);
    const y1 = 50 + 40 * Math.sin((start - 90) * Math.PI / 180);
    const x2 = 50 + 40 * Math.cos((end - 90) * Math.PI / 180);
    const y2 = 50 + 40 * Math.sin((end - 90) * Math.PI / 180);
    const hue = Object.keys(data).indexOf(channel) * 60;
    const fill = `hsl(${hue}, 60%, 55%)`;
    return (
      <path key={channel} d={`M50,50 L${x1},${y1} A40,40 0 ${largeArc},1 ${x2},${y2} Z`} fill={fill} />
    );
  });
  return (
    <div className="flex items-center justify-center gap-6">
      <svg width="160" height="160" viewBox="0 0 100 100">{segments}</svg>
      <div className="space-y-1">
        {Object.entries(data).map(([channel, value], i) => (
          <div key={channel} className="flex items-center gap-2">
            <span className="w-3 h-3 rounded" style={{ background: `hsl(${i * 60}, 60%, 55%)` }} />
            <span className="text-xs capitalize">{channel}</span>
            <span className="text-xs font-medium">${value.toLocaleString()}</span>
            <span className="text-xs text-gray-400">({((value / total) * 100).toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SubscriptionGrowthChart({ data, color }: { data: any[]; color: string }) {
  if (!data.length) return <p className="text-xs text-gray-400">No data</p>;
  const maxVal = Math.max(...data.map((d: any) => d.active ?? 0), 1);
  return (
    <div className="h-32 flex items-end justify-around gap-1">
      {data.slice(-12).map((d: any, i: number) => (
        <div key={i} className="flex flex-col items-center" style={{ width: "100%" }}>
          <div className="w-full rounded-t" style={{ height: `${(d.active / maxVal) * 100}%`, background: color }} />
          <span className="text-[10px] text-gray-400 mt-1">{d.month?.slice(5) ?? i}</span>
          <span className="text-[10px] font-medium text-gray-600">{d.active?.toLocaleString() ?? 0}</span>
        </div>
      ))}
    </div>
  );
}
