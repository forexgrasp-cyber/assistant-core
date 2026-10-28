'use client';

import { useState } from 'react';
import { Plus, Trash2, Calendar, Clock, Zap, Mail, Bell } from 'lucide-react';
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
      conditions: [],
    };
    onChange([...triggers, trigger]);
    setShowAddModal(false);
    setNewTrigger({ type: 'schedule', config: {} });
  };

  const handleUpdateTrigger = (id: string, updates: Partial<WorkflowTrigger>) => {
    onChange(triggers.map(t => t.id === id ? { ...t, ...updates } : t));
  };

  const handleDeleteTrigger = (id: string) => {
    onChange(triggers.filter(t => t.id !== id));
  };

  const handleConfigChange = (id: string, key: string, value: any) => {
    const trigger = triggers.find(t => t.id === id);
    if (trigger) {
      handleUpdateTrigger(id, {
        config: { ...trigger.config, [key]: value },
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
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
                        onChange={e => handleUpdateTrigger(trigger.id, { name: e.target.value })}
                        className="flex-1 bg-transparent border-none focus:outline-none text-sm font-medium"
                      />
                      <label className="flex items-center gap-1.5 text-sm">
                        <input
                          type="checkbox"
                          checked={trigger.isActive}
                          onChange={e => handleUpdateTrigger(trigger.id, { isActive: e.target.checked })}
                          className="rounded border-input"
                        />
                        Active
                      </label>
                    </div>
                    <p className="text-xs text-muted-foreground capitalize">{trigger.type} trigger</p>
                    
                    {trigger.type === 'schedule' && (
                      <div className="mt-2 space-y-2 text-sm">
                        <div>
                          <label className="text-xs text-muted-foreground">Cron Expression</label>
                          <input
                            type="text"
                            value={trigger.config.cron || ''}
                            onChange={e => handleConfigChange(trigger.id, 'cron', e.target.value)}
                            placeholder="0 9 * * 1-5"
                            className="w-full mt-1 px-2 py-1 border border-input rounded bg-background text-sm"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-muted-foreground">Timezone</label>
                          <input
                            type="text"
                            value={trigger.config.timezone || 'UTC'}
                            onChange={e => handleConfigChange(trigger.id, 'timezone', e.target.value)}
                            className="w-full mt-1 px-2 py-1 border border-input rounded bg-background text-sm"
                          />
                        </div>
                      </div>
                    )}

                    {trigger.type === 'event' && (
                      <div className="mt-2 space-y-2 text-sm">
                        <div>
                          <label className="text-xs text-muted-foreground">Event Name</label>
                          <input
                            type="text"
                            value={trigger.config.eventName || ''}
                            onChange={e => handleConfigChange(trigger.id, 'eventName', e.target.value)}
                            placeholder="user.signup"
                            className="w-full mt-1 px-2 py-1 border border-input rounded bg-background text-sm"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-muted-foreground">Source</label>
                          <input
                            type="text"
                            value={trigger.config.source || ''}
                            onChange={e => handleConfigChange(trigger.id, 'source', e.target.value)}
                            placeholder="analytics"
                            className="w-full mt-1 px-2 py-1 border border-input rounded bg-background text-sm"
                          />
                        </div>
                      </div>
                    )}

                    {trigger.type === 'webhook' && (
                      <div className="mt-2 space-y-2 text-sm">
                        <div>
                          <label className="text-xs text-muted-foreground">Webhook Path</label>
                          <input
                            type="text"
                            value={trigger.config.path || ''}
                            onChange={e => handleConfigChange(trigger.id, 'path', e.target.value)}
                            placeholder="/webhook/custom-event"
                            className="w-full mt-1 px-2 py-1 border border-input rounded bg-background text-sm"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-muted-foreground">Secret (optional)</label>
                          <input
                            type="password"
                            value={trigger.config.secret || ''}
                            onChange={e => handleConfigChange(trigger.id, 'secret', e.target.value)}
                            placeholder="hmac secret"
                            className="w-full mt-1 px-2 py-1 border border-input rounded bg-background text-sm"
                          />
                        </div>
                      </div>
                    )}
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
            );
          })}
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-6 w-full max-w-md">
            <h4 className="font-semibold mb-4">Add Trigger</h4>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Name</label>
                <input
                  type="text"
                  value={newTrigger.name || ''}
                  onChange={e => setNewTrigger({ ...newTrigger, name: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded bg-background"
                  placeholder="My Trigger"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Type</label>
                <select
                  value={newTrigger.type}
                  onChange={e => setNewTrigger({ ...newTrigger, type: e.target.value as any })}
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