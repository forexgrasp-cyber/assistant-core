'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  LayoutDashboard, Database, GitBranch, FlaskConical, Settings, BarChart3,
  ChevronLeft, ChevronRight, Plus, Trash2, Play, RefreshCw, Loader2, Search,
} from 'lucide-react';
import { api } from '@/lib/api';
import type { Workflow, VerticalPack, PackEntity, Agency, DashboardSummary } from '@/lib/api';
import toast from 'react-hot-toast';

const navItems = [
  { id: 'schema', label: 'Schema Builder', icon: Database },
  { id: 'workflows', label: 'Workflow Designer', icon: GitBranch },
  { id: 'vertical-packs', label: 'Vertical Packs', icon: FlaskConical },
  { id: 'tenants', label: 'Tenant Manager', icon: LayoutDashboard },
  { id: 'analytics', label: 'Analytics Explorer', icon: BarChart3 },
  { id: 'settings', label: 'Settings', icon: Settings },
] as const;

type TabId = (typeof navItems)[number]['id'];

export default function DevConsolePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>('workflows');

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        <div className="flex h-16 items-center justify-between px-4 border-b border-gray-200 dark:border-gray-700">
          <h1 className="text-xl font-bold text-primary-600 dark:text-primary-400">Dev Console</h1>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="Toggle sidebar"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === item.id
                  ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                  : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'
              }`}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="flex-1 lg:ml-64 overflow-auto">
        <header className="sticky top-0 z-40 h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
              aria-label="Toggle sidebar"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
            <h2 className="text-xl font-semibold">{navItems.find((i) => i.id === activeTab)?.label}</h2>
          </div>
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm text-gray-600 dark:text-gray-300">
            <span>dev-user</span>
          </div>
        </header>

        <div className="p-6">
          {activeTab === 'schema' && <SchemaBuilderTab />}
          {activeTab === 'workflows' && <WorkflowsTab />}
          {activeTab === 'vertical-packs' && <VerticalPacksTab />}
          {activeTab === 'tenants' && <TenantManagerTab />}
          {activeTab === 'analytics' && <AnalyticsExplorerTab />}
          {activeTab === 'settings' && <SettingsTab />}
        </div>
      </main>
    </div>
  );
}

// ── Shared helpers ────────────────────────────────────────────────────────

function LoadingState({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-gray-500">
      <Loader2 className="w-5 h-5 animate-spin mr-2" />
      Loading {label}...
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
      <p className="text-red-700 dark:text-red-300">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 px-4 py-2 bg-red-100 dark:bg-red-900/40 rounded-lg text-red-700 dark:text-red-300 hover:bg-red-200">
          Retry
        </button>
      )}
    </div>
  );
}

// ── Schema Builder (pack entities) ────────────────────────────────────────

function SchemaBuilderTab() {
  const [packs, setPacks] = useState<VerticalPack[]>([]);
  const [selectedPack, setSelectedPack] = useState<string>('');
  const [entities, setEntities] = useState<PackEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.listPacks({ limit: 50 });
      const items: VerticalPack[] = data.items || data || [];
      setPacks(items);
    } catch {
      setError('Failed to load vertical packs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!selectedPack) { setEntities([]); return; }
    api.listPackEntities(selectedPack)
      .then(setEntities)
      .catch(() => toast.error('Failed to load entities'));
  }, [selectedPack]);

  if (loading) return <LoadingState label="packs" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Entity Schema Builder</h3>
          <p className="text-gray-500 dark:text-gray-400">Entities defined by installed vertical packs</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <select
          value={selectedPack}
          onChange={(e) => setSelectedPack(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
        >
          <option value="">Select a pack...</option>
          {packs.map((p) => (
            <option key={p.id} value={p.id}>{p.name} v{p.version}</option>
          ))}
        </select>
      </div>

      {selectedPack && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-700">
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Slug</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Category</th>
                <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {entities.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-2 text-sm">{e.display_name || e.name}</td>
                  <td className="px-4 py-2 text-sm text-gray-500">{e.slug}</td>
                  <td className="px-4 py-2 text-sm">{e.category || '-'}</td>
                  <td className="px-4 py-2 text-sm">
                    <span className={`px-2 py-0.5 rounded text-xs ${e.is_system ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}`}>
                      {e.is_system ? 'system' : 'custom'}
                    </span>
                  </td>
                </tr>
              ))}
              {entities.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-500 text-sm">No entities defined for this pack</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {!selectedPack && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
          <p className="text-gray-500 dark:text-gray-400">Select a vertical pack to view its entity schemas ({packs.length} packs available)</p>
        </div>
      )}
    </div>
  );
}

// ── Workflows ─────────────────────────────────────────────────────────────

function WorkflowsTab() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.listWorkflows({ limit: 100 });
      setWorkflows(data.items || data || []);
    } catch {
      setError('Failed to load workflows');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!name.trim()) { toast.error('Name is required'); return; }
    try {
      await api.createWorkflow({ name: name.trim(), description: description.trim() || undefined, status: 'draft' } as any);
      toast.success('Workflow created');
      setName('');
      setDescription('');
      setShowCreate(false);
      load();
    } catch {
      toast.error('Failed to create workflow');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteWorkflow(id);
      toast.success('Workflow deleted');
      load();
    } catch {
      toast.error('Failed to delete workflow');
    }
  };

  const handleExecute = async (id: string) => {
    try {
      await api.executeWorkflow(id);
      toast.success('Workflow execution started');
      load();
    } catch {
      toast.error('Failed to execute workflow');
    }
  };

  if (loading) return <LoadingState label="workflows" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Workflow Designer</h3>
          <p className="text-gray-500 dark:text-gray-400">{workflows.length} workflows</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="px-4 py-2 bg-primary text-white rounded-lg flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Workflow
        </button>
      </div>

      {showCreate && (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 space-y-3">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Workflow name"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
          />
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description (optional)"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
          />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-2 bg-primary text-white rounded-lg text-sm">Create</button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {workflows.map((w) => (
          <div key={w.id} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-semibold">{w.name}</h4>
              <span className={`px-2 py-0.5 rounded text-xs ${
                w.status === 'published' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
              }`}>
                {w.status}
              </span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 line-clamp-2">{w.description || 'No description'}</p>
            <div className="flex gap-2">
              <button onClick={() => handleExecute(w.id)} className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-1">
                <Play className="w-3 h-3" /> Execute
              </button>
              <button onClick={() => handleDelete(w.id)} className="px-3 py-1 text-sm border border-red-300 text-red-600 rounded hover:bg-red-50 flex items-center gap-1">
                <Trash2 className="w-3 h-3" /> Delete
              </button>
            </div>
          </div>
        ))}
        {workflows.length === 0 && (
          <div className="col-span-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 text-center text-gray-500">
            No workflows yet — create your first one
          </div>
        )}
      </div>
    </div>
  );
}

// ── Vertical Packs ────────────────────────────────────────────────────────

function VerticalPacksTab() {
  const [packs, setPacks] = useState<VerticalPack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.listPacks({ limit: 50 });
      setPacks(data.items || data || []);
    } catch {
      setError('Failed to load vertical packs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleInstall = async (packId: string) => {
    try {
      await api.installPack(packId);
      toast.success('Pack installation started');
      load();
    } catch {
      toast.error('Failed to install pack');
    }
  };

  if (loading) return <LoadingState label="packs" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Vertical Packs</h3>
          <p className="text-gray-500 dark:text-gray-400">{packs.length} packs in registry</p>
        </div>
        <button onClick={load} className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg flex items-center gap-2 text-sm">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {packs.map((p) => (
          <div key={p.id} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
            <div className="flex items-start justify-between mb-2">
              <h4 className="font-semibold">{p.name}</h4>
              <span className={`px-2 py-0.5 rounded text-xs ${p.is_published ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                {p.is_published ? 'published' : p.status}
              </span>
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">{p.description || 'No description'}</p>
            <div className="flex items-center gap-3 text-xs text-gray-500 mb-4">
              <span>v{p.version}</span>
              <span>{p.price > 0 ? `$${p.price}/${p.currency}` : 'Free'}</span>
              <span>★ {p.rating?.toFixed(1) || '0.0'} ({p.review_count})</span>
              <span>{p.downloads} installs</span>
            </div>
            <button
              onClick={() => handleInstall(p.id)}
              disabled={!p.is_published}
              className="px-3 py-1.5 text-sm bg-primary text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Install
            </button>
          </div>
        ))}
        {packs.length === 0 && (
          <div className="col-span-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 text-center text-gray-500">
            No vertical packs registered
          </div>
        )}
      </div>
    </div>
  );
}

