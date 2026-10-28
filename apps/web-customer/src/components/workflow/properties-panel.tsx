'use client';

import { useState, useEffect } from 'react';
import { Node, Edge } from 'react-flow-renderer';
import { 
  X, 
  Save, 
  SlidersHorizontal, 
  Trash2, 
  Copy, 
  Play,
  BarChart2,
  Users,
  Filter,
  DollarSign,
  Zap,
  AlertTriangle,
  Mail,
  MessageSquare,
  Smartphone,
  ShoppingCart,
  Database,
  Clock,
  GitBranch,
  Repeat,
  Webhook,
  Cog
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkflowNodeData, WorkflowNode } from '@/types';

interface NodeConfigField {
  key: string;
  label: string;
  type: 'string' | 'number' | 'boolean' | 'select' | 'object' | 'array' | 'code';
  required?: boolean;
  default?: any;
  options?: Array<{ value: any; label: string }>;
  description?: string;
}

const NODE_CONFIG_SCHEMAS: Record<string, NodeConfigField[]> = {
  analytics_query: [
    { key: 'query', label: 'SQL Query', type: 'code', required: true, description: 'SQL query to execute' },
    { key: 'params', label: 'Parameters', type: 'object', description: 'Query parameters as JSON object' },
  ],
  analytics_cohort: [
    { key: 'months', label: 'Months Back', type: 'number', default: 12, required: true },
    { key: 'metric', label: 'Metric', type: 'select', options: [
      { value: 'retention', label: 'Retention Rate' },
      { value: 'revenue', label: 'Revenue per Customer' },
      { value: 'orders', label: 'Orders per Customer' },
    ], required: true },
  ],
  analytics_rfm: [],
  analytics_attribution: [
    { key: 'days', label: 'Lookback Days', type: 'number', default: 30, required: true },
  ],
  analytics_predictive: [],
  analytics_anomaly: [
    { key: 'metric', label: 'Metric Name', type: 'string', required: true },
    { key: 'sensitivity', label: 'Sensitivity (std deviations)', type: 'number', default: 2 },
  ],
  engagement_send_email: [
    { key: 'template_id', label: 'Template ID', type: 'string', required: true },
    { key: 'to', label: 'Recipient Field', type: 'string', required: true, description: 'Field name in context containing email' },
    { key: 'subject', label: 'Subject', type: 'string' },
    { key: 'data', label: 'Template Data', type: 'object', description: 'Additional data for template' },
  ],
  engagement_send_sms: [
    { key: 'template_id', label: 'Template ID', type: 'string', required: true },
    { key: 'to', label: 'Phone Field', type: 'string', required: true, description: 'Field name in context containing phone' },
    { key: 'body', label: 'Message Body', type: 'string', required: true },
  ],
  engagement_send_push: [
    { key: 'template_id', label: 'Template ID', type: 'string', required: true },
    { key: 'user_id', label: 'User ID Field', type: 'string', required: true },
    { key: 'title', label: 'Title', type: 'string' },
    { key: 'body', label: 'Body', type: 'string' },
    { key: 'data', label: 'Payload Data', type: 'object' },
  ],
  ecommerce_create_order: [
    { key: 'customer_id', label: 'Customer ID Field', type: 'string', required: true },
    { key: 'items', label: 'Order Items', type: 'array', required: true, description: 'Array of {product_id, quantity, price}' },
    { key: 'metadata', label: 'Metadata', type: 'object' },
  ],
  ecommerce_upsert_customer: [
    { key: 'email', label: 'Email Field', type: 'string', required: true },
    { key: 'first_name', label: 'First Name Field', type: 'string' },
    { key: 'last_name', label: 'Last Name Field', type: 'string' },
    { key: 'phone', label: 'Phone Field', type: 'string' },
    { key: 'tags', label: 'Tags', type: 'array' },
    { key: 'metadata', label: 'Metadata', type: 'object' },
  ],
  reporting_generate_report: [
    { key: 'report_id', label: 'Report ID', type: 'string', required: true },
    { key: 'format', label: 'Format', type: 'select', options: [
      { value: 'pdf', label: 'PDF' },
      { value: 'html', label: 'HTML' },
      { value: 'csv', label: 'CSV' },
      { value: 'json', label: 'JSON' },
      { value: 'xlsx', label: 'Excel' },
    ], required: true },
    { key: 'parameters', label: 'Parameters', type: 'object' },
  ],
  reporting_schedule_report: [
    { key: 'report_id', label: 'Report ID', type: 'string', required: true },
    { key: 'cron', label: 'Cron Expression', type: 'string', required: true, description: 'e.g., 0 9 * * MON' },
    { key: 'recipients', label: 'Recipients', type: 'array', description: 'Email addresses' },
  ],
  condition: [
    { key: 'field', label: 'Field', type: 'string', required: true, description: 'Field path in context (e.g., output.revenue)' },
    { key: 'operator', label: 'Operator', type: 'select', options: [
      { value: 'eq', label: 'Equals' },
      { value: 'neq', label: 'Not Equals' },
      { value: 'gt', label: 'Greater Than' },
      { value: 'gte', label: 'Greater Than or Equal' },
      { value: 'lt', label: 'Less Than' },
      { value: 'lte', label: 'Less Than or Equal' },
      { value: 'contains', label: 'Contains' },
      { value: 'in', label: 'In Array' },
    ], required: true },
    { key: 'value', label: 'Value', type: 'string', required: true },
  ],
  delay: [
    { key: 'seconds', label: 'Seconds', type: 'number', required: true, default: 60 },
  ],
  loop: [
    { key: 'items_field', label: 'Items Field', type: 'string', required: true, description: 'Field path to array in context' },
    { key: 'sub_workflow_id', label: 'Sub-workflow ID', type: 'string', required: true },
  ],
  webhook_call: [
    { key: 'url', label: 'URL', type: 'string', required: true },
    { key: 'method', label: 'Method', type: 'select', options: [
      { value: 'GET', label: 'GET' },
      { value: 'POST', label: 'POST' },
      { value: 'PUT', label: 'PUT' },
      { value: 'PATCH', label: 'PATCH' },
      { value: 'DELETE', label: 'DELETE' },
    ], default: 'POST' },
    { key: 'headers', label: 'Headers', type: 'object' },
    { key: 'body', label: 'Request Body', type: 'object' },
  ],
  transform_data: [
    { key: 'script', label: 'JavaScript Code', type: 'code', required: true, description: 'Return transformed data. Context available as `ctx`' },
  ],
};

