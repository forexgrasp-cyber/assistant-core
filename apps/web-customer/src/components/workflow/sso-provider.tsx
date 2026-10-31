'use client';

import { useState } from 'react';
import { Zap, Settings, Save, Plus, Trash2, Shield, Lock, User, LockOpen, CheckCircle, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SSOProviderItem {
  id: string;
  name: string;
  type: 'saml' | 'oidc' | 'oauth';
  domain: string;
  isEnabled: boolean;
}

interface SSOProviderProps {
  providers: SSOProviderItem[];
  onChange: (providers: SSOProviderItem[]) => void;
}

export function SSOPanel({ providers, onChange }: SSOProviderProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newProvider, setNewProvider] = useState<Partial<SSOProviderItem>>({
    id: '',
    name: '',
    type: 'saml',
    domain: '',
    isEnabled: false,
  });

  const handleAddProvider = () => {
    const provider: SSOProviderItem = {
      id: newProvider.id || `sso-${Date.now()}`,
      name: newProvider.name || '',
      type: newProvider.type || 'saml',
      domain: newProvider.domain || '',
      isEnabled: true,
    };
    onChange([...providers, provider]);
    setShowAddModal(false);
    setNewProvider({ id: '', name: '', type: 'saml', domain: '', isEnabled: true });
  };

  const handleUpdateProvider = (id: string, updates: Partial<SSOProviderItem>) => {
    onChange(providers.map(p => p.id === id ? { ...p, ...updates } : p));
  };

  const handleDeleteProvider = (id: string) => {
    onChange(providers.filter(p => p.id !== id));
  };

  return (
    <div className="bg-card border border-border rounded-lg shadow-lg p-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-blue-600" />
          <h3 className="font-semibold">SSO Providers</h3>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="p-2 hover:bg-accent rounded transition-colors"
          title="Add SSO Provider"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {providers.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p className="mb-2">No SSO providers configured</p>
          <p className="text-sm">Click + to add an SSO provider</p>
        </div>
      ) : (
        <div className="space-y-3">
          {providers.map(provider => (
            <div key={provider.id} className="border rounded-lg p-3 transition-colors">
              <div className="flex items-start gap-3">
                <div className="p-1.5 bg-primary/10 rounded">
                  <Shield className="w-4 h-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={provider.name}
                      onChange={e => handleUpdateProvider(provider.id, { name: e.target.value })}
                      className="flex-1 bg-transparent border-none text-sm font-medium"
                    />
                    <label className="flex items-center gap-1.5 text-sm">
                      <input
                        type="checkbox"
                        checked={provider.isEnabled}
                        onChange={e => handleUpdateProvider(provider.id, { isEnabled: e.target.checked })}
                        className="text-primary"
                      />
                      Enabled
                    </label>
                  </div>
                  <p className="text-xs text-muted-foreground capitalize">{provider.type.toUpperCase()}</p>
                  <p className="text-xs text-muted-foreground">{provider.domain}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <button
                  onClick={() => handleDeleteProvider(provider.id)}
                  className="p-1 hover:bg-destructive/10 text-destructive rounded transition-colors"
                  title="Delete provider"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        )}
      )}

      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border rounded-lg p-4 min-w-[240px] max-w-[400px] overflow-auto">
            <h4 className="font-semibold mb-4">Add SSO Provider</h4>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Provider Name</label>
                <input
                  type="text"
                  value={newProvider.name || ''}
                  onChange={e => setNewProvider({ ...newProvider, name: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded bg-background"
                  placeholder="SAML Provider Name"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Provider Type</label>
                <select
                  value={newProvider.type}
                  onChange={e => setNewProvider({ ...newProvider, type: e.target.value as any })}
                  className="w-full px-3 py-2 border border-input rounded bg-background"
                >
                  <option value="saml">SAML</option>
                  <option value="oidc">OIDC</option>
                  <option value="oauth">OAuth 2.0</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Domain</label>
                <input
                  type="text"
                  value={newProvider.domain || ''}
                  onChange={e => setNewProvider({ ...newProvider, domain: e.target.value })}
                  placeholder="example.com"
                  className="w-full px-3 py-2 border border-input rounded bg-background"
                />
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
                onClick={handleAddProvider}
                className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
              >
                Add Provider
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SSOProvider;
