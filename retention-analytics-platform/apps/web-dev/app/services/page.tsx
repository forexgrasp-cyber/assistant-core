"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

interface Service { name: string; version: string; actions: string[]; metadata?: Record<string, string>; }

const samplePayloads: Record<string, string> = {
  "analytics.metric": `{"payload": {"tenant_id": "00000000-0000-0000-0000-000000000001"}}`,
  "analytics.cohort": `{"payload": {"tenant_id": "00000000-0000-0000-0000-000000000001", "cohort_months": 6}}`,
  email: `{"payload": {"to": "dev@example.com", "subject": "Test from console", "body": "Hello"}}`,
  sms: `{"payload": {"to": "+15550000000", "body": "Test SMS"}}`,
  push: `{"payload": {"device_token": "tok_abc", "title": "Test", "body": "Push test"}}`,
  "ecommerce.core": `{"payload": {"cart_id": "cart-1", "customer_email": "c@example.com"}}`,
  quota: `{"payload": {"tenant_id": "00000000-0000-0000-0000-000000000001", "resource": "api_calls"}}`,
  entitlements: `{"payload": {"tenant_id": "00000000-0000-0000-0000-000000000001", "feature": "premium"}}`,
  feature_flags: `{"payload": {"flag": "new-feature", "tenant_id": "00000000-0000-0000-0000-000000000001"}}`,
};

export default function ServicesExplorer() {
  const [services, setServices] = useState<Service[]>([]);
  const [selected, setSelected] = useState<Service | null>(null);
  const [action, setAction] = useState("");
  const [payload, setPayload] = useState("");
  const [result, setResult] = useState<any>(null);
  const [invoking, setInvoking] = useState(false);

  useEffect(() => {
    apiGet("/services")
      .then((d: any) => {
        const svcs = d.services ?? [];
        setServices(svcs);
        if (svcs.length > 0) {
          setSelected(svcs[0]);
          setAction(svcs[0].actions[0] ?? "");
          setPayload(samplePayloads[svcs[0].name] ?? `{"payload": {}}`);
        }
      })
      .catch(() => {});
  }, []);

  const pickService = (s: Service) => {
    setSelected(s);
    setAction(s.actions[0] ?? "");
    setPayload(samplePayloads[s.name] ?? `{"payload": {}}`);
    setResult(null);
  };

  const invoke = async () => {
    if (!selected || !action) return;
    setInvoking(true);
    setResult(null);
    try {
      let body: any;
      try { body = JSON.parse(payload); } catch { throw new Error("Invalid JSON"); }
      const data = await apiPost(`/services/${selected.name}/actions/${action}`, body);
      setResult({ ok: true, data });
    } catch (e: any) {
      setResult({ ok: false, error: e.message });
    } finally {
      setInvoking(false);
    }
  };

  const domain = (s: Service) => s.metadata?.domain ?? s.name.split(".")[0];
  const grouped = services.reduce((acc, s) => {
    const d = domain(s);
    (acc[d] ??= []).push(s);
    return acc;
  }, {} as Record<string, Service[]>);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Service Explorer</h1>
        <p className="text-gray-500 text-sm mt-1">
          {services.length} registered services. Pick one, pick an action, send JSON input, see the output.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Service list grouped by domain */}
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
          {Object.entries(grouped).map(([dom, svcs]) => (
            <div key={dom}>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2 capitalize">{dom}</p>
              <div className="space-y-1">
                {svcs.map((s) => (
                  <button
                    key={s.name}
                    onClick={() => pickService(s)}
                    className={`w-full text-left px-3 py-2 rounded text-sm font-mono transition ${
                      selected?.name === s.name
                        ? "bg-emerald-100 text-emerald-900 border border-emerald-300"
                        : "bg-white border border-gray-200 hover:border-gray-300 text-gray-700"
                    }`}
                  >
                    {s.name}
                    <span className="text-xs text-gray-400 ml-2">{s.actions.length} actions</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Invoke panel */}
        <div className="lg:col-span-2 space-y-4">
          {selected && (
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
              <div>
                <h2 className="font-semibold text-gray-900 font-mono">{selected.name}</h2>
                <p className="text-xs text-gray-400">v{selected.version}{selected.metadata?.domain ? ` · ${selected.metadata.domain}` : ""}</p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Action</label>
                <select
                  value={action}
                  onChange={(e) => setAction(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono"
                >
                  {selected.actions.map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Request body (JSON)</label>
                <textarea
                  value={payload}
                  onChange={(e) => setPayload(e.target.value)}
                  rows={6}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <button
                onClick={invoke}
                disabled={invoking}
                className="px-5 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
              >
                {invoking ? "Invoking…" : "Invoke"}
              </button>
              <p className="text-xs text-gray-400 font-mono">
                POST /api/v1/services/{selected.name}/actions/{action || "…"}
              </p>
            </div>
          )}

          {result && (
            <div className={`rounded-lg border p-4 ${result.ok ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
              <p className={`text-sm font-medium mb-2 ${result.ok ? "text-green-700" : "text-red-700"}`}>
                {result.ok ? "Response" : `Error: ${result.error}`}
              </p>
              {result.ok && (
                <pre className="text-xs bg-white p-3 rounded border overflow-x-auto max-h-80">
                  {JSON.stringify(result.data, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
