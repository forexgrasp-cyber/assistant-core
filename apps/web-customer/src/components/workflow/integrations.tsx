'use client';

import { useState } from 'react';
import { Zap, Mail, Slack as SlackIcon, Database, Play, RefreshCcw, Trash2, Plus, SettingsIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface IntegrationItem {
  id: string;
  name: string;
  type: string;
  config: Record<string, any>;
}

interface IntegrationsPanelProps {
  integrations: IntegrationItem[];
  onChange: (integrations: IntegrationItem[]) => void;
  availableIntegrations: Array<{ id: string; label: string; type: string; configSchema: Record<string, any> }>;
}

export function IntegrationsPanel({ integrations, onChange, availableIntegrations }: IntegrationsPanelProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newIntegration, setNewIntegration] = useState<Partial<IntegrationItem>>({
    id: `integration-${Date.now()}`,
    name: '',
    type: 'source',
    config: {},
  });

  const handleAddIntegration = () => {
    const integration: IntegrationItem = {
      id: newIntegration.id || `integration-${Date.now()}`,
      name: newIntegration.name || '',
      type: newIntegration.type || 'source',
      config: newIntegration.config || {},
    };
    onChange([...integrations, integration]);
    setShowAddModal(false);
    setNewIntegration({ id: `integration-${Date.now()}`, name: '', type: 'source', config: {} });
  };

  const handleUpdateIntegration = (id: string, updates: Partial<IntegrationItem>) => {
    onChange(integrations.map(i => i.id === id ? { ...i, ...updates } : i));
  };

  const handleDeleteIntegration = (id: string) => {
    onChange(integrations.filter(i => i.id !== id));
  };

  return (
    <div className="bg-card border border-border rounded-lg shadow-lg p-4 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4" />
          <h3 className="font-semibold">Integrations</h3>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="p-2 hover:bg-accent rounded transition-colors"
          title="Add Integration"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {integrations.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p className="mb-2">No integrations configured</p>
          <p className="text-sm">Click + to add an integration</p>
        </div>
      ) : (
        <div className="space-y-3">
          {integrations.map(integration => (
            <div key={integration.id} className="border rounded-lg p-3 transition-colors">
              <div className="flex items-start gap-3">
                <div className="p-1.5 bg-primary/10 rounded">
                  <Mail className="w-4 h-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={integration.name}
                      onChange={e => handleUpdateIntegration(integration.id, { name: e.target.value })}
                      className="flex-1 bg-transparent border-none text-sm font-medium"
                    />
                    <label className="flex items-center gap-1.5 text-sm">
                      <input
                        type="checkbox"
                        checked={integration.isActive}
                        onChange={e => handleUpdateIntegration(integration.id, { isActive: e.target.checked })}
                        className="text-primary"
                      />
                      {integration.name}
                    </label>
                  </div>
                  <p className="text-xs text-muted-foreground capitalize">{integration.type} service</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-4 min-w-[200px] max-w-[400px] max-h-[80vh] overflow-auto">
            <h4 className="font-semibold mb-4">Add Integration</h4>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Name</label>
                <input
                  type="text"
                  value={newIntegration.name || ''}
                  onChange={e => setNewIntegration({ ...newIntegration, name: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded bg-background"
                  placeholder="My Integration"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Type</label>
                <select
                  value={newIntegration.type}
                  onChange={e => setNewIntegration({ ...newIntegration, type: e.target.value as any })}
                  className="w-full px-3 py-2 border border-input rounded bg-background"
                >
                  <option value="source">Source (Read)</option>
                  <option value="destination">Destination (Write)</option>
                  <option value="both">Both (Read & Write)</option>
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
                onClick={handleAddIntegration}
                className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
              >
                Add Integration
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
