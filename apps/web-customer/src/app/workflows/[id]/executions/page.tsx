'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAppStore } from '@/store';
import { api } from '@/lib/api';
import { WorkflowExecution, WorkflowNodeExecution } from '@/types';
import { ChevronLeft, Play, Pause, RotateCcw, Eye, Download, AlertCircle, CheckCircle, Clock, Zap } from 'lucide-react';
import Link from 'next/link';
import { format, formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import toast from 'react-hot-toast';

interface ExecutionDetail extends WorkflowExecution {
  node_executions?: WorkflowNodeExecution[];
}

export default function WorkflowExecutionsPage() {
  const params = useParams();
  const router = useRouter();
  const { setLoading } = useAppStore();
  const workflowId = params.id as string;
  const [workflow, setWorkflow] = useState<{ id: string; name: string } | null>(null);
  const [executions, setExecutions] = useState<ExecutionDetail[]>([]);
  const [loading, setLocalLoading] = useState(true);
  const [selectedExecution, setSelectedExecution] = useState<ExecutionDetail | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    loadWorkflow();
    loadExecutions();
  }, [workflowId, statusFilter]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      if (selectedExecution && selectedExecution.status === 'running') {
        loadExecution(selectedExecution.id);
      }
      loadExecutions();
    }, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh, selectedExecution]);

  async function loadWorkflow() {
    try {
      const data = await api.getWorkflow(workflowId);
      setWorkflow({ id: data.id, name: data.name });
    } catch (error) {
      toast.error('Failed to load workflow');
    }
  }

  async function loadExecutions() {
    try {
      const data = await api.listExecutions(workflowId, { status: statusFilter, limit: 50 });
      setExecutions(data.items);
    } catch (error) {
      toast.error('Failed to load executions');
    }
  }

  async function loadExecution(executionId: string) {
    try {
      const data = await api.getExecution(workflowId, executionId);
      setExecutions(prev => prev.map(e => e.id === executionId ? data : e));
      if (selectedExecution?.id === executionId) {
        setSelectedExecution(data);
      }
    } catch (error) {
      // Silently fail for auto-refresh
    }
  }

  async function handleExecute() {
    try {
      const result = await api.executeWorkflow(workflowId);
      toast.success('Execution started');
      loadExecutions();
      // Select the new execution
      setTimeout(() => loadExecution(result.executionId), 1000);
    } catch (error) {
      toast.error('Failed to start execution');
    }
  }

  async function handleCancel(executionId: string) {
    try {
      await api.cancelExecution(workflowId, executionId);
      toast.success('Execution cancelled');
      loadExecutions();
    } catch (error) {
      toast.error('Failed to cancel execution');
    }
  }

  const statusColors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-700',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    cancelled: 'bg-gray-100 text-gray-700',
    paused: 'bg-yellow-100 text-yellow-700',
    retrying: 'bg-orange-100 text-orange-700',
  };

  const statusIcons: Record<string, React.ReactNode> = {
    pending: <Clock className="w-4 h-4" />,
    running: <Zap className="w-4 h-4 animate-spin" />,
    completed: <CheckCircle className="w-4 h-4" />,
    failed: <AlertCircle className="w-4 h-4" />,
    cancelled: <Clock className="w-4 h-4" />,
    paused: <Pause className="w-4 h-4" />,
    retrying: <RotateCcw className="w-4 h-4 animate-spin" />,
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-card border-r border-border flex flex-col hidden lg:flex">
        <div className="p-4 border-b border-border">
          <h1 className="text-xl font-bold text-primary">Retention Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">Executions</p>
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
            className="w-full px-3 py-2 rounded-lg text-left transition-colors hover:bg-accent text-foreground"
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
        </nav>

        <div className="p-4 border-t border-border">
          <Link href={`/workflows/${workflowId}/edit`} className="w-full px-3 py-2 bg-primary text-primary-foreground rounded-lg text-center text-sm font-medium hover:bg-primary/90 transition-colors">
            Edit Workflow
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6 sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <Link href="/workflows" className="p-2 hover:bg-accent rounded transition-colors">
              <ChevronLeft className="w-5 h-5" />
            </Link>
            <div>
              <h2 className="text-lg font-semibold">{workflow?.name || 'Workflow'}</h2>
              <p className="text-sm text-muted-foreground">Execution History</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-input rounded-lg bg-background text-sm"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </select>

            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={e => setAutoRefresh(e.target.checked)}
                className="w-4 h-4 rounded border-input text-primary focus:ring-primary"
              />
              Auto-refresh (3s)
            </label>

            <button
              onClick={loadExecutions}
              disabled={loading}
              className="p-2 hover:bg-accent rounded transition-colors"
              title="Refresh"
            >
              <RotateCcw className={cn('w-4 h-4', loading && 'animate-spin')} />
            </button>

            <button onClick={handleExecute} className="px-4 py-2 bg-green-600 text-white rounded-lg flex items-center gap-2 hover:bg-green-700">
              <Play className="w-4 h-4" />
              Execute
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Executions List */}
          <div className="w-96 bg-card border-r border-border flex flex-col overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="font-semibold">Executions ({executions.length})</h3>
            </div>

            <div className="flex-1 overflow-y-auto">
              {loading && (
                <div className="p-4 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary" />
                </div>
              )}

              {!loading && executions.length === 0 && (
                <div className="p-8 text-center text-muted-foreground">
                  <Clock className="w-12 h-12 mx-auto mb-2 opacity-30" />
                  <p>No executions yet</p>
                </div>
              )}

              <div className="divide-y divide-border">
                {executions.map(exec => (
                  <button
                    key={exec.id}
                    onClick={() => setSelectedExecution(exec)}
                    className={cn(
                      'w-full p-4 text-left hover:bg-accent transition-colors border-b border-border/50',
                      selectedExecution?.id === exec.id && 'bg-accent'
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {statusIcons[exec.status]}
                      <span className={`px-2 py-0.5 text-xs rounded-full ${statusColors[exec.status]}`}>
                        {exec.status}
                      </span>
                      {exec.retryCount && exec.retryCount > 0 && (
                        <span className="px-1.5 py-0.5 text-[10px] bg-orange-100 text-orange-700 rounded">
                          Retry {exec.retryCount}
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {exec.triggerType} • {formatDistanceToNow(new Date(exec.queuedAt || ''), { addSuffix: true })}
                    </div>
                    {exec.startedAt && (
                      <div className="text-[11px] text-muted-foreground mt-1">
                        Duration: {exec.durationMs ? `${exec.durationMs}ms` : 'Running...'}
                      </div>
                    )}
                    {exec.error && (
                      <div className="text-[11px] text-red-600 mt-1 truncate">{exec.error}</div>
                    )}
                    {exec.progressPercent && exec.progressPercent > 0 && exec.status === 'running' && (
                      <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all duration-300"
                          style={{ width: `${exec.progressPercent}%` }}
                        />
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Execution Detail */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {selectedExecution ? (
              <ExecutionDetailView
                execution={selectedExecution}
                onClose={() => setSelectedExecution(null)}
                onCancel={() => handleCancel(selectedExecution.id)}
                onRefresh={() => loadExecution(selectedExecution.id)}
              />
            ) : (
              <div className="flex-1 flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Eye className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p className="text-lg">Select an execution to view details</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function ExecutionDetailView({
  execution,
  onClose,
  onCancel,
  onRefresh,
}: {
  execution: ExecutionDetail;
  onClose: () => void;
  onCancel: () => void;
  onRefresh: () => void;
}) {
  const statusColors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-700',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    cancelled: 'bg-gray-100 text-gray-700',
    paused: 'bg-yellow-100 text-yellow-700',
    retrying: 'bg-orange-100 text-orange-700',
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold">Execution Details</h3>
          <span className={`px-2 py-0.5 text-xs rounded-full ${statusColors[execution.status]}`}>
            {execution.status}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={onRefresh} className="p-2 hover:bg-accent rounded transition-colors" title="Refresh">
            <RotateCcw className="w-4 h-4" />
          </button>
          {execution.status === 'running' && (
            <button onClick={onCancel} className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700">
              Cancel
            </button>
          )}
          <button onClick={onClose} className="p-2 hover:bg-accent rounded transition-colors">
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Summary */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-card border border-border rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Status</p>
            <p className="font-semibold text-lg capitalize">{execution.status}</p>
          </div>
          <div className="bg-card border border-border rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Progress</p>
            <p className="font-semibold text-lg">{execution.completedNodes}/{execution.totalNodes} nodes</p>
          </div>
          <div className="bg-card border border-border rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Duration</p>
            <p className="font-semibold text-lg">
              {execution.durationMs ? `${execution.durationMs}ms` : execution.startedAt ? 'Running...' : 'N/A'}
            </p>
          </div>
          <div className="bg-card border border-border rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Revenue Attributed</p>
            <p className="font-semibold text-lg">${(execution.revenueAttributed || 0).toLocaleString()}</p>
          </div>
        </div>

        {/* Timing */}
        <div className="bg-card border border-border rounded-lg p-4">
          <h4 className="font-medium mb-3">Timing</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Queued</p>
              <p>{execution.queuedAt ? format(new Date(execution.queuedAt), 'PPpp') : 'N/A'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Started</p>
              <p>{execution.startedAt ? format(new Date(execution.startedAt), 'PPpp') : 'N/A'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Completed</p>
              <p>{execution.completedAt ? format(new Date(execution.completedAt), 'PPpp') : 'N/A'}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Trigger</p>
              <p className="capitalize">{execution.triggerType} ({execution.triggerSource})</p>
            </div>
          </div>
        </div>

        {/* Error */}
        {execution.error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <h4 className="font-medium text-red-800 mb-2 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Error
            </h4>
            <p className="text-red-700 font-mono text-sm">{execution.error}</p>
            {execution.errorNodeId && (
              <p className="text-red-600 text-sm mt-1">Failed at node: {execution.errorNodeId}</p>
            )}
          </div>
        )}

        {/* Node Executions */}
        {execution.node_executions && execution.node_executions.length > 0 && (
          <div className="bg-card border border-border rounded-lg">
            <div className="p-4 border-b border-border">
              <h4 className="font-medium">Node Executions ({execution.node_executions.length})</h4>
            </div>
            <div className="divide-y divide-border">
              {execution.node_executions.map(nodeExec => (
                <div key={nodeExec.id} className="p-4 hover:bg-accent/50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="px-2 py-0.5 text-xs rounded bg-muted text-muted-foreground">
                        {nodeExec.nodeType}
                      </span>
                      <div>
                        <p className="font-medium">{nodeExec.nodeName || nodeExec.nodeId}</p>
                        <p className="text-sm text-muted-foreground">Attempt {nodeExec.attempt}/{nodeExec.maxAttempts}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 text-xs rounded ${statusColors[nodeExec.status]}`}>
                        {nodeExec.status}
                      </span>
                      {nodeExec.durationMs && (
                        <span className="text-sm text-muted-foreground">{nodeExec.durationMs}ms</span>
                      )}
                    </div>
                  </div>
                  {nodeExec.error && (
                    <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm font-mono">
                      {nodeExec.error}
                    </div>
                  )}
                  {nodeExec.outputData && Object.keys(nodeExec.outputData).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-sm text-muted-foreground cursor-pointer">Output</summary>
                      <pre className="mt-2 text-[11px] bg-muted p-2 rounded overflow-auto max-h-32 font-mono">
                        {JSON.stringify(nodeExec.outputData, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Trigger Data */}
        {(execution.triggerData && Object.keys(execution.triggerData).length > 0) && (
          <div className="bg-card border border-border rounded-lg p-4">
            <h4 className="font-medium mb-2">Trigger Data</h4>
            <pre className="text-[11px] bg-muted p-3 rounded overflow-auto max-h-48 font-mono">
              {JSON.stringify(execution.triggerData, null, 2)}
            </pre>
          </div>
        )}

        {/* Output */}
        {execution.output && Object.keys(execution.output).length > 0 && (
          <div className="bg-card border border-border rounded-lg p-4">
            <h4 className="font-medium mb-2">Output</h4>
            <pre className="text-[11px] bg-muted p-3 rounded overflow-auto max-h-48 font-mono">
              {JSON.stringify(execution.output, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}