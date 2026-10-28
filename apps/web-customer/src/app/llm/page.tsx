'use client';

import { LLMModelManagement } from '@/components/llm/model-management';
import { useAppStore } from '@/store';

export default function LLMPage() {
  const { user } = useAppStore();
  const isDev = user?.role === 'owner' || user?.role === 'admin';

  return (
    <div className="min-h-screen bg-background">
      <LLMModelManagement tenantId={user?.client_id || ''} isDev={isDev} />
    </div>
  );
}