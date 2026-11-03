"use client";

import { useEffect, useState } from "react";
import { Mail, Phone, Smartphone } from "lucide-react";

const API = "/api";

const channels = [
  { name: "email", icon: <Mail />, label: "Email" },
  { name: "sms", icon: <Phone />, label: "SMS" },
  { name: "push", icon: <Smartphone />, label: "Push" },
];

export default function Campaigns() {
  const [services, setServices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/services`)
      .then((r) => r.json())
      .then((data) => setServices(data.services ?? []))
      .catch(() => setLoading(false));
  }, []);

  const send = async (channel: string) => {
    const payload =
      channel === "email"
        ? { to: "customer@example.com", subject: "We miss you!", body: "20% off your next month." }
        : channel === "sms"
          ? { to: "+15550000000", body: "We miss you! 20% off." }
          : { device_token: "tok_abc", title: "We miss you!", body: "20% off." };
    const res = await fetch(`${API}/services/${channel}/actions/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload }),
    });
    setResult(await res.json());
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Campaigns</h1>
      <p className="text-gray-500 mb-6">Send campaigns across channels — each call goes through a service registered in a workflow.</p>

      {loading ? (
        <p className="text-gray-500">Loading services…</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {channels.map((ch) => (
            <div key={ch.name} className="bg-white p-4 rounded border border-gray-200 shadow-sm flex flex-col items-center">
              <div className="p-2 bg-indigo-100 text-indigo-600 rounded">{ch.icon}</div>
              <h3 className="font-semibold text-gray-900 mt-2">{ch.label}</h3>
              <button
                onClick={() => send(ch.name)}
                className="mt-3 px-3 py-1.5 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700"
                disabled={loading}
              >
                Send {ch.label}
              </button>
            </div>
          ))}
        </div>
      )}

      {result && (
        <div className="bg-white p-4 rounded border border-gray-200 shadow-sm mt-6">
          <h3 className="font-semibold text-gray-900 mb-2">Last send result</h3>
          <pre className="text-xs text-gray-600 bg-gray-50 p-3 rounded overflow-x-auto">{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
