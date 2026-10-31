'use client';

import React, { useState } from 'react';
import { Shield, Lock, Delete, CheckCircle, ArrowRight, Download } from 'lucide-react';
import { cn } from '@/lib/utils';

interface GDPRManagerProps {
  onDataExport?: () => void;
  onDataDeletion?: () => void;
  onDataAccess?: () => void;
  consentSettings: {
    marketing: boolean;
    analytics: boolean;
    functional: boolean;
    essential: boolean;
  };
  onConsentChange: (type: string, enabled: boolean) => void;
}

export function GDPRPanel({ settings, onChange }: GDPRPanelProps) {
  const [showRequestModal, setShowAddModal] = useState(false);
  const [requestType, setRequestType] = useState<'access' | 'erasure' | 'portability' | null>(null);

  const handleDataRequest = (type: 'access' | 'erasure' | 'portability') => {
    setShowAddModal(true);
    setRequestType(type);
  };

  return (
    <div className="bg-card border border-border rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-semibold text-gray-900">Data Protection & Privacy</h3>
        <div className="flex gap-2">
          <button
            onClick={handleDataRequest}
            className="px-3 py-1.5 border border-input rounded hover:bg-accent text-sm"
          >
            Data Access Request
          </button>
          <button
            onClick={() => handleDataRequest('erasure')}
            className="px-4 py-2 border border-destructive text-destructive rounded hover:bg-destructive/10"
          >
            Request Data Deletion
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {/* Consent Management */}
        <div className="p-4 bg-muted/50 rounded-lg">
          <h4 className="font-semibold mb-3">Consent Preferences</h4>
          <div className="space-y-3">
            {[
              { id: 'essential', label: 'Essential Cookies', description: 'Required for site functionality' },
              { id: 'analytics', label: 'Analytics Cookies', description: 'Help us improve our services' },
              { id: 'marketing', label: 'Marketing Cookies', description: 'Personalized offers and recommendations' },
            ].map((setting) => (
              <div key={setting.id} className="flex items-center justify-between p-3 bg-white border border-input rounded hover:bg-gray-50">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={settings[setting.id as keyof typeof settings]}
                    onChange={(e) => onChange({ ...settings, [setting.id]: e.target.checked })}
                    className="w-4 h-4 text-primary rounded border-gray-300 focus:ring-blue-500"
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{setting.label}</p>
                    <p className="text-xs text-gray-500">{setting.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <h4 className="text-sm font-medium">Data Rights</h4>
          <div className="flex gap-2">
            <button
              onClick={() => handleDataRequest('access')}
              className="flex-1 px-4 py-2 border border-input rounded hover:bg-accent text-sm"
            >
              <Zap className="w-4 h-4 mr-2" />
              Data Access Request
            </button>
            <button
              onClick={() => handleDataRequest('erasure')}
              className="px-4 py-2 border border-destructive text-destructive rounded hover:bg-destructive/10"
            >
              <Trash2 className="w-4 h-4" />
              Request Data Deletion
            </button>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleDataRequest('portability')}
              className="flex-1 px-4 py-2 border border-input rounded hover:bg-accent text-sm"
            >
              <Download className="w-4 h-4" />
              Download My Data
            </button>
          </div>
        </div>

        <div className="p-4 bg-muted/50 rounded-lg">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium">Data Retention:</span> We retain your data for up to 2 years after account closure.
          </p>
          <p className="text-xs text-muted-foreground">
            <span className="font-medium">Data Location:</span> All data is stored in EU-based data centers.
          </p>
          <p className="text-xs text-muted-foreground">
            <span className="font-medium">Right to Object:</span>
            You have the right to object to processing based on legitimate interests.
          </p>
        </div>
      </div>
    </div>
  );
}

export default GDPRPanel;
