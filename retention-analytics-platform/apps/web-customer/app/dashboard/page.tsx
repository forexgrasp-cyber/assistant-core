import { useEffect, useState } from "react";

const API = "/api";

export default function Dashboard() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((data) => { setHealth(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Dashboard</h1>
      <p className="text-gray-500 mb-6">Retention metrics at a glance.</p>

      {loading ? (
        <p className="text-gray-500">Loading platform status…</p>
      ) : health ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded border border-gray-200 shadow-sm">
            <p className="text-sm text-gray-500">Registered Services</p>
            <p className="text-2xl font-bold">{health.services?.length}</p>
          </div>
          <div className="bg-white p-6 rounded border border-gray-200 shadow-sm">
            <p className="text-sm text-gray-500">Workflows (Pipelines)</p>
            <p className="text-2xl font-bold">{health.workflows?.length}</p>
          </div>
          <div className="bg-white p-6 rounded border border-gray-200 shadow-sm">
            <p className="text-sm text-gray-500">Status</p>
            <p className="text-2xl font-bold text-green-600">{health.status}</p>
          </div>
        </div>
      ) : null}

      <div className="bg-white p-6 rounded border border-gray-200 shadow-sm">
        <h2 className="font-semibold text-gray-900 mb-4">Available Workflows</h2>
        <ul className="space-y-2 text-sm">
          {health?.workflows?.map((w: string) => (
            <li key={w} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <span className="text-gray-700">{w}</span>
              <span className="text-xs text-indigo-600 font-medium">runnable</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
