'use client';

import { Handle, Position, NodeProps } from 'react-flow-renderer';
import { cn } from '@/lib/utils';
import {
  BarChart2, Mail, MessageSquare, Smartphone, Database,
  Filter, Users, DollarSign, Zap, AlertTriangle,
  ShoppingCart, Clock, GitBranch, Repeat, Webhook, Cog,
  CheckCircle, XCircle, Loader2, Zap as ZapIcon
} from 'lucide-react';

interface WorkflowNodeData {
  label: string;
  description?: string;
  config?: Record<string, any>;
  service?: 'analytics' | 'engagement' | 'ecommerce' | 'reporting' | 'custom';
  action?: string;
  icon?: string;
  color?: string;
  status?: 'idle' | 'running' | 'completed' | 'failed' | 'skipped';
  error?: string;
}

function getServiceIcon(service: string, action: string) {
  const icons: Record<string, Record<string, React.ReactNode>> = {
    analytics: {
      query: <BarChart2 className="w-4 h-4" />,
      cohort: <Users className="w-4 h-4" />,
      rfm: <Filter className="w-4 h-4" />,
      attribution: <DollarSign className="w-4 h-4" />,
      predictive: <Zap className="w-4 h-4" />,
      anomaly: <AlertTriangle className="w-4 h-4" />,
    },
    engagement: {
      send_email: <Mail className="w-4 h-4" />,
      send_sms: <MessageSquare className="w-4 h-4" />,
      send_push: <Smartphone className="w-4 h-4" />,
    },
    ecommerce: {
      create_order: <ShoppingCart className="w-4 h-4" />,
      upsert_customer: <Users className="w-4 h-4" />,
    },
    reporting: {
      generate_report: <Database className="w-4 h-4" />,
      schedule_report: <Clock className="w-4 h-4" />,
    },
    custom: {
      condition: <GitBranch className="w-4 h-4" />,
      delay: <Clock className="w-4 h-4" />,
      loop: <Repeat className="w-4 h-4" />,
      webhook: <Webhook className="w-4 h-4" />,
      transform: <Cog className="w-4 h-4" />,
    },
  };
  return icons[service]?.[action] || <Cog className="w-4 h-4" />;
}

function getServiceColor(service: string) {
  const colors: Record<string, string> = {
    analytics: '#3b82f6',
    engagement: '#10b981',
    ecommerce: '#f59e0b',
    reporting: '#8b5cf6',
    custom: '#6b7280',
  };
  return colors[service] || '#6b7280';
}

function getStatusIndicator(status?: string) {
  switch (status) {
    case 'running':
      return <Loader2 className="w-3 h-3 animate-spin text-blue-500" />;
    case 'completed':
      return <CheckCircle className="w-3 h-3 text-green-500" />;
    case 'failed':
      return <XCircle className="w-3 h-3 text-red-500" />;
    case 'skipped':
      return <span className="w-3 h-3 text-gray-400">⏭</span>;
    default:
      return null;
  }
}

export function WorkflowActionNode(props: NodeProps<WorkflowNodeData>) {
  const { data, selected, id } = props;
  const color = data.color || getServiceColor(data.service || 'custom');
  const statusIndicator = getStatusIndicator(data.status);
  const isRunning = data.status === 'running';

  return (
    <div
      className={cn(
        'workflow-node min-w-[200px] max-w-[280px] rounded-lg border-2 bg-card',
        'shadow-md transition-all duration-200',
        selected && 'ring-2 ring-primary ring-offset-2',
        isRunning && 'ring-2 ring-blue-500 ring-offset-2 animate-pulse'
      )}
      style={{ borderColor: color }}
    >
      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-transparent" style={{ background: color }} />
      
      <div className="p-3">
        <div className="flex items-start gap-2">
          <div
            className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-white"
            style={{ background: color }}
          >
            {getServiceIcon(data.service || 'custom', data.action || '')}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h4 className="font-medium text-sm truncate">{data.label}</h4>
              {statusIndicator}
            </div>
            {data.description && (
              <p className="text-[11px] text-muted-foreground mt-1 truncate">{data.description}</p>
            )}
            <div className="flex items-center gap-1 mt-2 text-[10px] text-muted-foreground">
              <span className="px-1.5 py-0.5 rounded bg-muted capitalize">{data.service}</span>
              <span className="px-1.5 py-0.5 rounded bg-muted">{data.action}</span>
            </div>
          </div>
        </div>

        {data.error && (
          <div className="mt-2 p-2 text-[10px] text-red-600 bg-red-50 rounded border border-red-200">
            {data.error}
          </div>
        )}

        {data.config && Object.keys(data.config).length > 0 && (
          <details className="mt-2">
            <summary className="text-[10px] text-muted-foreground cursor-pointer">Config</summary>
            <pre className="mt-1 text-[10px] bg-muted p-2 rounded overflow-auto max-h-24">
              {JSON.stringify(data.config, null, 2)}
            </pre>
          </details>
        )}
      </div>

      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-transparent" style={{ background: color }} />
    </div>
  );
}

