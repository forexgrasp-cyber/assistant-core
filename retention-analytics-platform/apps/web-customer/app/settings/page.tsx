"use client";

import { useState } from "react";
import { User, Mail, Shield } from "lucide-react";

const API = "/api";

export default function Settings() {
  const [saved, setSaved] = useState(false);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Settings</h1>
      <p className="text-gray-500 mb-6">White-label portal settings for your agency.</p>

      <div className="bg-white p-6 rounded border border-gray-200 shadow-sm max-w-md">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Agency name</label>
            <input
              defaultValue="Acme Agency"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default from email</label>
            <input
              defaultValue="noreply@acme.example"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Default from SMS number</label>
            <input
              defaultValue="+15550000000"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <button
            onClick={() => setSaved(true)}
            className="w-full px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm font-medium"
          >
            Save settings
          </button>
          {saved && <p className="text-sm text-green-600">Saved.</p>}
        </div>
      </div>

      <div className="mt-8 bg-white p-5 rounded border border-gray-200 shadow-sm max-w-md">
        <h3 className="font-semibold text-gray-900 mb-3">Connected services</h3>
        <div className="space-y-3">
          {[<User />, <Mail />, <Shield />].map((Icon, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded border border-gray-100">
              <div className="flex items-center gap-3">
                <Icon className="w-5 h-5 text-gray-400" />
                <span className="text-sm text-gray-700">Service {i + 1}</span>
              </div>
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Connected</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
