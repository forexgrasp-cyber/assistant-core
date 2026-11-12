"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

export default function IntegrationsPage() {
  const [catalog, setCatalog] = useState<any>(null);
  const [connectors, setConnectors] = useState<any>(null);
  const [connected, setConnected] = useState<any[]>([]);
  const [syncs, setSyncs] = useState<any[]>([]);
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [slackText, setSlackText] = useState("");
  const [slackResult, setSlackResult] = useState<any>(null);

  const load = () => {
    apiGet("/integrations/catalog").then((d: any) => setCatalog(d.catalog)).catch(() => {});
    apiGet("/connectors").then((d: any) => setConnectors(d.connectors)).catch(() => {});
    apiGet("/integrations/connected").then((d: any) => setConnected(d.connections ?? [])).catch(() => {});
    apiGet("/connectors/syncs").then((d: any) => setSyncs(d.syncs ?? [])).catch(() => {});
    apiGet("/webhook-endpoints").then((d: any) => setWebhooks(d.endpoints ?? [])).catch(() => {});
  };

  useEffect(() => { load(); }, []);

  const connect = async (provider: string, category: string) => {
    setMsg(`Connecting ${provider}…`);
    try {
      await apiPost(`/integrations/connect?provider=${provider}&category=${category}`);
      setMsg(`Connected ${provider}`);
      load();
    } catch (e: any) { setMsg("Error: " + e.message); }
  };

  const sync = async (provider: string) => {
    setMsg(`Syncing ${provider}…`);
    try {
      const r: any = await apiPost(`/connectors/${provider}/sync`);
      setMsg(`${provider}: ${r.status}${r.error ? " — " + r.error : ""}${r.customers_synced ? ` — ${r.customers_synced} customers` : ""}`);
      load();
    } catch (e: any) { setMsg("Sync error: " + e.message); }
  };

  const sendSlack = async () => {
    const r: any = await apiPost(`/integrations/slack/send?text=${encodeURIComponent(slackText)}&channel=%23customer-success`);
    setSlackResult(r);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
        <p className="text-gray-500 text-sm mt-1">
          Connect payment providers, CRM, analytics, and support tools. Sync pulls their data into your customer records. Only providers with keys in .env are offered for payments.
        </p>
      </div>

      {msg && <div className="bg-indigo-50 border border-indigo-200 text-indigo-800 px-4 py-2 rounded text-sm">{msg}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Catalog */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">Integration catalog ({catalog ? Object.values(catalog).flat().length : 0})</h3>
          {catalog && Object.entries(catalog).map(([cat, provs]: [string, any]) => (
            <div key={cat} className="mb-3">
              <p className="text-xs font-semibold text-gray-400 uppercase mb-1">{cat}</p>
              <div className="flex flex-wrap gap-1">
                {(provs as string[]).map((p) => (
                  <button key={p} onClick={() => connect(p, cat)} className="text-xs bg-gray-100 hover:bg-indigo-100 border border-gray-200 hover:border-indigo-300 px-2 py-1 rounded font-mono">
                    {p} +
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Connectors */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-3">Data connectors (pull into your records)</h3>
          <div className="space-y-1.5">
            {connectors && Object.entries(connectors).map(([p, desc]: [string, any]) => (
              <div key={p} className="flex items-center justify-between p-2 bg-gray-50 rounded border border-gray-100">
                <div>
                  <p className="text-sm font-medium font-mono">{p}</p>
                  <p className="text-xs text-gray-400">{desc}</p>
                </div>
                <button onClick={() => sync(p)} className="px-3 py-1.5 bg-emerald-600 text-white rounded text-xs hover:bg-emerald-700">Sync</button>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Connected ({connected.length})</h3>
          {connected.length === 0 && <p className="text-xs text-gray-400">None yet — click + on a provider above.</p>}
          {connected.map((c) => <p key={c.connection_id} className="text-xs font-mono py-1">{c.provider} <span className="text-gray-400">({c.category})</span></p>)}
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Sync history ({syncs.length})</h3>
          {syncs.slice(0, 8).map((s) => (
            <p key={s.sync_id} className="text-xs py-0.5"><span className="font-mono font-medium">{s.provider}</span> {s.action} — {s.records} records · {s.synced_at?.slice(0, 10)}</p>
          ))}
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Webhook endpoints ({webhooks.length})</h3>
          {webhooks.length === 0 && <p className="text-xs text-gray-400">Register in Settings or via API.</p>}
          {webhooks.map((w) => <p key={w.endpoint_id} className="text-xs font-mono py-0.5 truncate">{w.url}</p>)}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
        <h3 className="font-semibold text-gray-900 text-sm mb-2">Send a Slack alert</h3>
        <div className="flex gap-2">
          <input value={slackText} onChange={(e) => setSlackText(e.target.value)} placeholder="Alert text…" className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm" />
          <button onClick={sendSlack} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Send</button>
        </div>
        {slackResult && <p className="text-xs text-green-700 mt-2">Sent to {slackResult.message?.channel} (id {slackResult.message?.message_id?.slice(0, 12)})</p>}
      </div>
    </div>
  );
}
