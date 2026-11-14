"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost, authHeaders } from "@/lib/api";

const FLAG_LABELS: Record<string, string> = {
  workflows: "Retention workflows",
  ai_features: "AI features (churn prediction, offers, feedback)",
  dunning: "Dunning & payment recovery",
  surveys: "NPS / CSAT surveys",
};

export default function Settings() {
  const [settings, setSettings] = useState<any>(null);
  const [keys, setKeys] = useState<any[]>([]);
  const [saved, setSaved] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKey, setNewKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<any>(null);
  const [entitlements, setEntitlements] = useState<any>(null);
  const [quota, setQuota] = useState<any>(null);
  const [providers, setProviders] = useState<any>(null);
  const [monetization, setMonetization] = useState<any>(null);
  const [tickets, setTickets] = useState<any[]>([]);
  const [notifTitle, setNotifTitle] = useState("");
  const [notifResult, setNotifResult] = useState<any>(null);
  const [ticketSubject, setTicketSubject] = useState("");

  const load = () => {
    apiGet("/settings").then((d: any) => { setSettings(d.settings); setLoading(false); }).catch(() => setLoading(false));
    apiGet("/settings/api-keys").then((d: any) => setKeys(d.keys ?? [])).catch(() => {});
    apiGet("/profile").then(setProfile).catch(() => {});
    apiGet("/entitlements").then(setEntitlements).catch(() => {});
    apiPost("/quota/check?resource=api_calls").then(setQuota).catch(() => {});
    apiGet("/payments/providers").then(setProviders).catch(() => {});
    apiGet("/monetization/paths").then(setMonetization).catch(() => {});
    apiGet("/support/tickets").then((d: any) => setTickets(d.tickets ?? [])).catch(() => {});
  };

  const sendNotif = async () => {
    const r: any = await apiPost(`/notifications?title=${encodeURIComponent(notifTitle)}&body=From settings`);
    setNotifResult(r);
  };

  const createTicket = async () => {
    await apiPost(`/support/tickets?subject=${encodeURIComponent(ticketSubject)}&description=Opened from settings`);
    setTicketSubject("");
    load();
  };

  useEffect(() => { load(); }, []);

  const save = async (updates: any) => {
    await apiPost("/settings", { updates });
    // PATCH via fetch since apiPost is POST
    await fetch("/api/v1/settings", {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ updates }),
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    load();
  };

  const toggleFlag = async (flag: string, enabled: boolean) => {
    await apiPost(`/settings/flags/${flag}?enabled=${!enabled}`);
    load();
  };

  const createKey = async () => {
    const r: any = await apiPost(`/settings/api-keys?name=${encodeURIComponent(newKeyName)}`);
    setNewKey(r.key);
    setNewKeyName("");
    load();
  };

  const revokeKey = async (keyId: string) => {
    await fetch(`/api/v1/settings/api-keys/${keyId}`, { method: "DELETE", headers: authHeaders() });
    load();
  };

  const set = (path: string, value: any) => {
    const copy = JSON.parse(JSON.stringify(settings));
    const parts = path.split(".");
    let obj = copy;
    for (let i = 0; i < parts.length - 1; i++) obj = obj[parts[i]];
    obj[parts[parts.length - 1]] = value;
    setSettings(copy);
  };

  if (loading) return <p className="text-gray-400">Loading settings…</p>;
  if (!settings) return <p className="text-red-500">Failed to load settings.</p>;

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500 text-sm mt-1">Configure your workspace. Changes save per tenant.</p>
        </div>
        {saved && <span className="text-green-600 text-sm font-medium">✓ Saved</span>}
      </div>

      {/* Feature flags */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Feature flags</h3>
        <p className="text-xs text-gray-400 mb-4">Turn platform features on/off for your tenant.</p>
        <div className="space-y-3">
          {Object.entries(FLAG_LABELS).map(([flag, label]) => (
            <div key={flag} className="flex items-center justify-between">
              <span className="text-sm text-gray-700">{label}</span>
              <button
                onClick={() => toggleFlag(flag, settings.feature_flags?.[flag])}
                className={`w-11 h-6 rounded-full transition ${settings.feature_flags?.[flag] ? "bg-indigo-600" : "bg-gray-300"}`}
              >
                <span className={`block w-4 h-4 bg-white rounded-full shadow transform transition ${settings.feature_flags?.[flag] ? "translate-x-6" : "translate-x-1"} mt-1`} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Notification channels</h3>
        <p className="text-xs text-gray-400 mb-4">Where alerts and reports get delivered.</p>
        <div className="grid grid-cols-2 gap-3">
          {["email", "sms", "push", "slack"].map((ch) => (
            <label key={ch} className="flex items-center gap-2 text-sm text-gray-700 capitalize cursor-pointer">
              <input
                type="checkbox"
                checked={settings.notifications?.[ch] ?? false}
                onChange={(e) => { set(`notifications.${ch}`, e.target.checked); }}
                className="rounded"
              />
              {ch}
            </label>
          ))}
        </div>
        <button onClick={() => save({ notifications: settings.notifications })} className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Save channels</button>
      </div>

      {/* Quotas */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Usage quotas</h3>
        <p className="text-xs text-gray-400 mb-4">Daily limits for your plan tier.</p>
        <div className="grid grid-cols-3 gap-3">
          {["api_calls_per_day", "events_per_day", "reports_per_day"].map((q) => (
            <div key={q}>
              <label className="text-xs text-gray-500 capitalize">{q.replace(/_/g, " ")}</label>
              <input
                type="number"
                value={settings.quota?.[q] ?? 0}
                onChange={(e) => set(`quota.${q}`, parseInt(e.target.value))}
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-1"
              />
            </div>
          ))}
        </div>
        <button onClick={() => save({ quota: settings.quota })} className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Save quotas</button>
      </div>

      {/* Branding + general */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Workspace</h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-500">Company name</label>
            <input value={settings.branding?.company_name ?? ""} onChange={(e) => set("branding.company_name", e.target.value)} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-1" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Primary color</label>
            <input type="color" value={settings.branding?.primary_color ?? "#4f46e5"} onChange={(e) => set("branding.primary_color", e.target.value)} className="w-full h-9 border border-gray-300 rounded mt-1" />
          </div>
          <div>
            <label className="text-xs text-gray-500">Default channel</label>
            <select value={settings.default_channel ?? "email"} onChange={(e) => set("default_channel", e.target.value)} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-1">
              <option value="email">Email</option><option value="sms">SMS</option><option value="push">Push</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500">Data retention (days)</label>
            <input type="number" value={settings.data_retention_days ?? 365} onChange={(e) => set("data_retention_days", parseInt(e.target.value))} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-1" />
          </div>
        </div>
        <button onClick={() => save({ branding: settings.branding, default_channel: settings.default_channel, data_retention_days: settings.data_retention_days })} className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Save workspace</button>
      </div>

      {/* Attribution rules */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Attribution rules</h3>
        <p className="text-xs text-gray-400 mb-4">Configure how revenue is credited across channels and campaigns. Applied to all clients unless overridden.</p>
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div>
            <label className="text-xs text-gray-500">Default attribution model</label>
            <select value={settings.attribution?.default_model ?? "linear"} onChange={(e) => set("attribution.default_model", e.target.value)} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-1">
              <option value="first_touch">First touch</option>
              <option value="last_touch">Last touch</option>
              <option value="linear">Linear (equal weight)</option>
              <option value="time_decay">Time decay (recent weighted)</option>
              <option value="position_based">Position-based (40/20/40)</option>
            </select>
            <p className="text-[10px] text-gray-400 mt-1">How credit is distributed across touchpoints</p>
          </div>
          <div>
            <label className="text-xs text-gray-500">Attribution window (days)</label>
            <input type="number" value={settings.attribution?.window_days ?? 30} onChange={(e) => set("attribution.window_days", parseInt(e.target.value))} min="1" max="365" className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm mt-1" />
            <p className="text-[10px] text-gray-400 mt-1">Touchpoints older than this are ignored</p>
          </div>
        </div>
        <div className="space-y-2 mb-4">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={settings.attribution?.include_sms ?? true} onChange={(e) => set("attribution.include_sms", e.target.checked)} className="rounded" />
            Include SMS in attribution
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={settings.attribution?.include_push ?? true} onChange={(e) => set("attribution.include_push", e.target.checked)} className="rounded" />
            Include push in attribution
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={settings.attribution?.include_ads ?? false} onChange={(e) => set("attribution.include_ads", e.target.checked)} className="rounded" />
            Include ad/referral in attribution
          </label>
        </div>
        <button onClick={() => save({ attribution: settings.attribution })} className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Save attribution rules</button>
      </div>

      {/* API keys */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 mb-1">API keys</h3>
        <p className="text-xs text-gray-400 mb-4">Keys for programmatic access. Full key shown once on creation.</p>
        {newKey && (
          <div className="bg-amber-50 border border-amber-200 rounded p-3 mb-3">
            <p className="text-xs text-amber-700 mb-1">Copy this key now — it won't be shown again:</p>
            <code className="text-xs font-mono bg-white px-2 py-1 rounded block">{newKey}</code>
          </div>
        )}
        <div className="flex gap-2 mb-3">
          <input value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} placeholder="Key name (e.g. Production)" className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm" />
          <button onClick={createKey} className="px-4 py-1.5 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Create key</button>
        </div>
        <div className="space-y-2">
          {keys.length === 0 && <p className="text-sm text-gray-400">No keys yet.</p>}
          {keys.map((k: any) => (
            <div key={k.key_id} className="flex items-center justify-between p-2 bg-gray-50 rounded border border-gray-100">
              <div>
                <p className="text-sm font-medium text-gray-900">{k.name}</p>
                <p className="text-xs text-gray-400 font-mono">{k.key_prefix} · {k.created_at?.slice(0, 10)}</p>
              </div>
              <button onClick={() => revokeKey(k.key_id)} className="text-red-500 text-xs hover:underline">Revoke</button>
            </div>
          ))}
        </div>
      </div>

      {/* Account & platform surfaces */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Profile & entitlements</h3>
          <p className="text-xs text-gray-500 mb-1">User id: <code className="font-mono">{profile?.profile?.user_id ?? "—"}</code></p>
          <p className="text-xs text-gray-500">Entitlements: {entitlements?.entitlements?.length ?? 0} active</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Quota</h3>
          <p className="text-xs text-gray-500">api_calls: {quota?.status ? "checked" : "—"} · configured daily limit in Settings above</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Payment providers offered</h3>
          <div className="flex flex-wrap gap-1">
            {(providers?.providers ?? []).map((p: string) => <span key={p} className="text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded font-mono">{p}</span>)}
            {(providers?.providers ?? []).length === 0 && <span className="text-xs text-gray-400">set provider keys in .env to enable</span>}
          </div>
          <p className="text-xs text-gray-400 mt-1">{providers?.all_supported?.length ?? 0} supported total</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Monetization paths</h3>
          <div className="flex flex-wrap gap-1">
            {(monetization?.paths ?? []).map((p: string) => <span key={p} className="text-xs bg-purple-50 text-purple-700 px-2 py-0.5 rounded font-mono">{p}</span>)}
          </div>
        </div>
      </div>

      {/* Notifications + support */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Notifications</h3>
          <div className="flex gap-2">
            <input value={notifTitle} onChange={(e) => setNotifTitle(e.target.value)} placeholder="Title" className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm" />
            <button onClick={sendNotif} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Send</button>
          </div>
          {notifResult && <p className="text-xs text-green-700 mt-1">status: {notifResult.status}</p>}
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-900 text-sm mb-2">Support tickets ({tickets.length})</h3>
          <div className="flex gap-2 mb-2">
            <input value={ticketSubject} onChange={(e) => setTicketSubject(e.target.value)} placeholder="Subject" className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm" />
            <button onClick={createTicket} className="px-3 py-1.5 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Open</button>
          </div>
          {tickets.slice(0, 4).map((t) => <p key={t.ticket_id ?? t.id} className="text-xs py-0.5">{t.subject ?? t.id} <span className="text-gray-400">{t.status}</span></p>)}
        </div>
      </div>
    </div>
  );
}
