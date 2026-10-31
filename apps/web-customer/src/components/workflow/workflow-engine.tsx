'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import ReactFlow, { Node, Edge, useReactFlow, addEdge, Connection, NodeChange, EdgeChange, applyNodeChanges, applyEdgeChanges, MarkerType } from 'react-flow-renderer';
import { Play, Pause, Stop, RefreshCcw, Trash2, Download, Upload, AlignLeft, AlignCenter, AlignRight, LayoutDashboard, Settings, ChevronLeft, ChevronRight, Zap, Save, Undo, Redo, ZoomIn, ZoomOut, RotateCcw, Trash2 as TrashIcon, Download as DownloadIcon, Upload as UploadIcon, AlignLeft as AlignLeftIcon, AlignCenter as AlignCenterIcon, AlignRight as AlignRightIcon, LayoutDashboard as LayoutDashboardIcon, Settings as SettingsIcon2, ChevronLeft as ChevronLeftIcon, ChevronRight as ChevronRightIcon, Zap as ZapIcon2, Mail as MailIcon, Bell, RotateCcw as RotateCcwIcon, Trash2 as TrashIcon2, Download as DownloadIcon2, Upload as UploadIcon2, AlignLeft as AlignLeftIcon2, AlignCenter as AlignCenterIcon2, AlignRight as AlignRightIcon2, LayoutDashboard as LayoutDashboardIcon2, Settings as SettingsIcon2b, ChevronLeft as ChevronLeftIcon2, ChevronRight as ChevronRightIcon2, Zap as ZapIcon2, Mail as MailIcon2, Bell as BellIcon2, RotateCcw as RotateCcwIcon2, Trash2 as TrashIcon2, Download as DownloadIcon2, Upload as UploadIcon2, AlignLeft as AlignLeftIcon3, AlignCenter as AlignCenterIcon3, AlignRight as AlignRightIcon3, LayoutDashboard as LayoutDashboardIcon3, Settings as SettingsIcon3, ChevronLeft as ChevronLeftIcon3, ChevronRight as ChevronRightIcon3, Zap as ZapIcon3, Mail as MailIcon3, Bell as BellIcon3, RotateCcw as RotateCcwIcon3, Trash2 as TrashIcon3, Download as DownloadIcon3, Upload as UploadIcon3, AlignLeft as AlignLeftIcon3, AlignCenter as AlignCenterIcon3, AlignRight as AlignRightIcon3, LayoutDashboard as LayoutDashboardIcon3, Settings as SettingsIcon3, ChevronLeft as ChevronLeftIcon3, ChevronRight as ChevronRightIcon3, Zap as ZapIcon3, Mail as MailIcon3, Bell as BellIcon3, RotateCcw as RotateCcwIcon3, Trash2 as TrashIcon3, Download as DownloadIcon3, Upload as UploadIcon3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WorkflowNode, WorkflowEdge, WorkflowTrigger, WorkflowSettings, WorkflowViewport, WorkflowDefinition } from '@/types';
import { nodeTypes } from './custom-nodes';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

interface WorkflowExecutionState {
  id: string;
  workflowId: string;
  status: 'idle' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused';
  currentNode?: string;
  completedNodes: string[];
  failedNodes: string[];
  pendingNodes: string[];
  startTime: Date | null;
  endTime: Date | null;
  duration: number;
  results: Record<string, any>;
  logs: ExecutionLog[];
  errors: ExecutionError[];
}

interface ExecutionLog {
  id: string;
  timestamp: string;
  nodeId: string;
  nodeName: string;
  status: 'info' | 'success' | 'warning' | 'error';
  message: string;
  data?: any;
}

interface ExecutionError {
  id: string;
  nodeId: string;
  nodeName: string;
  error: string;
  timestamp: string;
  retryCount: number;
  maxRetries: number;
}

interface ExecutionResult {
  id: string;
  status: 'success' | 'failure' | 'partial';
  nodesExecuted: number;
  nodesTotal: number;
  duration: number;
  output: any;
  error?: string;
}

interface WorkflowExecutionState {
  [workflowId: string]: WorkflowExecution;
}

interface WorkflowExecutorProps {
  workflowId: string;
  nodes: Node[];
  edges: Edge[];
  onExecutionComplete?: (result: ExecutionResult) => void;
  onNodeExecution: (nodeId: string, result: any) => void;
  initialState?: WorkflowExecution;
}

