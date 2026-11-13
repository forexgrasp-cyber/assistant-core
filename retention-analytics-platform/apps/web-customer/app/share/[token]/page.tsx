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
  const campaigns = data.campaigns ?? [];
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

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card accent={accent} label="Active subscriptions" value={saas?.mrr?.active_subscriptions ?? 0} />
          <Card accent={accent} label="MRR" value={`$${saas?.mrr?.mrr ?? 0}`} />
          <Card accent={accent} label="30d retention" value={retention?.retention_rate_30d != null ? pct(retention.retention_rate_30d) : "-"} />
          <Card accent={accent} label="30d churn" value={retention?.churn_rate_30d != null ? pct(retention.churn_rate_30d) : "-"} />
        </div>

        {Object.keys(saas).length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 text-sm mb-3">Revenue metrics</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div><p className="text-xs text-gray-400">ARR</p><p className="font-bold">${saas?.arr?.arr ?? 0}</p></div>
              <div><p className="text-xs text-gray-400">Net revenue retention</p><p className="font-bold">{saas?.nrr?.nrr ?? "-"}%</p></div>
              <div><p className="text-xs text-gray-400">Lifetime value</p><p className="font-bold">${saas?.ltv?.ltv ?? 0}</p></div>
              <div><p className="text-xs text-gray-400">Churn rate</p><p className="font-bold">{saas?.quick_ratio?.quick_ratio ?? "-"}</p></div>
            </div>
          </div>
        )}

        {campaigns.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-5">
            <h2 className="font-semibold text-gray-900 text-sm mb-3">Campaigns that ran for you</h2>
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b text-xs text-gray-400"><th className="py-2">Campaign</th><th className="py-2">Status</th><th className="py-2">Flows</th></tr></thead>
              <tbody>
                {campaigns.map((c: any, i: number) => (
                  <tr key={i} className="border-b last:border-0">
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
