"use client";

import { useEffect, useState } from "react";
import { Database, Plus } from "lucide-react";

const API = "/api";

export default function SchemaBuilder() {
  const [schemas, setSchemas] = useState<any[]>([]);
  const [newName, setNewName] = useState("");

  useEffect(() => {
    // Entity schemas live in the API kernel; surface what's registered.
    fetch(`${API}/entities/client`)
      .then((r) => r.json())
      .then((data) => setSchemas([{ id: "client", name: "Client", fields: Object.keys(data.data ?? {}) }]))
      .catch(() => {});
  }, []);

  const addSchema = async () => {
    if (!newName) return;
    setSchemas((prev) => [...prev, { id: newName.toLowerCase(), name: newName, fields: [] }]);
    setNewName("");
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Schema Builder</h1>
          <p className="text-gray-500 text-sm">Schema-as-data: entities, fields, relationships defined at runtime.</p>
        </div>
      </div>

      <div className="bg-white p-5 rounded border border-gray-200 shadow-sm mb-8">
        <div className="flex gap-2 mb-4">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="New entity name (e.g. LoyaltyTier)"
            className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button onClick={addSchema} className="px-3 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
            <Plus className="w-4 h-4" /> Add
          </button>
        </div>
      </div>

      <h2 className="font-semibold text-gray-900 mb-3">Registered Entities</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {schemas.map((s) => (
          <div key={s.id} className="bg-white p-4 rounded border border-gray-200 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-5 h-5 text-gray-400" />
              <span className="font-semibold text-gray-900">{s.name}</span>
              <span className="ml-auto text-xs text-gray-400">{s.id}</span>
            </div>
            <p className="text-xs text-gray-500 mb-3">
              Fields: {s.fields?.length ?? 0} &nbsp;•&nbsp; Shared across services & workflows
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