export function WorkflowExecutor({ workflowId, nodes, edges, onSave, onSaveComplete, onSaveError }: WorkflowBuilderProps) {
  const [isExecuting, setIsExecuting] = useState(false);
  const [execution, setExecution] = useState<WorkflowExecution | null>(null);
  const [executionLogs, setExecutionLogs] = useState<ExecutionLog[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [isCancelled, setIsCancelled] = useState(false);

  const executeWorkflow = async () => {
    if (!workflowId || nodes.length === 0) return;

    setIsExecuting(true);
    setExecution({
      id: `exec-${Date.now()}`,
      workflowId,
      status: 'running',
      currentNode: undefined,
      nodes: [],
      edges: [],
      startedAt: new Date(),
      completedAt: null,
      duration: 0,
      results: {},
      logs: [],
      errors: [],
    });

    try {
      const executionOrder = topologicalSort(nodes, edges);
      
      for (const nodeId of executionOrder) {
        if (isCancelled) break;
        
        const node = nodes.find(n => n.id === nodeId);
        if (!node) continue;

        // Check if node should execute based on conditions
        if (!shouldExecuteNode(node, executionResults)) continue;

        // Execute node
        const result = await executeNode(node, edges);
        
        if (result.success) {
          setExecution(prev => ({ ...prev, results: { ...prev.results, [node.id]: result } }));
        } else {
          // Handle error based on error handling policy
          if (settings.errorHandling === 'stop') {
            setExecution(prev => ({
              ...prev,
              status: 'failed',
              errors: [...prev.errors, { id: `err-${Date.now()}`, nodeId: node.id, node: node.data.label, error: result.error || 'Unknown error', timestamp: new Date().toISOString(), retryCount: 0, maxRetries: settings.retryPolicy.maxRetries }],
            }));
            setIsExecuting(false);
            return;
          }
          
          // For retry policy, implement retry logic
          // ... (implementation details)
        }
      }

      setExecution(prev => ({ ...prev, status: 'completed', completedAt: new Date() }));
      setIsExecuting(false);
    } catch (error) {
      console.error('Workflow execution error:', error);
      toast.error('Workflow execution failed');
      setIsExecuting(false);
    }
  };

  const executeNode = async (node: Node): Promise<{ success: boolean; result?: any; error?: string }> => {
    try {
      // Simulate node execution based on type
      switch (node.type) {
        case 'analytics_query':
          await simulateDelay(1000, 2000);
          return { success: true, result: { rows: Math.floor(Math.random() * 100) + 1 } };
        case 'engagement_email':
          await simulateDelay(500, 1500);
          return { success: true, result: { emailsSent: Math.floor(Math.random() * 100) + 1 } };
        case 'ecommerce_order':
          await simulateDelay(1000, 3000);
          return { success: true, result: { orderId: `ORD-${Date.now()}`, total: Math.random() * 1000 } };
        case 'condition':
          // Condition nodes evaluate and return true/false
          return { success: true, result: Math.random() > 0.5 };
        case 'delay':
          await simulateDelay(1000, 5000);
          return { success: true, result: { delayed: true } };
        default:
          await simulateDelay(500, 1500);
          return { success: true, result: {} };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const simulateDelay = async (min: number, max: number) => {
    const delay = Math.random() * (max - min) + min;
    await new Promise(resolve => setTimeout(resolve, delay));
  };

  const applyNodeChanges = (changes: NodeChange[]) => {
    setNodes(prev => applyNodeChanges(changes, prev));
  };

  const handleEdgesChange = (changes: EdgeChange[]) => {
    setEdges(prev => applyEdgeChanges(changes, prev));
  };

  const handleConnect = (connection: Connection) => {
    setEdges(prev => addEdge({ ...connection, type: 'smoothstep', animated: true, markerEnd: { type: MarkerType.ArrowClosed } }, prev));
  };

  // Topological sort for execution order
  const topologicalSort = (nodes: Node[], edges: Edge[]): string[] => {
    const inDegree = new Map<string, number>();
    const adjacency = new Map<string, string[]>();
    
    nodes.forEach(node => {
      inDegree.set(node.id, 0);
      adjacency.set(node.id, []);
    });
    
    edges.forEach(edge => {
      if (edge.source && edge.target) {
        adjacency.get(edge.source)?.push(edge.target);
        inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
      }
    });
    
    const queue: string[] = nodes.filter(n => (inDegree.get(n.id) || 0) === 0).map(n => n.id);
    const result: string[] = [];
    
    while (queue.length > 0) {
      const nodeId = queue.shift()!;
      result.push(nodeId);
      
      adjacency.get(nodeId)?.forEach(target => {
        inDegree.set(target, (inDegree.get(target) || 1) - 1);
        if (inDegree.get(target) === 0) {
          queue.push(target);
        }
      });
    }
    
    return result.length === nodes.length ? result : nodes.map(n => n.id);
  };

  // ... rest of component