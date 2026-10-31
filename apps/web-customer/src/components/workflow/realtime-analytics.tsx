'use client';

import { useState, useEffect } from 'react';
import { Zap, Mail, Bell } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkflowTrigger } from '@/types';

interface TriggersPanelProps {
  triggers: WorkflowTrigger[];
  onChange: (triggers: WorkflowTrigger[]) => void;
}

export function TriggersPanel({ triggers, onChange }: TriggersPanelProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTrigger, setNewTrigger] = useState<Partial<WorkflowTrigger>>({
    type: 'schedule',
    config: {},
  });

  const triggerTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
    schedule: Calendar,
    event: Zap,
    webhook: Mail,
    manual: Bell,
  };

  const handleAddTrigger = () => {
    const trigger: WorkflowTrigger = {
      id: `trigger-${Date.now()}`,
      name: newTrigger.name || 'New Trigger',
      type: newTrigger.type || 'schedule',
      config: newTrigger.config || {},
      isActive: true,
    };
    onChange([...triggers, trigger]);
    setShowAddModal(false);
    setNewTrigger({ type: 'schedule', config: {} });
  };

  const handleUpdateTrigger = (id: string, updates: Partial<WorkflowTrigger>) => {
    onChange(triggers.map((t) => (t.id === id ? { ...t, ...updates } : t)));
  };

  const handleDeleteTrigger = (id: string) => {
    onChange(triggers.filter((t) => t.id !== id));
  };

  const handleConfigChange = (id: string, key: string, value: any) => {
    const trigger = triggers.find((t) => t.id === id);
    if (trigger) {
      handleUpdateTrigger(id, {
        config: { ...trigger.config, [key]: value },
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Triggers</h3>
        <button
          onClick={() => setShowAddModal(true)}
          className="p-2 hover:bg-accent rounded transition-colors"
          title="Add Trigger"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {triggers.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p className="mb-2">No triggers configured</p>
          <p className="text-sm">Click + to add a trigger</p>
        </div>
      ) : (
        <div className="space-y-3">
          {triggers.map(trigger => {
            const Icon = triggerTypeIcons[trigger.type] || Zap;
            return (
              <div
                key={trigger.id}
                className={cn(
                  'border rounded-lg p-3 transition-colors',
                  trigger.isActive ? 'border-border bg-card' : 'border-border/50 bg-muted/50 opacity-70'
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="p-1.5 bg-primary/10 rounded">
                    <Icon className="w-4 h-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={trigger.name}
                        onChange={(e) => handleUpdateTrigger(trigger.id, { name: e.target.value })}
                        className="flex-1 bg-transparent border-none text-sm font-medium"
                      />
                      <label className="flex items-center gap-1.5 text-sm">
                        <input
                          type="checkbox"
                          checked={trigger.isActive}
                          onChange={(e) => handleUpdateTrigger(trigger.id, { isActive: e.target.checked })}
                          className="rounded text-primary"
                        />
                        Active
                      </label>
                    </div>
                    <p className="text-xs text-muted-foreground capitalize">{trigger.type} trigger</p>
                  </div>
                  <button
                    onClick={() => handleDeleteTrigger(trigger.id)}
                    className="p-1.5 hover:bg-destructive/10 text-destructive rounded transition-colors"
                    title="Delete trigger"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          )}
        </div>
      )}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-4 min-w-[200px] max-w-[400px] max-h-[80vh] overflow-auto">
            <h4 className="font-semibold mb-4">Add Trigger</h4>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Name</label>
                <input
                  type="text"
                  value={newTrigger.name || ''}
                  onChange={(e) => setNewTrigger({ ...newTrigger, name: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded bg-background"
                  placeholder="My Trigger"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Type</label>
                <select
                  value={newTrigger.type}
                  onChange={(e) => setNewTrigger({ ...newTrigger, type: e.target.value as any })}
                  className="w-full px-3 py-2 border border-input rounded bg-background"
                >
                  <option value="schedule">Schedule (Cron)</option>
                  <option value="event">Event</option>
                  <option value="webhook">Webhook</option>
                  <option value="manual">Manual</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 border border-input rounded hover:bg-accent"
              >
                Cancel
              </button>
              <button
                onClick={handleAddTrigger}
                className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
              >
                Add Trigger
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const NODE_PALETTE_ITEMS = [
  { type: 'analytics_query', label: 'Query Analytics', description: 'Run SQL query', icon: null, color: '#3b82f6', service: 'analytics', action: 'query', configSchema: {} },
  { type: 'analytics_cohort', label: 'Cohort Analysis', description: 'Analyze cohorts', icon: null, color: '#3b82f6', service: 'analytics', action: 'cohort', configSchema: {} },
  { type: 'analytics_rfm', label: 'RFM Segmentation', description: 'Segment customers', icon: null, color: '#3b82f6', service: 'analytics', action: 'rfm', configSchema: {} },
  { type: 'analytics_attribution', label: 'Attribution', description: 'Revenue attribution', icon: null, color: '#3b82f6', service: 'analytics', action: 'attribution', configSchema: {} },
  { type: 'analytics_predictive', label: 'Predictive Scoring', description: 'Churn/LTV predictions', icon: null, color: '#3b82f6', service: 'analytics', action: 'predictive', configSchema: {} },
  { type: 'analytics_anomaly', label: 'Anomaly Detection', description: 'Detect anomalies', icon: null, color: '#3b82f6', service: 'analytics', action: 'anomaly', configSchema: {} },
  { type: 'engagement_email', label: 'Send Email', description: 'Send email', icon: null, color: '#10b981', service: 'engagement', action: 'send_email', configSchema: {} },
  { type: 'engagement_sms', label: 'Send SMS', description: 'Send SMS', icon: null, color: '#10b981', service: 'engagement', action: 'send_sms', configSchema: {} },
  { type: 'engagement_push', label: 'Send Push', description: 'Send push', icon: null, color: '#10b981', service: 'engagement', action: 'send_push', configSchema: {} },
  { type: 'ecommerce_order', label: 'Create Order', description: 'Create order', icon: null, color: '#f59e0b', service: 'ecommerce', action: 'create_order', configSchema: {} },
  { type: 'ecommerce_customer', label: 'Upsert Customer', description: 'Update customer', icon: null, color: '#f59e0b', service: 'ecommerce', action: 'upsert_customer', configSchema: {} },
  { type: 'reporting_generate', label: 'Generate Report', description: 'Generate report', icon: null, color: '#8b5cf6', service: 'reporting', action: 'generate_report', configSchema: {} },
  { type: 'reporting_schedule', label: 'Schedule Report', description: 'Schedule report', icon: null, color: '#8b5cf6', service: 'reporting', action: 'schedule_report', configSchema: {} },
  { type: 'condition', label: 'Condition', description: 'Branch on condition', icon: null, color: '#ef4444', service: 'custom', action: 'condition', configSchema: {} },
  { type: 'delay', label: 'Delay', description: 'Wait', icon: null, color: '#6b7280', service: 'custom', action: 'delay', configSchema: {} },
  { type: 'loop', label: 'Loop', description: 'Iterate', icon: null, color: '#6b7280', service: 'custom', action: 'loop', configSchema: {} },
  { type: 'webhook_call', label: 'Call Webhook', description: 'HTTP request', icon: null, color: '#ec4899', service: 'custom', action: 'webhook', configSchema: {} },
  { type: 'transform_data', label: 'Transform Data', description: 'JS transform', icon: null, color: '#6366f1', service: 'custom', action: 'transform', configSchema: {} },
];

export default {
  TriggersPanel,
  NODE_PALETTE_ITEMS,
};