export function WorkflowTriggerNode(props: NodeProps<WorkflowNodeData>) {
  const { data, selected } = props;
  const color = data.color || '#3b82f6';

  return (
    <div
      className={cn(
        'workflow-node min-w-[180px] max-w-[240px] rounded-lg border-2 bg-card',
        'shadow-md transition-all duration-200',
        selected && 'ring-2 ring-primary ring-offset-2'
      )}
      style={{ borderColor: color }}
    >
      <div className="p-3">
        <div className="flex items-center gap-2">
          <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-white" style={{ background: color }}>
            <ZapIcon className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-sm truncate">{data.label}</h4>
            <p className="text-[11px] text-muted-foreground truncate">{data.description || 'Workflow trigger'}</p>
            <div className="mt-2 text-[10px] text-muted-foreground capitalize">{data.action || 'trigger'}</div>
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-transparent" style={{ background: color }} />
    </div>
  );
}

export function WorkflowConditionNode(props: NodeProps<WorkflowNodeData>) {
  const { data, selected } = props;
  const color = data.color || '#ef4444';
  const statusIndicator = getStatusIndicator(data.status);
  const isRunning = data.status === 'running';

  return (
    <div
      className={cn(
        'workflow-node min-w-[200px] max-w-[260px] rounded-lg border-2 bg-card',
        'shadow-md transition-all duration-200',
        selected && 'ring-2 ring-primary ring-offset-2',
        isRunning && 'ring-2 ring-blue-500 ring-offset-2 animate-pulse'
      )}
      style={{ borderColor: color }}
    >
      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-transparent" style={{ background: color }} />
      
      <div className="p-3">
        <div className="flex items-start gap-2">
          <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-white" style={{ background: color }}>
            <GitBranch className="w-4 h-4" />
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h4 className="font-medium text-sm truncate">{data.label}</h4>
              {statusIndicator}
            </div>
            {data.description && (
              <p className="text-[11px] text-muted-foreground mt-1 truncate">{data.description}</p>
            )}
            {data.config && (
              <div className="mt-2 text-[10px] text-muted-foreground font-mono">
                {data.config.field} {data.config.operator} {JSON.stringify(data.config.value)}
              </div>
            )}
          </div>
        </div>
      </div>

      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-transparent" style={{ background: color }} />
    </div>
  );
}

export function WorkflowDelayNode(props: NodeProps<WorkflowNodeData>) {
  const { data, selected } = props;
  const color = data.color || '#6b7280';
  const statusIndicator = getStatusIndicator(data.status);
  const isRunning = data.status === 'running';

  return (
    <div
      className={cn(
        'workflow-node min-w-[160px] max-w-[220px] rounded-lg border-2 bg-card',
        'shadow-md transition-all duration-200',
        selected && 'ring-2 ring-primary ring-offset-2',
        isRunning && 'ring-2 ring-blue-500 ring-offset-2 animate-pulse'
      )}
      style={{ borderColor: color }}
    >
      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-transparent" style={{ background: color }} />
      
      <div className="p-3">
        <div className="flex items-center gap-2">
          <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-white" style={{ background: color }}>
            <Clock className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-sm truncate">{data.label}</h4>
            {data.config?.seconds && (
              <p className="text-[11px] text-muted-foreground mt-1">
                Wait {data.config.seconds}s
              </p>
            )}
            {statusIndicator && (
              <div className="mt-2 flex justify-end">{statusIndicator}</div>
            )}
          </div>
        </div>
      </div>

      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-transparent" style={{ background: color }} />
    </div>
  );
}

export const nodeTypes = {
  action: WorkflowActionNode,
  trigger: WorkflowTriggerNode,
  condition: WorkflowConditionNode,
  delay: WorkflowDelayNode,
  default: WorkflowActionNode,
};