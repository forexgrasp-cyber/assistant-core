'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
  Node,
  Edge,
  useReactFlow,
  addEdge,
  Connection,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  MarkerType,
  Background,
  Controls,
  MiniMap,
  NodeTypes,
  EdgeTypes,
} from 'react-flow-renderer';
import { X, Save, Play, Undo, Redo, ZoomIn, ZoomOut, RotateCcw, Trash2, Download, Upload, AlignLeft, AlignCenter, AlignRight, LayoutDashboard, Settings, ChevronLeft, ChevronRight, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { NodePalette } from './node-palette';
import { PropertiesPanel } from './properties-panel';
import { TriggersPanel } from './triggers-panel';
import { SettingsPanel } from './settings-panel';
import { WorkflowNode, WorkflowEdge, WorkflowTrigger, WorkflowSettings, WorkflowViewport, WorkflowDefinition } from '@/types';
import { nodeTypes } from './custom-nodes';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

const Panel = ({ position, children, className }: { position: string; children: React.ReactNode; className?: string }) => {
  const positions: Record<string, string> = {
    'top-right': 'top-4 right-4',
    'right': 'right-4 top-1/2 -translate-y-1/2',
    'left': 'left-4 top-1/2 -translate-y-1/2',
    'bottom': 'bottom-4 left-1/2 -translate-x-1/2',
  };
  return (
    <div className={cn('fixed z-50', positions[position], className)}>
      <div className="bg-card border border-border rounded-lg shadow-lg p-4 min-w-[200px] max-w-[400px] max-h-[80vh] overflow-auto">
        {children}
      </div>
    </div>
  );
};

const initialNodes: Node<WorkflowNode['data']>[] = [];
const initialEdges: Edge<WorkflowEdge['data']>[] = [];

interface WorkflowBuilderProps {
  workflowId?: string;
  initialWorkflow?: WorkflowDefinition;
  onSave?: (workflow: Partial<WorkflowDefinition>) => Promise<void>;
  onBack?: () => void;
}

export function WorkflowBuilder({
  workflowId,
  initialWorkflow,
  onSave,
  onBack,
}: WorkflowBuilderProps) {
  const [nodes, setNodes] = useState<Node<WorkflowNodeData>[]>(initialNodes);
  const [edges, setEdges] = useState<Edge<WorkflowEdge['data']>[]>(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node<WorkflowNodeData> | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [viewport, setViewport] = useState({ x: 0, y: 0, zoom: 1 });
  const [showTriggers, setShowTriggers] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [history, setHistory] = useState<Array<{ nodes: Node[]; edges: Edge[] }>>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [triggers, setTriggers] = useState<WorkflowTrigger[]>([]);
  const [settings, setSettings] = useState<WorkflowSettings>({
    concurrencyLimit: 10,
    timeoutSeconds: 3600,
    retryPolicy: { maxRetries: 3, backoffSeconds: 60 },
    errorHandling: 'stop',
    notifications: { onFailure: [], onSuccess: [] },
  });
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { getNodes, getEdges, setViewport: setRFViewport, fitView, project } = useReactFlow();

  const pushHistory = useCallback((newNodes: Node[], newEdges: Edge[]) => {
    setHistory(prev => {
      const newHistory = prev.slice(0, historyIndex + 1);
      newHistory.push({ nodes: newNodes, edges: newEdges });
      return newHistory.slice(-50);
    });
    setHistoryIndex(prev => Math.min(prev + 1, 49));
  }, [getEdges, historyIndex]);

  const handleNodesChange = (changes: NodeChange[]) => {
    setNodes(prev => applyNodeChanges(changes, prev));
  };

  const handleEdgesChange = (changes: EdgeChange[]) => {
    setEdges(prev => applyEdgeChanges(changes, prev));
  };

  const handleConnect = (connection: Connection) => {
    setEdges(prev => addEdge({ ...connection, type: 'smoothstep', animated: true, markerEnd: { type: MarkerType.ArrowClosed } }, prev));
  };

  const handleNodeClick = (_: unknown, node: Node) => {
    setSelectedNode(node);
  };

  const handlePaneClick = () => {
    setSelectedNode(null);
  };

  const handleAddNode = (nodeType: string, position: { x: number; y: number }) => {
    const flowPosition = project(position);
    const paletteItem = NODE_PALETTE_ITEMS.find(p => p.type === nodeType);
    if (!paletteItem) return;

    const newNode: Node<WorkflowNode['data']> = {
      id: `${nodeType}-${Date.now()}`,
      type: (paletteItem.type === 'condition' ? 'condition' : paletteItem.type === 'delay' ? 'delay' : 'action') as 'action' | 'condition' | 'delay',
      position: flowPosition,
      data: {
        label: paletteItem.label,
        description: paletteItem.description,
        service: paletteItem.service as 'custom' | 'analytics' | 'engagement' | 'ecommerce' | 'reporting',
        action: paletteItem.action,
        config: {},
        color: paletteItem.color,
      },
    };

    setNodes(prev => {
      const updated = [...prev, newNode];
      pushHistory(updated, getEdges());
      return updated;
    });
    setSelectedNode(newNode);
  }, [getEdges, pushHistory, project]);

  const handleUpdateNode = (nodeId: string, data: Partial<WorkflowNode['data']>) => {
    setNodes(prev => prev.map(n => n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n));
  };

  const handleDeleteNode = (nodeId: string) => {
    setNodes(prev => prev.filter(n => n.id !== nodeId));
    setEdges(prev => prev.filter(e => e.source !== nodeId && e.target !== nodeId));
    setSelectedNode(null);
  };

  const handleDuplicateNode = (node: Node) => {
    const newNode: Node = {
      ...node,
      id: `${node.id}-copy-${Date.now()}`,
      position: { x: node.position.x + 20, y: node.position.y + 20 },
    };
    setNodes(prev => {
      const updated = [...prev, newNode];
      pushHistory(updated, getEdges());
      return updated;
    });
    setSelectedNode(newNode);
  };

  const handleTestRunNode = async (node: Node) => {
    toast('Test run functionality coming soon', { icon: '🧪' });
  };

  const handleSave = async () => {
    if (!onSave) return;
    setIsSaving(true);
    try {
      await onSave({
        nodes: nodes.map(n => ({
          id: n.id,
          type: n.type as WorkflowNode['type'],
          name: n.data.label,
          position: n.position,
          data: n.data,
        })),
        edges: edges.map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          sourceHandle: e.sourceHandle ?? undefined,
          targetHandle: e.targetHandle ?? undefined,
          type: e.type as WorkflowEdge['type'],
          animated: e.animated,
          label: e.label as string | undefined,
          data: e.data,
        })),
        viewport,
        triggers,
        settings,
      });
      toast.success('Workflow saved');
    } catch (error) {
      toast.error('Failed to save workflow');
    } finally {
      setIsSaving(false);
    }
  };

  const handleExecute = async () => {
    if (!workflowId) {
      toast.error('Save workflow first');
      return;
    }
    setIsExecuting(true);
    try {
      const result = await api.post(`/workflows/${workflowId}/execute`, {});
      toast.success('Workflow execution started');
    } catch (error) {
      toast.error('Failed to execute workflow');
    } finally {
      setIsExecuting(false);
    }
  };

  const undo = () => {
    if (historyIndex > 0) {
      const prev = history[historyIndex - 1];
      setNodes(prev.nodes);
      setEdges(prev.edges);
      setHistoryIndex(prev => prev - 1);
    }
  };

  const redo = () => {
    if (historyIndex < history.length - 1) {
      const next = history[historyIndex + 1];
      setNodes(next.nodes);
      setEdges(next.edges);
      setHistoryIndex(prev => prev + 1);
    }
  };

  const exportWorkflow = () => {
    const data = { nodes, edges, viewport, triggers, settings };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = url;
    a.download = 'workflow.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Node Palette */}
      <NodePalette onAddNode={handleAddNode} />

      {/* Main Canvas */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Top Toolbar */}
        <div className="h-12 bg-card border-b border-border flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            {onBack && (
              <button onClick={onBack} className="p-2 hover:bg-accent rounded transition-colors">
                <ChevronLeft className="w-4 h-4" />
              </button>
            )}
            <h2 className="font-semibold text-lg">Workflow Builder</h2>
            {workflowId && <span className="text-xs text-muted-foreground px-2 py-0.5 bg-muted rounded">ID: {workflowId.slice(0, 8)}</span>}
          </div>
          <div className="flex items-center gap-1">
            <button onClick={undo} disabled={historyIndex <= 0} className="p-2 hover:bg-accent rounded transition-colors disabled:opacity-50" title="Undo">
              <Undo className="w-4 h-4" />
            </button>
            <button onClick={redo} disabled={historyIndex >= history.length - 1} className="p-2 hover:bg-accent rounded transition-colors disabled:opacity-50" title="Redo">
              <Redo className="w-4 h-4" />
            </button>
            <div className="w-px h-6 bg-border mx-1" />
            <button onClick={() => setRFViewport(v => ({ ...v, zoom: Math.min(v.zoom * 1.2, 2) }))} className="p-2 hover:bg-accent rounded transition-colors" title="Zoom In">
              <ZoomIn className="w-4 h-4" />
            </button>
            <button onClick={() => setRFViewport((v: { x: number; y: number; zoom: number }) => ({ ...v, zoom: Math.max(v.zoom / 1.2, 0.1) }))} className="p-2 hover:bg-accent rounded transition-colors" title="Zoom Out">
              <ZoomOut className="w-4 h-4" />
            </button>
            <button onClick={() => fitView()} className="p-2 hover:bg-accent rounded transition-colors" title="Fit View">
              <RotateCcw className="w-4 h-4" />
            </button>
            <div className="w-px h-6 bg-border mx-1" />
            <button onClick={exportWorkflow} className="px-3 py-1.5 text-sm border border-input rounded hover:bg-accent transition-colors flex items-center gap-1" title="Export">
              <Download className="w-4 h-4" />
              Export
            </button>
            <button onClick={handleSave} disabled={isSaving} className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors flex items-center gap-1 disabled:opacity-50">
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save'}
            </button>
            <button onClick={handleExecute} disabled={isExecuting || !workflowId} className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 transition-colors flex items-center gap-1 disabled:opacity-50">
              <Play className="w-4 h-4" />
              {isExecuting ? 'Running...' : 'Execute'}
            </button>
          </div>
        </div>

        {/* React Flow Canvas */}
        <div className="flex-1 relative" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={handleConnect}
            onNodeClick={handleNodeClick}
            onPaneClick={handlePaneClick}
            nodeTypes={nodeTypes as NodeTypes}
            fitView={false}
            defaultZoom={1}
            defaultPosition={[0, 0]}
            snapToGrid={true}
            snapGrid={[20, 20]}
          >
            <Background color="#e5e7eb" gap={20} size={1} />
            <Controls />
            <MiniMap nodeColor={({ data }: any) => data?.color || '#6b7280'} nodeStrokeWidth={1.5} />
          </ReactFlow>

          {/* Sidebar Panels */}
          <div className="absolute top-4 right-4 flex flex-col gap-2 z-50">
            <div className="fixed top-4 right-4 z-50">
              <div className="bg-card border border-border rounded-lg shadow-lg p-4 min-w-[200px] max-w-[400px] max-h-[80vh] overflow-auto">
                <div className="flex gap-1 p-2 bg-card border border-border rounded-lg shadow-lg">
                  <button
                    onClick={() => setShowTriggers(!showTriggers)}
                    className={cn('p-2 rounded transition-colors', showTriggers && 'bg-primary text-primary-foreground')}
                    title="Triggers"
                  >
                    <Zap className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setShowSettings(!showSettings)}
                    className={cn('p-2 rounded transition-colors', showSettings && 'bg-primary text-primary-foreground')}
                    title="Settings"
                  >
                    <Settings className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {showTriggers && (
                <div className="fixed right-4 top-44 w-80 max-h-[60vh]">
                  <div className="bg-card border border-border rounded-lg shadow-lg p-4 min-w-[200px] max-w-[400px] max-h-[80vh] overflow-auto">
                    <TriggersPanel triggers={triggers} onChange={setTriggers} />
                  </div>
                </div>
              )}
              {showSettings && (
                <div className="fixed right-4 top-44 w-80 max-h-[60vh]">
                  <div className="bg-card border border-border rounded-lg shadow-lg p-4 min-w-[200px] max-w-[400px] max-h-[80vh] overflow-auto">
                    <SettingsPanel settings={settings} onChange={setSettings} />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
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
  WorkflowBuilder: WorkflowBuilder,
  NODE_PALETTE_ITEMS,
};
