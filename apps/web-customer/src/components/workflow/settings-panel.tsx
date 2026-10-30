'use client';

import { useState } from 'react';
import { X, Save, RotateCcw, AlertTriangle, CheckCircle, XCircle, Bell, Mail, Slack } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkflowSettings } from '@/types';

interface SettingsPanelProps {
  settings: WorkflowSettings;
  onChange: (settings: WorkflowSettings) => void;
}

export function SettingsPanel({ settings, onChange }: SettingsPanelProps) {
  const [activeTab, setActiveTab] = useState<'general' | 'retry' | 'notifications'>('general');

  const errorHandlingOptions = [
    { value: 'stop', label: 'Stop on Error', description: 'Halt execution when any node fails' },
    { value: 'continue', label: 'Continue on Error', description: 'Skip failed nodes and continue' },
    { value: 'retry', label: 'Retry Failed Nodes', description: 'Automatically retry based on retry policy' },
  ];

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex border-b border-border">
        {[
          { id: 'general', label: 'General', icon: null },
          { id: 'retry', label: 'Retry Policy', icon: RotateCcw },
          { id: 'notifications', label: 'Notifications', icon: Bell },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 text-sm border-b-2 transition-colors',
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.icon && <tab.icon className="w-4 h-4" />}
            {tab.label}
          </button>
        ))}
      </div>

      {/* General Tab */}
      {activeTab === 'general' && (
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Concurrency Limit</label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                value={settings.concurrencyLimit}
                onChange={e => onChange({ ...settings, concurrencyLimit: parseInt(e.target.value) || 1 })}
                min={1}
                max={100}
                className="w-24 px-3 py-2 border border-input rounded bg-background"
              />
              <span className="text-sm text-muted-foreground">Max parallel executions</span>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">Timeout (seconds)</label>
            <div className="flex items-center gap-4">
              <input
                type="number"
                value={settings.timeoutSeconds}
                onChange={e => onChange({ ...settings, timeoutSeconds: parseInt(e.target.value) || 60 })}
                min={60}
                max={86400}
                className="w-24 px-3 py-2 border border-input rounded bg-background"
              />
              <span className="text-sm text-muted-foreground">Max execution time</span>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">Error Handling</label>
            <div className="space-y-2">
              {errorHandlingOptions.map(opt => (
                <label
                  key={opt.value}
                  className={cn(
                    'flex items-center gap-3 p-3 rounded-lg border transition-colors',
                    settings.errorHandling === opt.value
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50'
                  )}
                >
                  <input
                    type="radio"
                    name="errorHandling"
                    value={opt.value}
                    checked={settings.errorHandling === opt.value}
                    onChange={e => onChange({ ...settings, errorHandling: e.target.value as any })}
                    className="text-primary"
                  />
                  <div>
                    <p className="font-medium">{opt.label}</p>
                    <p className="text-xs text-muted-foreground">{opt.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Retry Policy Tab */}
      {activeTab === 'retry' && (
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Max Retries</label>
            <input
              type="number"
              value={settings.retryPolicy.maxRetries}
              onChange={e => onChange({
                ...settings,
                retryPolicy: { ...settings.retryPolicy, maxRetries: parseInt(e.target.value) || 0 }
              })}
              min={0}
              max={10}
              className="w-24 px-3 py-2 border border-input rounded bg-background"
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">Backoff (seconds)</label>
            <input
              type="number"
              value={settings.retryPolicy.backoffSeconds}
              onChange={e => onChange({
                ...settings,
                retryPolicy: { ...settings.retryPolicy, backoffSeconds: parseInt(e.target.value) || 60 }
              })}
              min={1}
              max={3600}
              className="w-24 px-3 py-2 border border-input rounded bg-background"
            />
          </div>

          <div className="p-3 bg-muted/50 rounded-lg">
            <p className="text-sm text-muted-foreground">
              Retries use exponential backoff. Each retry waits: backoff × 2^attempt
            </p>
          </div>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="space-y-6">
          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-destructive" />
              On Failure
            </h4>
            <NotificationChannelList
              channels={settings.notifications.onFailure}
              onChange={channels => onChange({ ...settings, notifications: { ...settings.notifications, onFailure: channels } })}
              availableChannels={[
                { id: 'email', label: 'Email', icon: Mail },
                { id: 'slack', label: 'Slack', icon: Slack },
                { id: 'webhook', label: 'Webhook', icon: Mail },
              ]}
            />
          </div>

          <div>
            <h4 className="font-medium mb-3 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-600" />
              On Success
            </h4>
            <NotificationChannelList
              channels={settings.notifications.onSuccess}
              onChange={channels => onChange({ ...settings, notifications: { ...settings.notifications, onSuccess: channels } })}
              availableChannels={[
                { id: 'email', label: 'Email', icon: Mail },
                { id: 'slack', label: 'Slack', icon: Slack },
                { id: 'webhook', label: 'Webhook', icon: Mail },
              ]}
            />
          </div>
        </div>
      )}
    </div>
  );
}

interface NotificationChannelListProps {
  channels: string[];
  onChange: (channels: string[]) => void;
  availableChannels: Array<{ id: string; label: string; icon: React.ComponentType<{ className?: string }> }>;
}

function NotificationChannelList({ channels, onChange, availableChannels }: NotificationChannelListProps) {
  return (
    <div className="space-y-2">
      {availableChannels.map(channel => {
        const Icon = channel.icon;
        const isEnabled = channels.includes(channel.id);
        return (
          <label
            key={channel.id}
            className={cn(
              'flex items-center gap-3 p-3 rounded-lg border transition-colors cursor-pointer',
              isEnabled ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
            )}
          >
            <input
              type="checkbox"
              checked={isEnabled}
              onChange={e => onChange(
                e.target.checked
                  ? [...channels, channel.id]
                  : channels.filter(c => c !== channel.id)
              )}
              className="text-primary"
            />
            <Icon className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm">{channel.label}</span>
            {isEnabled && <span className="ml-auto text-xs text-green-600">Enabled</span>}
          </label>
        )}
      )}
      {channels.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-4">
          No notification channels configured
        </p>
      )}
    </div>
  );
}
