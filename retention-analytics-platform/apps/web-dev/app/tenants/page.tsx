"use client";

import { useState } from "react";
import { UserPlus, Building, Trash2 } from "lucide-react";

const tenants = [
  { id: "t1", name: "Acme Agency", plan: "Growth", clients: 14, status: "active" },
  { id: "t2", name: "Globex Corp", plan: "Enterprise", clients: 42, status: "active" },
  { id: "t3", name: "Hooli", plan: "Starter", clients: 3, status: "paused" },
];

export default function Tenants() {
  const [tenantsList, setTenantsList] = useState(tenants);
  const [newName, setNewName] = useState("");

  const addTenant = () => {
    if (!newName) return;
    setTenantsList([...tenantsList, { id: `t${tenantsList.length + 1}`, name: newName, plan: "Starter", clients: 0, status: "active" }]);
    setNewName("");
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Tenants</h1>
          <p className="text-gray-500 text-sm">Agency → Client → User hierarchy with PostgreSQL RLS.</p>
        </div>
      </div>

      <div className="bg-white p-5 rounded border border-gray-200 shadow-sm mb-8 max-w-md">
        <div className="flex gap-2">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="New tenant name"
            className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button onClick={addTenant} className="px-3 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
            <UserPlus className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="bg-white rounded border border-gray-200 shadow-sm overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Tenant</th>
              <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Plan</th>
              <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Clients</th>
              <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Status</th>
              <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {tenantsList.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <Building className="w-5 h-5 text-gray-400" />
                    <span className="font-medium text-gray-900">{t.name}</span>
                  </div>
                </td>
                <td className="px-5 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    t.plan === "Enterprise" ? "bg-indigo-100 text-indigo-700" :
                    t.plan === "Growth" ? "bg-blue-100 text-blue-700" :
                    "bg-gray-100 text-gray-600"
                  }`}>{t.plan}</span>
                </td>
                <td className="px-5 py-4 text-gray-600">{t.clients}</td>
                <td className="px-5 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    t.status === "active" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
                  }`}>{t.status}</span>
                </td>
                <td className="px-5 py-4">
                  <button className="text-xs text-red-500 hover:text-red-700">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
