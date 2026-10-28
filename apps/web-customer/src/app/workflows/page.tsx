'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAppStore } from '@/store';
import { api } from '@/lib/api';
import { Plus, Search, Filter, MoreVertical, Edit, Trash2, Copy, Play, Eye, Download, Upload, X } from 'lucide-react';
import { format } from 'date-fns';
import toast from 'react-hot-toast';

interface WorkflowListItem {
  id: string;
  name: string;
  slug: string;
  description?: string;
  category: string;
  status: string;
  version: number;
  totalExecutions: number;
  successfulExecutions: number;
  failedExecutions: number;
  createdAt: string;
  updatedAt: string;
}

export default function WorkflowsPage() {
  const { user, setLoading } = useAppStore();
  const router = useRouter();
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([]);
  const [loading, setLocalLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWorkflowName, setNewWorkflowName] = useState('');
  const [newWorkflowCategory, setNewWorkflowCategory] = useState('general');

  useEffect(() => {
    loadWorkflows();
  }, [statusFilter, categoryFilter]);

  async function loadWorkflows() {
    setLocalLoading(true);
    setLoading(true);
    try {
      const data = await api.listWorkflows({ status: statusFilter, category: categoryFilter, limit: 100 });
      setWorkflows(data.items);
    } catch (error) {
      toast.error('Failed to load workflows');
    } finally {
      setLocalLoading(false);
      setLoading(false);
    }
  }

  async function handleCreateWorkflow() {
    if (!newWorkflowName.trim()) return;
    try {
      const workflow = await api.createWorkflow({
        name: newWorkflowName,
        category: newWorkflowCategory,
        status: 'draft',
      });
      toast.success('Workflow created');
      setShowCreateModal(false);
      setNewWorkflowName('');
      router.push(`/workflows/${workflow.id}/edit`);
    } catch (error) {
      toast.error('Failed to create workflow');
    }
  }

  async function handleDeleteWorkflow(id: string) {
    if (!confirm('Are you sure you want to delete this workflow?')) return;
    try {
      await api.deleteWorkflow(id);
      toast.success('Workflow deleted');
      loadWorkflows();
    } catch (error) {
      toast.error('Failed to delete workflow');
    }
  }

  async function handleDuplicateWorkflow(w: WorkflowListItem) {
    try {
      const workflow = await api.createWorkflow({
        name: `${w.name} (Copy)`,
        category: w.category,
        status: 'draft',
      });
      toast.success('Workflow duplicated');
      router.push(`/workflows/${workflow.id}/edit`);
    } catch (error) {
      toast.error('Failed to duplicate workflow');
    }
  }

  const filteredWorkflows = workflows.filter(w =>
    w.name.toLowerCase().includes(search.toLowerCase()) ||
    w.description?.toLowerCase().includes(search.toLowerCase())
  );

  const statusColors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    published: 'bg-green-100 text-green-700',
    deprecated: 'bg-yellow-100 text-yellow-700',
    archived: 'bg-red-100 text-red-700',
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-card border-r border-border flex flex-col hidden lg:flex">
        <div className="p-4 border-b border-border">
          <h1 className="text-xl font-bold text-primary">Retention Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">Workflows</p>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          <Link
            href="/dashboard"
            className="w-full px-3 py-2 rounded-lg text-left transition-colors hover:bg-accent text-foreground"
          >
            Dashboard
          </Link>
          <Link
            href="/workflows"
            className="w-full px-3 py-2 rounded-lg text-left transition-colors bg-primary text-primary-foreground"
          >
            Workflows
          </Link>
          <Link
            href="/reports"
            className="w-full px-3 py-2 rounded-lg text-left transition-colors hover:bg-accent text-foreground"
          >
            Reports
          </Link>
          <Link
            href="/analytics"
            className="w-full px-3 py-2 rounded-lg text-left transition-colors hover:bg-accent text-foreground"
          >
            Analytics
          </Link>
          <Link
            href="/engagement"
            className="w-full px-3 py-2 rounded-lg text-left transition-colors hover:bg-accent text-foreground"
          >
            Engagement
          </Link>
          <Link
            href="/settings"
            className="w-full px-3 py-2 rounded-lg text-left transition-colors hover:bg-accent text-foreground"
          >
            Settings
          </Link>
        </nav>

        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-sm font-medium text-primary">
                {user?.name?.charAt(0) || 'U'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name || 'User'}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email || ''}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6 sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold">Workflows</h2>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search workflows..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-64 pl-10 pr-4 py-2 border border-input rounded-lg bg-background text-sm"
              />
            </div>

            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-input rounded-lg bg-background text-sm"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="deprecated">Deprecated</option>
              <option value="archived">Archived</option>
            </select>

            <select
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value)}
              className="px-3 py-2 border border-input rounded-lg bg-background text-sm"
            >
              <option value="">All Categories</option>
              <option value="general">General</option>
              <option value="retention">Retention</option>
              <option value="engagement">Engagement</option>
              <option value="ecommerce">E-commerce</option>
              <option value="reporting">Reporting</option>
              <option value="analytics">Analytics</option>
            </select>

            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg flex items-center gap-2 hover:bg-primary/90"
            >
              <Plus className="w-4 h-4" />
              New Workflow
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          )}

          {!loading && filteredWorkflows.length === 0 && (
            <div className="text-center py-16">
              <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
                <Play className="w-8 h-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-medium mb-2">No workflows yet</h3>
              <p className="text-muted-foreground mb-6">Create your first workflow to automate retention campaigns</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-6 py-3 bg-primary text-primary-foreground rounded-lg flex items-center gap-2 mx-auto"
              >
                <Plus className="w-4 h-4" />
                Create Workflow
              </button>
            </div>
          )}

          {!loading && filteredWorkflows.length > 0 && (
            <div className="space-y-4">
              {filteredWorkflows.map(w => (
                <WorkflowCard
                  key={w.id}
                  workflow={w}
                  onEdit={() => router.push(`/workflows/${w.id}/edit`)}
                  onDuplicate={() => handleDuplicateWorkflow(w)}
                  onExecute={() => router.push(`/workflows/${w.id}/execute`)}
                  onDelete={() => handleDeleteWorkflow(w.id)}
                  onViewExecutions={() => router.push(`/workflows/${w.id}/executions`)}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="font-semibold">Create New Workflow</h3>
              <button onClick={() => setShowCreateModal(false)} className="p-1 hover:bg-accent rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="text-sm font-medium block mb-1">Name</label>
                <input
                  type="text"
                  value={newWorkflowName}
                  onChange={e => setNewWorkflowName(e.target.value)}
                  placeholder="e.g., Welcome Email Sequence"
                  className="w-full px-3 py-2 border border-input rounded-lg bg-background"
                  autoFocus
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-1">Category</label>
                <select
                  value={newWorkflowCategory}
                  onChange={e => setNewWorkflowCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-lg bg-background"
                >
                  <option value="general">General</option>
                  <option value="retention">Retention</option>
                  <option value="engagement">Engagement</option>
                  <option value="ecommerce">E-commerce</option>
                  <option value="reporting">Reporting</option>
                  <option value="analytics">Analytics</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <button onClick={() => setShowCreateModal(false)} className="px-4 py-2 border border-input rounded-lg hover:bg-accent">
                  Cancel
                </button>
                <button onClick={handleCreateWorkflow} className="px-4 py-2 bg-primary text-primary-foreground rounded-lg">
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function WorkflowCard({
  workflow,
  onEdit,
  onDuplicate,
  onExecute,
  onDelete,
  onViewExecutions,
}: {
  workflow: WorkflowListItem;
  onEdit: () => void;
  onDuplicate: () => void;
  onExecute: () => void;
  onDelete: () => void;
  onViewExecutions: () => void;
}) {
  const statusColors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    published: 'bg-green-100 text-green-700',
    deprecated: 'bg-yellow-100 text-yellow-700',
    archived: 'bg-red-100 text-red-700',
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold truncate">{workflow.name}</h3>
            <span className={`px-2 py-0.5 text-xs rounded-full ${statusColors[workflow.status] || 'bg-gray-100 text-gray-700'}`}>
              {workflow.status}
            </span>
            <span className="text-xs text-muted-foreground px-2 py-0.5 rounded bg-muted">
              v{workflow.version}
            </span>
          </div>
          {workflow.description && (
            <p className="text-sm text-muted-foreground mt-1 truncate">{workflow.description}</p>
          )}
          <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
            <span>Category: {workflow.category}</span>
            <span>Executions: {workflow.totalExecutions}</span>
            <span>Success: {workflow.successfulExecutions}</span>
            <span>Failed: {workflow.failedExecutions}</span>
            <span>Updated: {format(new Date(workflow.updatedAt), 'MMM d, yyyy')}</span>
          </div>
        </div>

        <div className="flex items-center gap-1 ml-4">
          <button onClick={onEdit} className="p-2 hover:bg-accent rounded transition-colors" title="Edit">
            <Edit className="w-4 h-4" />
          </button>
          <button onClick={onDuplicate} className="p-2 hover:bg-accent rounded transition-colors" title="Duplicate">
            <Copy className="w-4 h-4" />
          </button>
          {workflow.status === 'published' && (
            <button onClick={onExecute} className="p-2 hover:bg-accent rounded transition-colors text-green-600" title="Execute">
              <Play className="w-4 h-4" />
            </button>
          )}
          <button onClick={onViewExecutions} className="p-2 hover:bg-accent rounded transition-colors" title="View Executions">
            <Eye className="w-4 h-4" />
          </button>
          <div className="relative">
            <button className="p-2 hover:bg-accent rounded transition-colors">
              <MoreVertical className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}