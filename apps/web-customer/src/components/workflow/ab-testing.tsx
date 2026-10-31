'use client';

import { useState } from 'react';
import { RotateCcw, Save, Play, Plus, Trash2, AlertTriangle, CheckCircle, XCircle, Bell, Mail, Slack } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkflowSettings } from '@/types';

interface Experiment {
  id: string;
  name: string;
  description: string;
  status: 'draft' | 'running' | 'completed' | 'paused';
  variants: Array<{ id: string; name: string; traffic: number }>;
  metrics: Array<{ name: string; valueA: number; valueB: number; lift: number }>;
}

interface ExperimentProps {
  experiments: Experiment[];
  onChange: (experiments: Experiment[]) => void;
}

export function ExperimentsPanel({ experiments, onChange }: ExperimentProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newExperiment, setNewExperiment] = useState<Partial<Experiment>>({
    name: '',
    description: '',
    variants: [
      { id: 'control', name: 'Control', traffic: 50 },
      { id: 'treatment', name': 'Treatment', traffic: 50 },
    ],
  });

  const handleCreateExperiment = () => {
    const experiment = {
      id: `experiment-${Date.now()}`,
      name: newExperiment.name || 'A/B Test',
      description: newExperiment.description || '',
      status: 'draft',
      variants: newExperiment.variants || [{ id: 'control', name: 'Control', traffic: 50 }, { id: 'treatment', name: 'Treatment', traffic: 50 }],
      metrics: [],
    };
    onChange([...experiments, experiment]);
    setShowAddModal(false);
    setNewExperiment({ id: '', name: '', description: '', variants: [] });
  };

  const handleDeleteExperiment = (id: string) => {
    onChange(experiments.filter(e => e.id !== id));
  };

  return (
    <div className="bg-card border border-border rounded-lg shadow-lg p-4 min-w-[320px] max-w-[400px] max-h-[80vh] overflow-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">A/B Testing</h3>
        <button
          onClick={() => setShowAddModal(true)}
          className="p-2 hover:bg-accent rounded transition-colors"
          title="Add Experiment"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {experiments.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p className="mb-2">No experiments configured</p>
          <p className="text-sm">Click + to add an experiment</p>
        </div>
      ) : (
        <div className="space-y-3">
          {experiments.map(exp => (
            <div key={experiment.id} className="border rounded-lg p-3 transition-colors">
              <div className="flex items-start gap-3">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={exp.name}
                    onChange={e => {
                      const updated = [...experiments];
                      const idx = updated.findIndex(e => e.id === exp.id);
                      if (updated[idx]) updated[idx].name = e.target.value;
                      onChange(updated);
                    }}
                    className="flex-1 bg-transparent border-none text-sm font-medium"
                  />
                </div>
                <div className="flex items-center gap-1.5 text-sm">
                  <input
                    type="checkbox"
                    checked={exp.status === 'running'}
                    onChange={(e) => {
                      const updated = [...experiments];
                      const idx = updated.findIndex(e => e.id === exp.id);
                      if (updated[idx]) updated[idx].status = e.target.checked ? 'running' : 'stopped';
                      onChange(updated);
                    }}
                    className="rounded text-primary"
                  />
                  {exp.status === 'running' ? 'Running' : 'Draft'}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => {
                      const updated = [...experiments];
                      const idx = updated.findIndex(e => e.id === exp.id);
                      if (updated[idx]) updated[idx].conversions++;
                      onChange(updated);
                    }}
                    className="p-1 hover:bg-accent rounded text-sm text-green-600"
                    title="Increment conversion"
                  >
                    <CheckCircle className="w-3 h-3 text-green-600" />
                  </button>
                  <button
                    onClick={() => {
                      const updated = [...experiments];
                      const idx = updated.findIndex(e => e.id === exp.id);
                      if (updated[idx]) updated[idx].impressions++;
                      onChange(updated);
                    }}
                    className="p-1 hover:bg-accent rounded text-sm text-muted-foreground"
                    title="Increment impression"
                  >
                    <Eye className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => {
                      const updated = [...experiments];
                      const idx = updated.findIndex(e => e.id === exp.id);
                      if (updated[idx]) updated[idx].conversionRate = updated[idx].impressions > 0 ? (updated[idx].conversions / updated[idx].impressions) * 100 : 0;
                      onChange(updated);
                    }}
                    className="p-1 hover:bg-accent rounded text-sm text-muted-foreground"
                    title="Recalculate conversion rate"
                  >
                    <RotateCcw className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
