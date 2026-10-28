/**
 * Report List Component
 */

'use client';

import { useState } from 'react';
import { Play, Download, Eye, Edit, Trash2, MoreHorizontal, Clock, CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react';
import { format } from 'date-fns';
import type { ReportDefinition, ReportRun, RunStatus, ReportStatus } from '@/types';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';

interface ReportListProps {
  reports: ReportDefinition[];
  onRun: (reportId: string) => void;
  onDownload?: (runId: string, reportId: string, format: string) => void;
  currentReport?: ReportDefinition | null;
  setCurrentReport?: (report: ReportDefinition | null) => void;
  showActions?: boolean;
}

const STATUS_COLORS: Record<ReportStatus, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  paused: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  archived: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
};

const RUN_STATUS_COLORS: Record<RunStatus, string> = {
  pending: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  queued: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  running: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 animate-pulse',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  cancelled: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400',
};

const RUN_STATUS_ICONS: Record<RunStatus, React.ReactNode> = {
  pending: <Clock className="w-4 h-4" />,
  queued: <Clock className="w-4 h-4" />,
  running: <Loader2 className="w-4 h-4 animate-spin" />,
  completed: <CheckCircle className="w-4 h-4" />,
  failed: <XCircle className="w-4 h-4" />,
  cancelled: <AlertCircle className="w-4 h-4" />,
};

export function ReportList({ 
  reports, 
  onRun, 
  onDownload, 
  currentReport, 
  setCurrentReport,
  showActions = true 
}: ReportListProps) {
  const [expandedReport, setExpandedReport] = useState<string | null>(null);
  const [runningReports, setRunningReports] = useState<Set<string>>(new Set());

  const handleRun = async (reportId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRunningReports(prev => new Set(prev).add(reportId));
    try {
      await onRun(reportId);
    } finally {
      setRunningReports(prev => {
        const next = new Set(prev);
        next.delete(reportId);
        return next;
      });
    }
  };

  const handleDownload = async (runId: string, reportId: string, format: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDownload) {
      await onDownload(runId, reportId, format);
    }
  };

  const handleRowClick = (report: ReportDefinition) => {
    if (setCurrentReport) {
      setCurrentReport(report);
    }
    setExpandedReport(prev => prev === report.id ? null : report.id);
  };

  const getLatestRun = (report: ReportDefinition): ReportRun | undefined => {
    // In real app, this would come from the API
    return undefined;
  };

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-muted/50 border-b border-border">
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Report</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden md:table-cell">Status</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Schedule</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Last Run</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Next Run</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {reports.map((report) => (
              <tr
                key={report.id}
                className={`${currentReport?.id === report.id ? 'bg-primary/5' : ''} hover:bg-accent/50 transition-colors cursor-pointer`}
                onClick={() => handleRowClick(report)}
              >
                <td className="px-4 py-3">
                  <div>
                    <p className="font-medium text-foreground truncate max-w-xs">{report.name}</p>
                    <p className="text-xs text-muted-foreground truncate max-w-xs mt-0.5">{report.description || 'No description'}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${STATUS_COLORS[report.status]}`}>
                        {report.status.charAt(0).toUpperCase() + report.status.slice(1)}
                      </span>
                      {report.vertical && (
                        <span className="px-2 py-0.5 text-xs rounded-full bg-primary/10 text-primary">
                          {report.vertical}
                        </span>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 hidden md:table-cell">
                  <ReportRunStatus reportId={report.id} runningReports={runningReports} />
                </td>
                <td className="px-4 py-3 hidden lg:table-cell">
                  {report.schedule ? (
                    <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                      {report.schedule}
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">Manual</span>
                  )}
                </td>
                <td className="px-4 py-3 hidden lg:table-cell">
                  {report.last_run_at ? format(new Date(report.last_run_at), 'MMM d, yyyy HH:mm') : (
                    <span className="text-xs text-muted-foreground">Never</span>
                  )}
                </td>
                <td className="px-4 py-3 hidden lg:table-cell">
                  {report.next_run_at ? format(new Date(report.next_run_at), 'MMM d, yyyy HH:mm') : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {showActions && (
                      <>
                        <button
                          onClick={(e) => handleRun(report.id, e)}
                          disabled={runningReports.has(report.id)}
                          className="p-1.5 border border-input rounded hover:bg-accent disabled:opacity-50 transition-colors"
                          title="Run Report"
                        >
                          {runningReports.has(report.id) ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Play className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={(e) => handleDownload('latest', report.id, 'pdf', e)}
                          className="p-1.5 border border-input rounded hover:bg-accent transition-colors"
                          title="Download PDF"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); if (setCurrentReport) setCurrentReport(report); }}
                          className="p-1.5 border border-input rounded hover:bg-accent transition-colors"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {reports.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-muted-foreground">
                  No reports found. Create your first report to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ReportRunStatus({ reportId, runningReports }: { reportId: string; runningReports: Set<string> }) {
  // In real app, this would fetch the latest run status
  const isRunning = runningReports.has(reportId);
  
  if (isRunning) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
        <Loader2 className="w-3 h-3 animate-spin" />
        Generating...
      </span>
    );
  }
  
  // Mock status - in real app would come from API
  return (
    <span className="inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
      <CheckCircle className="w-3 h-3" />
      Ready
    </span>
  );
}