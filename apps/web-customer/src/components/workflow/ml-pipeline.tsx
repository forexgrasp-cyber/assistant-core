'use client';

import { useState } from 'react';
import { Chart as ChartIcon, Play, Undo, Redo, Save, Upload, Download, Share2, Plus, Trash2, Settings, Brain, Signal, Activity, Clock } from 'lucide-react';

interface MLPipelineProps {
  workflowId?: string;
}

export function MLPipeline({ workflowId }: MLPipelineProps) {
  const [showBuilder, setShowBuilder] = useState(false);

  const modelTypes = [
    { id: 'regression', label: 'Regression', icon: <Activity className="w-4 h-4" /> },
    { id: 'classification', label: 'Classification', icon: <Zap className="w-4 h-4" /> },
    { type: 'clustering', label: 'Clustering', icon: <Layers className="w-4 h-4" /> },
    { type: 'forecasting', label: 'Forecasting', icon: <ChartIcon className="w-4 h-4" /> },
    { type: 'nlp', label: 'NLP', icon: <Zap className="w-4 h-4" /> },
    { type: 'cv', label: 'Computer Vision', icon: <Zap className="w-4 h-4" /> },
  ];

  return (
    <div className="bg-card border border-border rounded-lg shadow-lg p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-600" />
          <h3 className="font-semibold">ML Pipeline</h3>
        </div>
        <button
          onClick={() => {}}
          className="p-2 hover:bg-accent rounded transition-colors"
          title="Add Model"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-card/50 border border-dashed rounded-lg p-4">
              <div className="flex items-center justify-center w-full h-24">
                <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600">
                  <span className="text-lg">📊</span>
                </div>
              </div>
              <div className="mt-3 text-center">
                <h4 className="text-sm font-medium">Data Source</h4>
                <p className="text-xs text-muted-foreground">Select data source</p>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <label className="text-sm font-medium mb-2 block">Model Type</label>
          <select
            value="analytics"
            onChange={() => {}}
            className="w-full px-3 py-2 border border-input rounded bg-background"
          >
            {[
              { id: 'analytics', label: 'Analytics Model' },
              { id: 'prediction', label: 'Prediction Model' },
              { type: 'segmentation', label: 'Segmentation Model' },
            ].map(item => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={() => {}}
            className="px-4 py-2 border border-input rounded hover:bg-accent"
          >
            Cancel
          </button>
          <button
            onClick={() => {}}
            className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
          >
            Run Pipeline
          </button>
        </div>
      </div>
    </div>
  );
}