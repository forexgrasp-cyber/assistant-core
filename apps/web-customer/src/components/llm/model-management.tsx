'use client';

import { useEffect, useState } from 'react';
import { useAppStore } from '@/store';
import { api } from '@/lib/api';
import {
  Settings, Zap, Shield, DollarSign, Eye, Edit, Trash2, Plus, Save, X,
  ChevronDown, ChevronUp, Check, X as XIcon, Loader2, AlertTriangle, Info,
  ToggleLeft, ToggleRight, Copy, ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import toast from 'react-hot-toast';

interface OverrideForm {
  enabled: boolean;
  custom_pricing: {
    input_per_1m: string;
    output_per_1m: string;
    cached_input_per_1m: string;
    currency: string;
  };
  custom_limits: {
    max_context_tokens: string;
    max_output_tokens: string;
    max_input_tokens: string;
  };
  custom_tier: string;
  api_key: string;
  api_base: string;
  extra_headers: Record<string, string>;
  max_monthly_cost_usd: string;
}

interface ModelOverride {
  enabled?: boolean;
  custom_pricing?: {
    input_per_1m?: string;
    output_per_1m?: string;
    cached_input_per_1m?: string;
    currency?: string;
  };
  custom_limits?: {
    max_context_tokens?: string;
    max_output_tokens?: string;
    max_input_tokens?: string;
  };
  custom_tier?: string;
  api_key?: string;
  api_base?: string;
  extra_headers?: Record<string, string>;
  max_monthly_cost_usd?: string;
}

export function LLMModelManagement({ tenantId, isDev = false }: { tenantId: string; isDev?: boolean }) {
  const [models, setModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [overrideForm, setOverrideForm] = useState<OverrideForm>({
    enabled: true,
    custom_pricing: { input_per_1m: '', output_per_1m: '', cached_input_per_1m: '', currency: 'USD' },
    custom_limits: { max_context_tokens: '', max_output_tokens: '', max_input_tokens: '' },
    custom_tier: '',
    api_key: '',
    api_base: '',
    extra_headers: {},
    max_monthly_cost_usd: '',
  });
  const [providerConfigs, setProviderConfigs] = useState<Record<string, any>>({});
  const [defaults, setDefaults] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<'models' | 'overrides' | 'defaults' | 'providers'>('models');
  const [providerFilter, setProviderFilter] = useState('');
  const [tierFilter, setTierFilter] = useState('');
  const [capabilityFilter, setCapabilityFilter] = useState('');
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [tenantId]);

  async function loadData() {
    setLoading(true);
    try {
      const [modelsRes, overridesRes, defaultsRes, providersRes] = await Promise.all([
        api.get('/llm/models', { params: { provider: providerFilter, tier: tierFilter, capability: capabilityFilter } }),
        api.get('/llm/overrides'),
        api.get('/llm/defaults'),
        api.get('/llm/providers'),
      ]);
      setModels(modelsRes.data);
      setOverrideFormValues(overridesRes.data);
      setDefaults(defaultsRes.data.defaults);
      setProviderConfigs(providersRes.data);
    } catch (error) {
      toast.error('Failed to load LLM models');
    } finally {
      setLoading(false);
    }
  }

  function setOverrideFormValues(overrides: Record<string, any>) {
    // Store overrides for reference
  }

  function getOverride(modelId: string): ModelOverride | null {
    // In real implementation, would fetch from overrides state
    return null;
  }

  function handleModelClick(model: any) {
    setSelectedModel(model);
  }

  function handleOpenOverride(model: any) {
    setSelectedModel(model);
    const override = getOverride(model.id);
    setOverrideForm({
      enabled: override?.enabled ?? true,
      custom_pricing: {
        input_per_1m: override?.custom_pricing?.input_per_1m ?? '',
        output_per_1m: override?.custom_pricing?.output_per_1m ?? '',
        cached_input_per_1m: override?.custom_pricing?.cached_input_per_1m ?? '',
        currency: override?.custom_pricing?.currency ?? 'USD',
      },
      custom_limits: {
        max_context_tokens: override?.custom_limits?.max_context_tokens ?? '',
        max_output_tokens: override?.custom_limits?.max_output_tokens ?? '',
        max_input_tokens: override?.custom_limits?.max_input_tokens ?? '',
      },
      custom_tier: override?.custom_tier ?? '',
      api_key: override?.api_key ?? '',
      api_base: override?.api_base ?? '',
      extra_headers: override?.extra_headers ?? {},
      max_monthly_cost_usd: override?.max_monthly_cost_usd ?? '',
    });
    setShowOverrideModal(true);
  }

  async function handleSaveOverride() {
    if (!selectedModel) return;
    setSaving(selectedModel.id);
    try {
      const pricing = overrideForm.custom_pricing.input_per_1m ? {
        input_per_1m: parseFloat(overrideForm.custom_pricing.input_per_1m),
        output_per_1m: parseFloat(overrideForm.custom_pricing.output_per_1m),
        cached_input_per_1m: overrideForm.custom_pricing.cached_input_per_1m ? parseFloat(overrideForm.custom_pricing.cached_input_per_1m) : undefined,
        currency: overrideForm.custom_pricing.currency,
      } : undefined;

      const limits = overrideForm.custom_limits.max_context_tokens ? {
        max_context_tokens: parseInt(overrideForm.custom_limits.max_context_tokens),
        max_output_tokens: parseInt(overrideForm.custom_limits.max_output_tokens),
        max_input_tokens: overrideForm.custom_limits.max_input_tokens ? parseInt(overrideForm.custom_limits.max_input_tokens) : undefined,
      } : undefined;

      await api.post(`/llm/models/${selectedModel.id}/override`, {
        enabled: overrideForm.enabled,
        custom_pricing: pricing,
        custom_limits: limits,
        custom_tier: overrideForm.custom_tier || undefined,
        api_key: overrideForm.api_key || undefined,
        api_base: overrideForm.api_base || undefined,
        extra_headers: overrideForm.extra_headers,
        max_monthly_cost_usd: overrideForm.max_monthly_cost_usd ? parseFloat(overrideForm.max_monthly_cost_usd) : undefined,
      });

      toast.success('Override saved');
      setShowOverrideModal(false);
      loadData();
    } catch (error) {
      toast.error('Failed to save override');
    } finally {
      setSaving(null);
    }
  }

  async function handleRemoveOverride(modelId: string) {
    try {
      await api.delete(`/llm/models/${modelId}/override`);
      toast.success('Override removed');
      loadData();
    } catch (error) {
      toast.error('Failed to remove override');
    }
  }

  async function handleSetDefault(tier: string, modelId: string) {
    try {
      await api.post(`/llm/defaults/${tier}`, { model_id: modelId });
      toast.success(`Default for ${tier} updated`);
      loadData();
    } catch (error) {
      toast.error('Failed to set default');
    }
  }

  const tierOrder: Record<string, number> = { flagship: 0, balanced: 1, fast: 2, economy: 3, embedding: 4 };

  const filteredModels = models.filter(m => {
    if (providerFilter && m.provider !== providerFilter) return false;
    if (tierFilter && m.tier !== tierFilter) return false;
    if (capabilityFilter && !m.capabilities.includes(capabilityFilter)) return false;
    return true;
  }).sort((a, b) => (tierOrder[a.tier] || 99) - (tierOrder[b.tier] || 99));

  const providers = Object.keys(providerConfigs);

  return (
    <div className="h-full flex flex-col">
      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="flex gap-1 px-4" role="tablist">
          {[
            { id: 'models', label: 'Models', icon: Zap },
            { id: 'overrides', label: 'Overrides', icon: Settings },
            { id: 'defaults', label: 'Defaults', icon: Shield },
            { id: 'providers', label: 'Providers', icon: ExternalLink },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors',
                activeTab === tab.id
                  ? 'bg-primary text-primary-foreground border-b-2 border-primary'
                  : 'text-muted-foreground hover:text-foreground hover:bg-accent'
              )}
              role="tab"
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Filters */}
      {activeTab === 'models' && (
        <div className="p-4 border-b border-border bg-muted/50 flex flex-wrap gap-4">
          <select
            value={providerFilter}
            onChange={e => { setProviderFilter(e.target.value); loadData(); }}
            className="px-3 py-2 border border-input rounded-lg bg-background text-sm min-w-[150px]"
          >
            <option value="">All Providers</option>
            {providers.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <select
            value={tierFilter}
            onChange={e => { setTierFilter(e.target.value); loadData(); }}
            className="px-3 py-2 border border-input rounded-lg bg-background text-sm min-w-[150px]"
          >
            <option value="">All Tiers</option>
            <option value="flagship">Flagship</option>
            <option value="balanced">Balanced</option>
            <option value="fast">Fast</option>
            <option value="economy">Economy</option>
            <option value="embedding">Embedding</option>
          </select>
          <select
            value={capabilityFilter}
            onChange={e => { setCapabilityFilter(e.target.value); loadData(); }}
            className="px-3 py-2 border border-input rounded-lg bg-background text-sm min-w-[180px]"
          >
            <option value="">All Capabilities</option>
            <option value="text">Text</option>
            <option value="vision">Vision</option>
            <option value="function_calling">Function Calling</option>
            <option value="reasoning">Reasoning</option>
            <option value="long_context">Long Context</option>
            <option value="streaming">Streaming</option>
            <option value="structured_output">Structured Output</option>
            <option value="audio">Audio</option>
            <option value="embedding">Embedding</option>
          </select>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : activeTab === 'models' ? (
          <ModelList
            models={filteredModels}
            onViewOverride={handleOpenOverride}
            onSetDefault={handleSetDefault}
            isDev={isDev}
            tenantId={tenantId}
          />
        ) : activeTab === 'overrides' ? (
          <OverridesList
            models={models}
            overrides={[]}
            onEdit={handleOpenOverride}
            onRemove={handleRemoveOverride}
            saving={saving}
            isDev={isDev}
          />
        ) : activeTab === 'defaults' ? (
          <DefaultsManager
            defaults={defaults}
            models={models}
            onSetDefault={handleSetDefault}
            isDev={isDev}
          />
        ) : activeTab === 'providers' ? (
          <ProvidersManager
            providers={providerConfigs}
            isDev={isDev}
          />
        ) : null}
      </div>

      {/* Override Modal */}
      {showOverrideModal && selectedModel ? (
        <OverrideModal
          model={selectedModel as Model}
          form={overrideForm}
          onChange={setOverrideForm}
          onSave={handleSaveOverride}
          onClose={() => setShowOverrideModal(false)}
          saving={saving === selectedModel.id}
        />
      ) : null}
    </div>
  );
}

function ModelList({ models, onViewOverride, onSetDefault, isDev, tenantId }: any) {
  const tierColors: Record<string, string> = {
    flagship: 'bg-purple-100 text-purple-700',
    balanced: 'bg-blue-100 text-blue-700',
    fast: 'bg-green-100 text-green-700',
    economy: 'bg-gray-100 text-gray-700',
    embedding: 'bg-orange-100 text-orange-700',
  };

  const capabilityIcons: Record<string, React.ReactNode> = {
    text: <Zap className="w-3 h-3" />,
    vision: <Eye className="w-3 h-3" />,
    function_calling: <Settings className="w-3 h-3" />,
    reasoning: <Shield className="w-3 h-3" />,
    long_context: <Info className="w-3 h-3" />,
    streaming: <Zap className="w-3 h-3" />,
    structured_output: <Check className="w-3 h-3" />,
    audio: <ExternalLink className="w-3 h-3" />,
    embedding: <DollarSign className="w-3 h-3" />,
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Available Models ({models.length})</h2>
        {isDev && (
          <span className="text-xs text-muted-foreground">Dev mode: Can set global defaults</span>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {models.map((model: Model) => (
          <ModelCard
            key={model.id}
            model={model}
            onViewOverride={onViewOverride}
            onSetDefault={onSetDefault}
            isDev={isDev}
            tierColors={tierColors}
            capabilityIcons={capabilityIcons}
          />
        ))}
      </div>
    </div>
  );
}

interface Model {
  id: string;
  name: string;
  provider: string;
  tier: string;
  description: string;
  capabilities: string[];
  pricing: {
    input_per_1m: string;
    output_per_1m: string;
    cached_input_per_1m?: string;
  };
  limits: {
    max_context_tokens: number;
    max_output_tokens: number;
  };
  deprecated?: boolean;
  deprecated_at?: string;
  replacement_model_id?: string;
}

interface ModelCardProps {
  model: Model;
  onViewOverride: (model: Model) => void;
  onSetDefault: (tier: string, modelId: string) => void;
  isDev: boolean;
  tierColors: Record<string, string>;
  capabilityIcons: Record<string, React.ReactNode>;
}

function ModelCard({ model, onViewOverride, onSetDefault, isDev, tierColors, capabilityIcons }: ModelCardProps) {
  const override = null; // Would come from parent

  return (
    <div className="bg-card border border-border rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold truncate">{model.name}</h3>
            <span className={cn('px-2 py-0.5 text-xs rounded-full', tierColors[model.tier])}>
              {model.tier}
            </span>
            <span className="text-xs text-muted-foreground px-2 py-0.5 rounded bg-muted">
              {model.provider}
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{model.description}</p>

          {/* Capabilities */}
          <div className="flex flex-wrap gap-1 mt-2">
            {model.capabilities.map((cap: string) => (
              <span
                key={cap}
                className="flex items-center gap-1 px-2 py-0.5 text-xs text-muted-foreground bg-muted rounded"
              >
                {capabilityIcons[cap]}
                {cap.replace('_', ' ')}
              </span>
            ))}
          </div>

          {/* Pricing */}
          <div className="mt-3 pt-3 border-t border-border">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Input:</span>
              <span className="font-mono">${parseFloat(model.pricing.input_per_1m).toFixed(2)}/1M</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Output:</span>
              <span className="font-mono">${parseFloat(model.pricing.output_per_1m).toFixed(2)}/1M</span>
            </div>
            {model.pricing.cached_input_per_1m && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Cached:</span>
                <span className="font-mono">${parseFloat(model.pricing.cached_input_per_1m).toFixed(2)}/1M</span>
              </div>
            )}
          </div>

          {/* Limits */}
          <div className="mt-2 text-xs text-muted-foreground">
            Context: {model.limits.max_context_tokens.toLocaleString()} tokens •
            Output: {model.limits.max_output_tokens.toLocaleString()} tokens
          </div>

          {model.deprecated && (
            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-yellow-700 text-xs">
              ⚠️ Deprecated {model.deprecated_at ? `(${model.deprecated_at})` : ''}
              {model.replacement_model_id && <span> → Use {model.replacement_model_id}</span>}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 ml-4 flex-shrink-0">
          <button
            onClick={() => onViewOverride(model)}
            className="p-2 hover:bg-accent rounded transition-colors text-muted-foreground hover:text-foreground"
            title="Configure Override"
          >
            <Settings className="w-4 h-4" />
          </button>
          {isDev && (
            <button
              onClick={() => onSetDefault(model.tier, model.id)}
              className="p-2 hover:bg-accent rounded transition-colors text-muted-foreground hover:text-foreground"
              title={`Set as default for ${model.tier}`}
            >
              <Shield className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

interface ModelOverride {
  enabled?: boolean;
  custom_pricing?: {
    input_per_1m?: string;
    output_per_1m?: string;
    cached_input_per_1m?: string;
    currency?: string;
  };
  custom_limits?: {
    max_context_tokens?: string;
    max_output_tokens?: string;
    max_input_tokens?: string;
  };
  custom_tier?: string;
  api_key?: string;
  api_base?: string;
  extra_headers?: Record<string, string>;
  max_monthly_cost_usd?: string;
}

interface ModelWithOverrides {
  id: string;
  name: string;
  provider: string;
  tier: string;
  tenant_overrides?: any[];
}

interface OverridesListProps {
  models: ModelWithOverrides[];
  overrides: any[];
  onEdit: (model: ModelWithOverrides) => void;
  onRemove: (modelId: string) => void;
  saving: string | null;
  isDev: boolean;
}

interface DefaultsManagerProps {
  defaults: Record<string, string>;
  models: Model[];
  onSetDefault: (tier: string, modelId: string) => void;
  isDev: boolean;
}

interface ProviderConfig {
  name: string;
  api_base: string;
  auth_type: string;
  auth_header: string;
  api_key_env: string;
  supports_streaming: boolean;
  supports_function_calling: boolean;
  rate_limit_rpm: number;
  rate_limit_tpm: number;
  webhook_secret_env: string;
  extra_headers: Record<string, string>;
}

interface ProvidersManagerProps {
  providers: Record<string, ProviderConfig>;
  isDev: boolean;
}

interface OverridesListProps {
  models: ModelWithOverrides[];
  overrides: any[];
  onEdit: (model: ModelWithOverrides) => void;
  onRemove: (modelId: string) => void;
  saving: string | null;
  isDev: boolean;
}

function OverridesList({ models, overrides, onEdit, onRemove, saving, isDev }: OverridesListProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Tenant Overrides</h2>
      <p className="text-sm text-muted-foreground">
        Configure per-client model settings. Overrides apply only to this tenant.
      </p>

      {models.filter(m => m.tenant_overrides && m.tenant_overrides.length > 0).map(model => (
        <div key={model.id} className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">{model.name}</h3>
              <p className="text-sm text-muted-foreground">{model.provider} • {model.tier}</p>
            </div>
            <button
              onClick={() => onEdit(model)}
              disabled={saving === model.id}
              className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
            >
              {saving === model.id ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Edit Override'}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function DefaultsManager({ defaults, models, onSetDefault, isDev }: DefaultsManagerProps) {
  if (!isDev) {
    return (
      <div className="text-center py-12">
        <Shield className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
        <h3 className="text-lg font-medium mb-2">Dev Access Required</h3>
        <p className="text-muted-foreground">Only developers can manage global default models.</p>
      </div>
    );
  }

  const tierOrder = ['flagship', 'balanced', 'fast', 'economy', 'embedding'];

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Global Default Models</h2>
      <p className="text-sm text-muted-foreground">
        Default models are used when no tenant override exists. Used by workflows and auto-selection.
      </p>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {tierOrder.map(tier => {
          const defaultModelId = defaults[tier];
          const defaultModel = models.find(m => m.id === defaultModelId);
          const tierModels = models.filter(m => m.tier === tier && !m.deprecated);

          return (
            <div key={tier} className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold capitalize">{tier}</h3>
              </div>

              <select
                value={defaultModelId || ''}
                onChange={e => onSetDefault(tier, e.target.value)}
                className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm"
              >
                <option value="">— Select Default —</option>
                {tierModels.map(m => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>

              {defaultModel && (
                <div className="mt-2 p-2 bg-muted rounded text-sm">
                  Current: <span className="font-medium">{defaultModel.name}</span>
                  <span className="text-muted-foreground ml-2">({defaultModel.provider})</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ProvidersManager({ providers, isDev }: ProvidersManagerProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Provider Configurations</h2>
      <p className="text-sm text-muted-foreground">
        Configure API endpoints, auth, and rate limits for each provider.
      </p>

      <div className="grid gap-4 md:grid-cols-2">
        {Object.entries(providers).map(([key, config]: [string, ProviderConfig]) => (
          <div key={key} className="bg-card border border-border rounded-lg p-4">
            <h3 className="font-semibold capitalize mb-3">{key}</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">API Base</dt>
                <dd className="font-mono text-xs truncate max-w-[200px]">{config.api_base}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Auth Type</dt>
                <dd>{config.auth_type}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Auth Header</dt>
                <dd className="font-mono text-xs">{config.auth_header}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">API Key Env</dt>
                <dd className="font-mono text-xs">{config.api_key_env || 'Not set'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Streaming</dt>
                <dd>{config.supports_streaming ? '✓' : '✗'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Function Calling</dt>
                <dd>{config.supports_function_calling ? '✓' : '✗'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Rate Limit (RPM)</dt>
                <dd>{config.rate_limit_rpm}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Rate Limit (TPM)</dt>
                <dd>{config.rate_limit_tpm.toLocaleString()}</dd>
              </div>
            </dl>
            {isDev && (
              <button className="mt-3 w-full px-3 py-1.5 text-sm border border-input rounded-lg hover:bg-accent">
                Edit Config
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

interface OverrideModalProps {
  model: Model;
  form: OverrideForm;
  onChange: React.Dispatch<React.SetStateAction<OverrideForm>>;
  onSave: () => void;
  onClose: () => void;
  saving: boolean;
}

function OverrideModal({ model, form, onChange, onSave, onClose, saving }: OverrideModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-card rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h3 className="font-semibold">Configure Override: {model.name}</h3>
          <button onClick={onClose} className="p-1 hover:bg-accent rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 space-y-6">
          {/* Enable/Disable */}
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Enable Model</p>
              <p className="text-sm text-muted-foreground">Disable to hide from this tenant</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={e => onChange({ ...form, enabled: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
            </label>
          </div>

          {/* Custom Pricing */}
          <div className="border-t border-border pt-4">
            <h4 className="font-medium mb-3">Custom Pricing (per 1M tokens)</h4>
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <label className="block text-sm font-medium mb-1">Input</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.custom_pricing.input_per_1m}
                  onChange={e => onChange({ ...form, custom_pricing: { ...form.custom_pricing, input_per_1m: e.target.value } })}
                  className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm"
                  placeholder="e.g., 3.00"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Output</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.custom_pricing.output_per_1m}
                  onChange={e => onChange({ ...form, custom_pricing: { ...form.custom_pricing, output_per_1m: e.target.value } })}
                  className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm"
                  placeholder="e.g., 15.00"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Cached Input</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.custom_pricing.cached_input_per_1m}
                  onChange={e => onChange({ ...form, custom_pricing: { ...form.custom_pricing, cached_input_per_1m: e.target.value } })}
                  className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm"
                  placeholder="e.g., 0.30"
                />
              </div>
            </div>
          </div>

          {/* Custom Limits */}
          <div className="border-t border-border pt-4">
            <h4 className="font-medium mb-3">Custom Limits</h4>
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <label className="block text-sm font-medium mb-1">Max Context Tokens</label>
                <input
                  type="number"
                  value={form.custom_limits.max_context_tokens}
                  onChange={e => onChange({ ...form, custom_limits: { ...form.custom_limits, max_context_tokens: e.target.value } })}
                  className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm"
                  placeholder="e.g., 200000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Max Output Tokens</label>
                <input
                  type="number"
                  value={form.custom_limits.max_output_tokens}
                  onChange={e => onChange({ ...form, custom_limits: { ...form.custom_limits, max_output_tokens: e.target.value } })}
                  className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm"
                  placeholder="e.g., 8192"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Max Input Tokens</label>
                <input
                  type="number"
                  value={form.custom_limits.max_input_tokens}
                  onChange={e => onChange({ ...form, custom_limits: { ...form.custom_limits, max_input_tokens: e.target.value } })}
                  className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm"
                  placeholder="Optional"
                />
              </div>
            </div>
          </div>

          {/* API Key & Base */}
          <div className="border-t border-border pt-4">
            <h4 className="font-medium mb-3">Client API Credentials</h4>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">API Key</label>
                <div className="relative">
                  <input
                    type="password"
                    value={form.api_key}
                    onChange={e => onChange({ ...form, api_key: e.target.value })}
                    className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm pr-10"
                    placeholder="Client's own API key (optional)"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                    Stored encrypted
                  </span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Custom API Base</label>
                <input
                  type="text"
                  value={form.api_base}
                  onChange={e => onChange({ ...form, api_base: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm"
                  placeholder="e.g., https://custom-proxy.com/v1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Max Monthly Cost (USD)</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.max_monthly_cost_usd}
                  onChange={e => onChange({ ...form, max_monthly_cost_usd: e.target.value })}
                  className="w-full px-3 py-2 border border-input rounded-lg bg-background text-sm"
                  placeholder="Budget limit for this model"
                />
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 border-t border-border pt-4">
            <button onClick={onClose} className="px-4 py-2 border border-input rounded-lg hover:bg-accent">
              Cancel
            </button>
            <button
              onClick={onSave}
              disabled={saving}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save Override'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}