interface PropertiesPanelProps {
  node: Node<WorkflowNodeData> | null;
  onUpdate: (nodeId: string, data: Partial<WorkflowNodeData>) => void;
  onDelete: (nodeId: string) => void;
  onDuplicate: (node: Node<WorkflowNodeData>) => void;
  onTestRun: (node: Node<WorkflowNodeData>) => void;
}

export function PropertiesPanel({ node, onUpdate, onDelete, onDuplicate, onTestRun }: PropertiesPanelProps) {
  const [config, setConfig] = useState<Record<string, any>>({});
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (node?.data?.config) {
      setConfig({ ...node.data.config });
    } else {
      setConfig({});
    }
  }, [node]);

  if (!node) {
    return (
      <div className="w-80 h-full bg-card border-l border-border flex flex-col">
        <div className="p-4 border-b border-border">
          <h3 className="font-semibold">Node Properties</h3>
          <p className="text-sm text-muted-foreground mt-1">Select a node to configure</p>
        </div>
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          No node selected
        </div>
      </div>
    );
  }

  const schema = NODE_CONFIG_SCHEMAS[node.data.action || ''] || [];
  const color = node.data.color || getServiceColor(node.data.service || 'custom');

  const handleChange = (key: string, value: any) => {
    setConfig(prev => ({ ...prev, [key]: value }));
    onUpdate(node.id, { config: { ...config, [key]: value } });
  };

  const renderField = (field: NodeConfigField) => {
    const value = config[field.key] ?? field.default ?? '';
    const id = `config-${node.id}-${field.key}`;

    switch (field.type) {
      case 'string':
        return (
          <div key={field.key} className="space-y-1">
            <label htmlFor={id} className="text-xs font-medium">{field.label}{field.required && <span className="text-red-500">*</span>}</label>
            <input
              id={id}
              type="text"
              value={value}
              onChange={e => handleChange(field.key, e.target.value)}
              className="w-full px-2 py-1.5 text-sm border border-input rounded bg-background"
              placeholder={field.description}
            />
            {field.description && <p className="text-[10px] text-muted-foreground">{field.description}</p>}
          </div>
        );
      case 'number':
        return (
          <div key={field.key} className="space-y-1">
            <label htmlFor={id} className="text-xs font-medium">{field.label}{field.required && <span className="text-red-500">*</span>}</label>
            <input
              id={id}
              type="number"
              value={value}
              onChange={e => handleChange(field.key, parseFloat(e.target.value) || 0)}
              className="w-full px-2 py-1.5 text-sm border border-input rounded bg-background"
            />
            {field.description && <p className="text-[10px] text-muted-foreground">{field.description}</p>}
          </div>
        );
      case 'boolean':
        return (
          <div key={field.key} className="space-y-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={value}
                onChange={e => handleChange(field.key, e.target.checked)}
                className="w-4 h-4 rounded border-input text-primary focus:ring-primary"
              />
              <span className="text-xs font-medium">{field.label}</span>
            </label>
            {field.description && <p className="text-[10px] text-muted-foreground ml-6">{field.description}</p>}
          </div>
        );
      case 'select':
        return (
          <div key={field.key} className="space-y-1">
            <label htmlFor={id} className="text-xs font-medium">{field.label}{field.required && <span className="text-red-500">*</span>}</label>
            <select
              id={id}
              value={value}
              onChange={e => handleChange(field.key, e.target.value)}
              className="w-full px-2 py-1.5 text-sm border border-input rounded bg-background"
            >
              {field.options?.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            {field.description && <p className="text-[10px] text-muted-foreground">{field.description}</p>}
          </div>
        );
      case 'object':
        return (
          <div key={field.key} className="space-y-1">
            <label htmlFor={id} className="text-xs font-medium">{field.label}</label>
            <textarea
              id={id}
              value={typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
              onChange={e => {
                try {
                  handleChange(field.key, JSON.parse(e.target.value));
                } catch {
                  handleChange(field.key, e.target.value);
                }
              }}
              className="w-full px-2 py-1.5 text-sm border border-input rounded bg-background font-mono text-[11px]"
              rows={4}
              placeholder="JSON object"
            />
            {field.description && <p className="text-[10px] text-muted-foreground">{field.description}</p>}
          </div>
        );
      case 'array':
        return (
          <div key={field.key} className="space-y-1">
            <label htmlFor={id} className="text-xs font-medium">{field.label}</label>
            <textarea
              id={id}
              value={typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
              onChange={e => {
                try {
                  handleChange(field.key, JSON.parse(e.target.value));
                } catch {
                  handleChange(field.key, e.target.value);
                }
              }}
              className="w-full px-2 py-1.5 text-sm border border-input rounded bg-background font-mono text-[11px]"
              rows={4}
              placeholder="JSON array"
            />
            {field.description && <p className="text-[10px] text-muted-foreground">{field.description}</p>}
          </div>
        );
      case 'code':
        return (
          <div key={field.key} className="space-y-1">
            <label htmlFor={id} className="text-xs font-medium">{field.label}{field.required && <span className="text-red-500">*</span>}</label>
            <textarea
              id={id}
              value={value}
              onChange={e => handleChange(field.key, e.target.value)}
              className="w-full px-2 py-1.5 text-sm border border-input rounded bg-background font-mono text-[11px]"
              rows={8}
              placeholder={field.description}
              spellCheck={false}
            />
            {field.description && <p className="text-[10px] text-muted-foreground">{field.description}</p>}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="w-80 h-full bg-card border-l border-border flex flex-col">
      <div className="p-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white" style={{ background: color }}>
            {getServiceIcon(node.data.service || 'custom', node.data.action || '')}
          </div>
          <div>
            <h3 className="font-semibold text-sm truncate">{node.data.label}</h3>
            <p className="text-[10px] text-muted-foreground capitalize">{node.data.service} / {node.data.action}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => onTestRun(node)} className="p-1.5 hover:bg-accent rounded transition-colors" title="Test Run">
            <Play className="w-4 h-4" />
          </button>
          <button onClick={() => onDuplicate(node)} className="p-1.5 hover:bg-accent rounded transition-colors" title="Duplicate">
            <Copy className="w-4 h-4" />
          </button>
          <button onClick={() => onDelete(node.id)} className="p-1.5 hover:bg-accent rounded transition-colors text-red-500" title="Delete">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        <div className="space-y-2">
          <label className="text-xs font-medium">Label</label>
          <input
            type="text"
            value={node.data.label}
            onChange={e => onUpdate(node.id, { label: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-input rounded bg-background"
          />
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium">Description</label>
          <textarea
            value={node.data.description || ''}
            onChange={e => onUpdate(node.id, { description: e.target.value })}
            className="w-full px-2 py-1.5 text-sm border border-input rounded bg-background"
            rows={2}
            placeholder="Optional description"
          />
        </div>

        {schema.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Configuration</h4>
            {schema.map(field => renderField(field))}
          </div>
        )}

        {schema.length === 0 && (
          <div className="text-center py-8 text-muted-foreground text-sm">
            <SlidersHorizontal className="w-8 h-8 mx-auto mb-2 opacity-30" />
            <p>No configuration required for this node type</p>
          </div>
        )}
      </div>
    </div>
  );
}

function getServiceIcon(service: string, action: string) {
  const icons: Record<string, Record<string, React.ReactNode>> = {
    analytics: { query: <BarChart2 className="w-4 h-4" />, cohort: <Users className="w-4 h-4" />, rfm: <Filter className="w-4 h-4" />, attribution: <DollarSign className="w-4 h-4" />, predictive: <Zap className="w-4 h-4" />, anomaly: <AlertTriangle className="w-4 h-4" /> },
    engagement: { send_email: <Mail className="w-4 h-4" />, send_sms: <MessageSquare className="w-4 h-4" />, send_push: <Smartphone className="w-4 h-4" /> },
    ecommerce: { create_order: <ShoppingCart className="w-4 h-4" />, upsert_customer: <Users className="w-4 h-4" /> },
    reporting: { generate_report: <Database className="w-4 h-4" />, schedule_report: <Clock className="w-4 h-4" /> },
    custom: { condition: <GitBranch className="w-4 h-4" />, delay: <Clock className="w-4 h-4" />, loop: <Repeat className="w-4 h-4" />, webhook: <Webhook className="w-4 h-4" />, transform: <Cog className="w-4 h-4" /> },
  };
  return icons[service]?.[action] || <Cog className="w-4 h-4" />;
}

function getServiceColor(service: string) {
  const colors: Record<string, string> = {
    analytics: '#3b82f6', engagement: '#10b981', ecommerce: '#f59e0b', reporting: '#8b5cf6', custom: '#6b7280',
  };
  return colors[service] || '#6b7280';
}