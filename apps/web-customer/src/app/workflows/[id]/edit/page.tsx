'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAppStore } from '@/store';
import { api } from '@/lib/api';
import { WorkflowBuilder } from '@/components/workflow/workflow-builder';
import { WorkflowDefinition } from '@/types';
import { ChevronLeft, Save, Play } from 'lucide-react';
import toast from 'react-hot-toast';

export default function WorkflowEditPage() {
  const params = useParams();
  const router = useRouter();
  const { setLoading } = useAppStore();
  const workflowId = params.id as string;
  const [workflow, setWorkflow] = useState<WorkflowDefinition | null>(null);
  const [loading, setLocalLoading] = useState(true);

  useEffect(() => {
    loadWorkflow();
  }, [workflowId]);

  async function loadWorkflow() {
    setLocalLoading(true);
    setLoading(true);
    try {
      const data = await api.getWorkflow(workflowId);
      setWorkflow(data);
    } catch (error) {
      toast.error('Failed to load workflow');
      router.push('/workflows');
    } finally {
      setLocalLoading(false);
      setLoading(false);
    }
  }

  async function handleSave(data: Partial<WorkflowDefinition>) {
    try {
      await api.updateWorkflow(workflowId, data);
      toast.success('Workflow saved');
      // Reload to get updated version
      loadWorkflow();
    } catch (error) {
      toast.error('Failed to save workflow');
    }
  }

  async function handlePublish() {
    try {
      await api.publishWorkflow(workflowId);
      toast.success('Workflow published');
      loadWorkflow();
    } catch (error) {
      toast.error('Failed to publish workflow');
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!workflow) {
    return null;
  }

  return (
    <WorkflowBuilder
      workflowId={workflowId}
      initialWorkflow={workflow}
      onSave={handleSave}
      onBack={() => router.push('/workflows')}
    />
  );
}