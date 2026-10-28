/**
 * Dashboard Page - Main landing page
 */

'use client';

import { Suspense } from 'react';
import { DashboardContent } from './dashboard-content';
import { DashboardSkeleton } from '@/components/dashboard-skeleton';

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-background">
      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardContent />
      </Suspense>
    </div>
  );
}