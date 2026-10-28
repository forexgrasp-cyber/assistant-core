'use client';

import { useState } from 'react';
import { Node, Edge, useReactFlow } from 'react-flow-renderer';
import {
  Zap,
  Mail,
  MessageSquare,
  Smartphone,
  Database,
  BarChart2,
  Filter,
  Clock,
  GitBranch,
  Repeat,
  Webhook,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Send,
  Users,
  DollarSign,
  ShoppingCart,
  RefreshCw,
  Cog,
  Plus,
  Minus,
  Copy,
  Trash2,
  Settings,
  Play,
  Pause,
  Save,
  Download,
  Upload,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NodePaletteItem {
  type: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  service: 'analytics' | 'engagement' | 'ecommerce' | 'reporting' | 'custom';
  action: string;
  configSchema: Record<string, any>;
}

const NODE_PALETTE: NodePaletteItem[] = [
  {
    type: 'analytics_query',
    label: 'Query Analytics',
    description: 'Run SQL query or fetch metrics from analytics engine',
    icon: <BarChart2 className="w-5 h-5" />,
    color: '#3b82f6',
    service: 'analytics',
    action: 'query',
    configSchema: {
      query: { type: 'string', label: 'SQL Query', required: true },
      params: { type: 'object', label: 'Parameters' },
    },
  },
  {
    type: 'analytics_cohort',
    label: 'Cohort Analysis',
    description: 'Analyze customer cohorts and retention',
    icon: <Users className="w-5 h-5" />,
    color: '#3b82f6',
    service: 'analytics',
    action: 'cohort',
    configSchema: {
      months: { type: 'number', label: 'Months Back', default: 12 },
      metric: { type: 'select', options: ['retention', 'revenue', 'orders'], label: 'Metric' },
    },
  },
  {
    type: 'analytics_rfm',
    label: 'RFM Segmentation',
    description: 'Segment customers by Recency, Frequency, Monetary',
    icon: <Filter className="w-5 h-5" />,
    color: '#3b82f6',
    service: 'analytics',
    action: 'rfm',
    configSchema: {},
  },
  {
    type: 'analytics_attribution',
    label: 'Attribution Analysis',
    description: 'Calculate revenue attribution by channel',
    icon: <DollarSign className="w-5 h-5" />,
    color: '#3b82f6',
    service: 'analytics',
    action: 'attribution',
    configSchema: {
      days: { type: 'number', label: 'Lookback Days', default: 30 },
    },
  },
  {
    type: 'analytics_predictive',
    label: 'Predictive Scoring',
    description: 'Get churn risk and LTV predictions',
    icon: <Zap className="w-5 h-5" />,
    color: '#3b82f6',
    service: 'analytics',
    action: 'predictive',
    configSchema: {},
  },
  {
    type: 'analytics_anomaly',
    label: 'Anomaly Detection',
    description: 'Detect anomalies in metrics',
    icon: <AlertTriangle className="w-5 h-5" />,
    color: '#3b82f6',
    service: 'analytics',
    action: 'anomaly',
    configSchema: {
      metric: { type: 'string', label: 'Metric Name' },
      sensitivity: { type: 'number', label: 'Sensitivity', default: 2 },
    },
  },
  {
    type: 'engagement_email',
    label: 'Send Email',
    description: 'Send transactional or marketing email',
    icon: <Mail className="w-5 h-5" />,
    color: '#10b981',
    service: 'engagement',
    action: 'send_email',
    configSchema: {
      template_id: { type: 'string', label: 'Template ID', required: true },
      to: { type: 'string', label: 'Recipient Field', required: true },
      subject: { type: 'string', label: 'Subject' },
      data: { type: 'object', label: 'Template Data' },
    },
  },
  {
    type: 'engagement_sms',
    label: 'Send SMS',
    description: 'Send SMS message',
    icon: <MessageSquare className="w-5 h-5" />,
    color: '#10b981',
    service: 'engagement',
    action: 'send_sms',
    configSchema: {
      template_id: { type: 'string', label: 'Template ID', required: true },
      to: { type: 'string', label: 'Phone Field', required: true },
      body: { type: 'string', label: 'Message Body' },
    },
  },
  {
    type: 'engagement_push',
    label: 'Send Push',
    description: 'Send push notification',
    icon: <Smartphone className="w-5 h-5" />,
    color: '#10b981',
    service: 'engagement',
    action: 'send_push',
    configSchema: {
      template_id: { type: 'string', label: 'Template ID', required: true },
      user_id: { type: 'string', label: 'User ID Field', required: true },
      title: { type: 'string', label: 'Title' },
      body: { type: 'string', label: 'Body' },
      data: { type: 'object', label: 'Payload Data' },
    },
  },
  {
    type: 'ecommerce_order',
    label: 'Create Order',
    description: 'Create or update order in ecommerce system',
    icon: <ShoppingCart className="w-5 h-5" />,
    color: '#f59e0b',
    service: 'ecommerce',
    action: 'create_order',
    configSchema: {
      customer_id: { type: 'string', label: 'Customer ID', required: true },
      items: { type: 'array', label: 'Order Items', required: true },
      metadata: { type: 'object', label: 'Metadata' },
    },
  },
  {
    type: 'ecommerce_customer',
    label: 'Upsert Customer',
    description: 'Create or update customer profile',
    icon: <Users className="w-5 h-5" />,
    color: '#f59e0b',
    service: 'ecommerce',
    action: 'upsert_customer',
    configSchema: {
      email: { type: 'string', label: 'Email', required: true },
      first_name: { type: 'string', label: 'First Name' },
      last_name: { type: 'string', label: 'Last Name' },
      phone: { type: 'string', label: 'Phone' },
      tags: { type: 'array', label: 'Tags' },
      metadata: { type: 'object', label: 'Metadata' },
    },
  },
  {
    type: 'reporting_generate',
    label: 'Generate Report',
    description: 'Generate and export a report',
    icon: <Database className="w-5 h-5" />,
    color: '#8b5cf6',
    service: 'reporting',
    action: 'generate_report',
    configSchema: {
      report_id: { type: 'string', label: 'Report ID', required: true },
      format: { type: 'select', options: ['pdf', 'html', 'csv', 'json', 'xlsx'], label: 'Format' },
      parameters: { type: 'object', label: 'Parameters' },
    },
  },
  {
    type: 'reporting_schedule',
    label: 'Schedule Report',
    description: 'Schedule a report for recurring delivery',
    icon: <Clock className="w-5 h-5" />,
    color: '#8b5cf6',
    service: 'reporting',
    action: 'schedule_report',
    configSchema: {
      report_id: { type: 'string', label: 'Report ID', required: true },
      cron: { type: 'string', label: 'Cron Expression', required: true },
      recipients: { type: 'array', label: 'Recipients' },
    },
  },
  {
    type: 'condition',
    label: 'Condition',
    description: 'Branch workflow based on condition',
    icon: <GitBranch className="w-5 h-5" />,
    color: '#ef4444',
    service: 'custom',
    action: 'condition',
    configSchema: {
      field: { type: 'string', label: 'Field', required: true },
      operator: { type: 'select', options: ['eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'contains', 'in'], label: 'Operator', required: true },
      value: { type: 'any', label: 'Value', required: true },
    },
  },
  {
    type: 'delay',
    label: 'Delay',
    description: 'Wait for specified duration',
    icon: <Clock className="w-5 h-5" />,
    color: '#6b7280',
    service: 'custom',
    action: 'delay',
    configSchema: {
      seconds: { type: 'number', label: 'Seconds', required: true },
    },
  },
  {
    type: 'loop',
    label: 'Loop',
    description: 'Iterate over array and execute sub-workflow',
    icon: <Repeat className="w-5 h-5" />,
    color: '#6b7280',
    service: 'custom',
    action: 'loop',
    configSchema: {
      items_field: { type: 'string', label: 'Items Field', required: true },
      sub_workflow_id: { type: 'string', label: 'Sub-workflow ID', required: true },
    },
  },
  {
    type: 'webhook_call',
    label: 'Call Webhook',
    description: 'Make HTTP request to external endpoint',
    icon: <Webhook className="w-5 h-5" />,
    color: '#ec4899',
    service: 'custom',
    action: 'webhook',
    configSchema: {
      url: { type: 'string', label: 'URL', required: true },
      method: { type: 'select', options: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], label: 'Method', default: 'POST' },
      headers: { type: 'object', label: 'Headers' },
      body: { type: 'object', label: 'Request Body' },
    },
  },
  {
    type: 'transform_data',
    label: 'Transform Data',
    description: 'Transform/manipulate data with JavaScript',
    icon: <Cog className="w-5 h-5" />,
    color: '#6366f1',
    service: 'custom',
    action: 'transform',
    configSchema: {
      script: { type: 'string', label: 'JavaScript Code', required: true },
    },
  },
];

interface NodePaletteProps {
  onAddNode: (nodeType: string, position: { x: number; y: number }) => void;
}

export function NodePalette({ onAddNode }: NodePaletteProps) {
  const [search, setSearch] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    analytics: true,
    engagement: true,
    ecommerce: true,
    reporting: true,
    custom: true,
  });

  const categories = [
    { key: 'analytics', label: 'Analytics', icon: <BarChart2 className="w-4 h-4" /> },
    { key: 'engagement', label: 'Engagement', icon: <Mail className="w-4 h-4" /> },
    { key: 'ecommerce', label: 'E-commerce', icon: <ShoppingCart className="w-4 h-4" /> },
    { key: 'reporting', label: 'Reporting', icon: <Database className="w-4 h-4" /> },
    { key: 'custom', label: 'Control Flow', icon: <Cog className="w-4 h-4" /> },
  ];

  const filteredPalette = NODE_PALETTE.filter(node =>
    node.label.toLowerCase().includes(search.toLowerCase()) ||
    node.description.toLowerCase().includes(search.toLowerCase()) ||
    node.action.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="w-72 h-full bg-card border-r border-border flex flex-col">
      <div className="p-3 border-b border-border">
        <h3 className="font-semibold text-sm">Node Palette</h3>
        <input
          type="text"
          placeholder="Search nodes..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="mt-2 w-full px-2 py-1 text-xs border border-input rounded bg-background"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-3">
        {categories.map(category => {
          const categoryNodes = filteredPalette.filter(n => n.service === category.key);
          if (categoryNodes.length === 0) return null;

          const isExpanded = expandedCategories[category.key];

          return (
            <div key={category.key} className="space-y-1">
              <button
                onClick={() => setExpandedCategories(prev => ({ ...prev, [category.key]: !prev[category.key] }))}
                className="w-full flex items-center gap-2 px-2 py-1 text-xs font-medium text-muted-foreground hover:text-foreground rounded"
              >
                <span className={cn('transition-transform', isExpanded ? 'rotate-90' : '')}>▶</span>
                {category.icon}
                <span>{category.label}</span>
                <span className="ml-auto text-xs text-muted-foreground">{categoryNodes.length}</span>
              </button>

              {isExpanded && (
                <div className="space-y-1 ml-6">
                  {categoryNodes.map(node => (
                    <button
                      key={node.type}
                      onClick={() => onAddNode(node.type, { x: 100, y: 100 })}
                      className="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-left hover:bg-accent rounded transition-colors group"
                      style={{ borderLeft: `3px solid ${node.color}` }}
                    >
                      <span
                        style={{ color: node.color }}
                        className="flex-shrink-0"
                      >
                        {node.icon}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">{node.label}</div>
                        <div className="text-[10px] text-muted-foreground truncate">{node.description}</div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}