// ── Tenants ───────────────────────────────────────────────────────────────

function TenantManagerTab() {
  const [agencies, setAgencies] = useState<Agency[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.listAgencies({ limit: 100 });
      setAgencies(data.items || data || []);
    } catch {
      setError('Failed to load tenants');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <LoadingState label="tenants" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Tenant Manager</h3>
          <p className="text-gray-500 dark:text-gray-400">{agencies.length} agencies</p>
        </div>
        <button onClick={load} className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg flex items-center gap-2 text-sm">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-700">
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Agency</th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Slug</th>
              <th className="px-4 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {agencies.map((a) => (
              <tr key={a.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-4 py-2 text-sm font-medium">{a.name}</td>
                <td className="px-4 py-2 text-sm text-gray-500">{a.slug}</td>
                <td className="px-4 py-2 text-sm">
                  <span className={`px-2 py-0.5 rounded text-xs ${a.is_active !== false ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                    {a.is_active !== false ? 'active' : 'inactive'}
                  </span>
                </td>
              </tr>
            ))}
            {agencies.length === 0 && (
              <tr><td colSpan={3} className="px-4 py-8 text-center text-gray-500 text-sm">No agencies registered</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Analytics Explorer ────────────────────────────────────────────────────

function AnalyticsExplorerTab() {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [days, setDays] = useState(30);
  const [queryResult, setQueryResult] = useState<any>(null);
  const [metric, setMetric] = useState('total_revenue');
  const [querying, setQuerying] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getDashboard({ days });
      setDashboard(data);
    } catch {
      setError('Failed to load analytics');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  const runQuery = async () => {
    setQuerying(true);
    try {
      const result = await api.executeQuery({
        source: { type: 'daily_facts', metrics: [metric], dimensions: ['date'] },
        date_range: { days },
      });
      setQueryResult(result);
    } catch {
      toast.error('Query failed');
    } finally {
      setQuerying(false);
    }
  };

  if (loading) return <LoadingState label="analytics" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Analytics Explorer</h3>
          <p className="text-gray-500 dark:text-gray-400">Ad-hoc queries over daily facts</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last 365 days</option>
        </select>
      </div>

      {/* Summary cards */}
      {dashboard && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
            <p className="text-xs text-gray-500 uppercase">Revenue</p>
            <p className="text-2xl font-bold">${(dashboard.totals.revenue || 0).toLocaleString()}</p>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
            <p className="text-xs text-gray-500 uppercase">Orders</p>
            <p className="text-2xl font-bold">{(dashboard.totals.orders || 0).toLocaleString()}</p>
          </div>
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
            <p className="text-xs text-gray-500 uppercase">New Customers</p>
            <p className="text-2xl font-bold">{(dashboard.totals.new_customers || 0).toLocaleString()}</p>
          </div>
        </div>
      )}

      {/* Ad-hoc query */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium">Metric:</label>
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
          >
            <option value="total_revenue">total_revenue</option>
            <option value="email_revenue">email_revenue</option>
            <option value="sms_revenue">sms_revenue</option>
            <option value="push_revenue">push_revenue</option>
            <option value="organic_revenue">organic_revenue</option>
            <option value="sessions">sessions</option>
            <option value="total_orders">total_orders</option>
          </select>
          <span className="text-sm text-gray-500">grouped by date</span>
          <button
            onClick={runQuery}
            disabled={querying}
            className="ml-auto px-4 py-2 bg-primary text-white rounded-lg text-sm flex items-center gap-2 disabled:opacity-50"
          >
            {querying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Run Query
          </button>
        </div>

        {queryResult && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-700">
                  {(queryResult.columns || []).map((c: string) => (
                    <th key={c} className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {(queryResult.data || []).slice(0, 30).map((row: Record<string, any>, i: number) => (
                  <tr key={i}>
                    {(queryResult.columns || []).map((c: string) => (
                      <td key={c} className="px-3 py-1.5">{typeof row[c] === 'number' ? row[c].toLocaleString() : String(row[c] ?? '-')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-xs text-gray-500">
              {queryResult.row_count} rows in {queryResult.execution_time_ms}ms
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Settings ──────────────────────────────────────────────────────────────

function SettingsTab() {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">Settings</h3>
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 space-y-6">
        <div>
          <h4 className="font-semibold mb-4">Platform Configuration</h4>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium mb-1">Default Timezone</label>
              <select className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700">
                <option>UTC</option>
                <option>America/New_York</option>
                <option>Europe/London</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Default Currency</label>
              <input type="text" defaultValue="USD" className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg" />
            </div>
          </div>
        </div>
        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <h4 className="font-semibold mb-4">API Connection</h4>
          <p className="text-sm text-gray-500">
            Base URL: <code className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">{process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765'}</code>
          </p>
        </div>
      </div>
    </div>
  );
}
