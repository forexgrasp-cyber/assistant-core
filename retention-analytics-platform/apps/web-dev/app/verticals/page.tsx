"use client";

import { useState } from "react";
import { Layers, Folder, Globe } from "lucide-react";

const packs = [
  { id: "marketing", name: "Marketing", description: "Campaigns, audiences, lead scoring", icon: <Globe /> },
  { id: "ecommerce", name: "Ecommerce", description: "Products, orders, subscriptions, cart recovery", icon: <Layers /> },
  { id: "saas", name: "SaaS", description: "Subscriptions, plans, dunning, activation", icon: <Folder /> },
  { id: "fintech", name: "Fintech", description: "Wallets, transactions, KYC, fraud", icon: <ShieldIcon /> },
  { id: "healthcare", name: "Healthcare", description: "Patients, appointments, compliance", icon: <Folder /> },
];

function ShieldIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
    </svg>
  );
}

export default function VerticalPacks() {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Vertical Packs</h1>
      <p className="text-gray-500 mb-6">Pluggable domain packs with entities, workflows, and reports. Zero vertical logic in core.</p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {packs.map((p) => (
          <div
            key={p.id}
            onClick={() => setSelected(selected === p.id ? null : p.id)}
            className={`bg-white p-5 rounded border border-gray-200 shadow-sm cursor-pointer hover:border-indigo-300 transition ${selected === p.id ? "border-indigo-500 bg-indigo-50" : ""}`}
          >
            <div className="p-2 bg-gray-100 rounded text-gray-600 mb-3">{p.icon}</div>
            <h3 className="font-semibold text-gray-900">{p.name}</h3>
            <p className="text-xs text-gray-500 mt-2">{p.description}</p>
            {selected === p.id && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-sm text-gray-600 mb-3">Includes:</p>
                <ul className="space-y-1 text-xs text-gray-500">
                  <li>Entities: clients, campaigns, flows</li>
                  <li>Workflows: retention, win-back</li>
                  <li>Reports: cohort, RFM</li>
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
