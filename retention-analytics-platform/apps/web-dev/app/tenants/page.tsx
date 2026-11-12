"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";

export default function TenantsPage() {
  const [health, setHealth] = useState<any>(null);
  const [services, setServices] = useState<any[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);

  useEffect(() => {
    apiGet("/health").then(setHealth).catch(() => {});
    apiGet("/services").then((d: any) => setServices(d.services ?? [])).catch(() => {});
    apiGet("/workflows").then((d: any) => setWorkflows(d.workflows ?? [])).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Tenants</h1>
        <p className="text-gray-500 text-sm mt-1">
          Multi-tenancy is enforced at the API boundary: the tenant comes from the JWT principal,
          never from the request body. Cross-tenant access returns 403/404.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <p className="text-xs text-gray-400 uppercase">Current tenant (seed)</p>
          <p className="font-mono text-sm text-gray-900 mt-1 break-all">00000000-0000-0000-0000-000000000001</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <p className="text-xs text-gray-400 uppercase">Environment</p>
          <p className="font-semibold text-gray-900 mt-1">{health?.environment ?? "…"}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
          <p className="text-xs text-gray-400 uppercase">Isolation</p>
          <p className="font-semibold text-green-600 mt-1">Enforced (403 on cross-tenant)</p>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 text-sm mb-3">Tenant-scoped resources visible now</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div><p className="text-gray-400 text-xs uppercase">Services</p><p className="text-xl font-bold">{services.length}</p></div>
          <div><p className="text-gray-400 text-xs uppercase">Workflows</p><p className="text-xl font-bold">{workflows.length}</p></div>
          <div><p className="text-gray-400 text-xs uppercase">Health</p><p className="text-xl font-bold text-green-600">{health?.status ?? "…"}</p></div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-900 text-sm mb-2">How tenancy works</h3>
        <ol className="text-sm text-gray-600 space-y-1 list-decimal list-inside">
          <li>JWT validated → principal tenant extracted (auth.py)</li>
          <li>Any tenant_id in body/header must match principal → else 403 (tenancy.py)</li>
          <li>All queries filtered by tenant_id at the kernel/repository layer</li>
          <li>Audit log records tenant on every mutation</li>
        </ol>
      </div>
    </div>
  );
}
