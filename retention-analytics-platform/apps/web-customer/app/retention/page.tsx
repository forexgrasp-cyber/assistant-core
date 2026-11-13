"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

export default function RetentionPage() {
  const [gap, setGap] = useState<any>(null);
  const [paths, setPaths] = useState<any>(null);
  const [ltv, setLtv] = useState<any>(null);
  const [oneTime, setOneTime] = useState<any>(null);
  const [trends, setTrends] = useState<any>(null);
  const [rfm, setRfm] = useState<any>(null);
  const [keyword, setKeyword] = useState("");
  const [msg, setMsg] = useState("");

  const load = () => {
    apiGet("/commerce/time-between-orders").then(setGap).catch(() => {});
    apiGet("/commerce/product-paths").then(setPaths).catch(() => {});
    apiGet("/commerce/subscription-ltv").then(setLtv).catch(() => {});
    apiGet("/commerce/one-time-to-subscriber").then(setOneTime).catch(() => {});
    apiGet("/commerce/product-trends").then(setTrends).catch(() => {});
    apiGet("/commerce/rfm-movement").then(setRfm).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const seed = async () => {
    const now = new Date();
    const daysAgo = (d: number) => new Date(now.getTime() - d * 86400000).toISOString();
    const rows = [
      { customer_email: "a@x.com", amount: 100, products: [{ name: "Sampler Trio", units: 1, revenue: 100 }], placed_at: daysAgo(90) },
      { customer_email: "a@x.com", amount: 60, products: [{ name: "House Blend", units: 1, revenue: 60 }], is_subscription: true, subscription_product: "House Blend", placed_at: daysAgo(50) },
      { customer_email: "a@x.com", amount: 60, products: [{ name: "House Blend", units: 1, revenue: 60 }], is_subscription: true, subscription_product: "House Blend", campaign_id: "camp-1", placed_at: daysAgo(30) },
      { customer_email: "b@x.com", amount: 50, products: [{ name: "Cold Brew Pack", units: 1, revenue: 50 }], placed_at: daysAgo(240) },
      { customer_email: "b@x.com", amount: 70, products: [{ name: "Cold Brew Pack", units: 1, revenue: 70 }], placed_at: daysAgo(40) },
    ];
    for (const r of rows) {
      await apiPost("/commerce/orders", r);
    }
    setMsg("Seeded 5 orders across 2 customers.");
    load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Retention analytics</h1>
          <p className="text-gray-500 text-sm mt-1">
            Repeat purchase, product paths, subscription value and segment movement.
          </p>
        </div>
        <button onClick={seed} className="px-3 py-2 border border-gray-300 rounded text-sm hover:bg-gray-50">Seed sample orders</button>
      </div>

      {msg && <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded text-sm">{msg}</div>}

      {/* Time between orders */}
      {gap && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 text-sm mb-3">Time between orders</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div><p className="text-xs text-gray-400">Median gap (all)</p><p className="text-xl font-bold">{gap.median_gap_days}d</p></div>
            <div><p className="text-xs text-gray-400">After a campaign</p><p className="text-xl font-bold text-green-600">{gap.after_campaign.median_gap_days}d</p>
              {gap.after_campaign.days_sooner != null && <p className="text-[10px] text-green-600">{gap.after_campaign.days_sooner}d sooner</p>}</div>
            <div><p className="text-xs text-gray-400">On their own</p><p className="text-xl font-bold">{gap.on_their_own.median_gap_days}d</p></div>
            <div><p className="text-xs text-gray-400">Reorders</p><p className="text-xl font-bold">{gap.all_reorders}</p>
              <p className="text-[10px] text-gray-400">{gap.returning_customers} returning customers</p></div>
          </div>
          <div className="mt-4 flex flex-wrap gap-1">
            {gap.buckets.map((b: any) => (
              <div key={b.range} className="flex-1 min-w-[80px] text-center">
                <div className="bg-gray-100 rounded h-16 flex items-end justify-center">
                  <div className="bg-indigo-500 rounded-t w-full" style={{ height: `${Math.min(100, b.count * 25)}%` }} />
                </div>
                <p className="text-[10px] text-gray-400 mt-1">{b.range}</p>
                <p className="text-xs font-medium">{b.count}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Product paths */}
      {paths && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900 text-sm">Product purchase paths</h2>
            <input value={keyword} onChange={(e) => setKeyword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && apiGet(`/commerce/product-paths?keyword=${encodeURIComponent(keyword)}`).then(setPaths)}
              placeholder="filter by keyword…" className="border border-gray-300 rounded px-2 py-1 text-xs" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-400 mb-1">Paths</p>
              {paths.paths.slice(0, 8).map((p: any) => (
                <p key={p.path} className="text-xs py-0.5 font-mono">{p.path} <span className="text-gray-400">×{p.count}</span></p>
              ))}
              {paths.paths.length === 0 && <p className="text-xs text-gray-400">No paths yet.</p>}
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Retention by product</p>
              {paths.by_product.map((p: any) => (
                <div key={p.product} className="flex justify-between text-xs py-0.5 border-b last:border-0">
                  <span>{p.product}</span>
                  <span className="text-gray-500">{p.first_time_buyers} first · {p.repeat_rate}% repeat</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Subscription value */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 text-sm mb-3">Subscription LTV</h2>
          {ltv?.by_product?.map((p: any) => (
            <div key={p.product} className="mb-2">
              <p className="text-xs font-medium">{p.product} <span className="text-gray-400">({p.subscribers} subs)</span></p>
              <div className="flex gap-1 mt-1">
                {p.ltv.map((l: any) => (
                  <span key={l.months} className="text-[10px] bg-gray-50 border border-gray-100 rounded px-1.5 py-0.5">
                    {l.months}m: ${l.value}
                  </span>
                ))}
              </div>
            </div>
          ))}
          {ltv?.by_product?.length === 0 && <p className="text-xs text-gray-400">No subscriptions yet.</p>}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 text-sm mb-3">One-time → subscriber</h2>
          {oneTime && (
            <div className="space-y-2 text-sm">
              <div><p className="text-xs text-gray-400">Conversion</p><p className="text-xl font-bold">{oneTime.conversion_rate}%</p>
                <p className="text-[10px] text-gray-400">{oneTime.converted}/{oneTime.one_time_buyers} buyers</p></div>
              <div><p className="text-xs text-gray-400">Avg days to subscribe</p><p className="font-bold">{oneTime.avg_days_to_subscribe ?? "—"}</p></div>
              <div><p className="text-xs text-gray-400">Best first product</p><p className="font-bold">{oneTime.best_first_product ?? "—"}</p></div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 text-sm mb-3">Product trends</h2>
          <p className="text-xs text-gray-400 mb-1">Most new starts</p>
          {trends?.most_new_starts?.map((t: any) => (
            <p key={t.product} className="text-xs py-0.5">{t.product} <span className="text-gray-400">{t.starts} starts</span></p>
          ))}
          <p className="text-xs text-gray-400 mt-2 mb-1">Fastest growing</p>
          {trends?.fastest_growing?.slice(0, 3).map((t: any) => (
            <p key={t.product} className="text-xs py-0.5">{t.product} <span className="text-green-600">↑{t.change}</span></p>
          ))}
          <p className="text-xs text-gray-400 mt-2 mb-1">Top add-on</p>
          {trends?.top_add_on?.map((t: any) => (
            <p key={t.product} className="text-xs py-0.5">{t.product} <span className="text-gray-400">{t.orders} orders</span></p>
          ))}
        </div>
      </div>

      {/* RFM movement */}
      {rfm && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h2 className="font-semibold text-gray-900 text-sm mb-1">RFM movement</h2>
          <p className="text-xs text-gray-400 mb-3">{rfm.attributed_share}% of movement is marketing-attributed</p>
          <table className="w-full text-left text-sm">
            <thead><tr className="border-b text-xs text-gray-400"><th className="py-2">Segment</th><th className="py-2">Customers</th><th className="py-2">Previous</th><th className="py-2">Net change</th></tr></thead>
            <tbody>
              {rfm.segments.map((s: any) => (
                <tr key={s.segment} className="border-b last:border-0">
                  <td className="py-2 capitalize">{s.segment.replace("_", " ")}</td>
                  <td className="py-2">{s.customers}</td>
                  <td className="py-2 text-gray-400">{s.previous}</td>
                  <td className={`py-2 ${s.net_change > 0 ? "text-green-600" : s.net_change < 0 ? "text-red-500" : ""}`}>
                    {s.net_change > 0 ? "↑" : s.net_change < 0 ? "↓" : ""}{s.net_change}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs font-semibold text-gray-400 uppercase mt-4 mb-1">Biggest moves this quarter</p>
          {rfm.biggest_moves.slice(0, 5).map((m: any) => (
            <p key={m.move} className="text-xs py-0.5">
              <b>{m.move.replace("→", " → ")}</b> {m.count}
              <span className="text-gray-400"> · {m.attributed_pct}% attributed</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
