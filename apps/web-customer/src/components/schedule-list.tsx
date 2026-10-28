/**
 * Schedule List Component
 */

'use client';

import { Play, Pause, Edit, Trash2, Clock, Calendar, MoreHorizontal } from 'lucide-react';
import { format } from 'date-fns';
import type { ReportSchedule, ReportDefinition } from '@/types';
import { api } from '@/lib/api';
import toast from 'react-hot-toast';
import { useState } from 'react';

interface ScheduleListProps {
  schedules?: ReportSchedule[];
  reports?: ReportDefinition[];
}

export function ScheduleList({ schedules = [], reports = [] }: ScheduleListProps) {
  const [editingSchedule, setEditingSchedule] = useState<ReportSchedule | null>(null);
  const [deletingSchedule, setDeletingSchedule] = useState<string | null>(null);

  const getReportName = (reportId: string) => {
    return reports.find(r => r.id === reportId)?.name || 'Unknown Report';
  };

  const handleTrigger = async (scheduleId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.triggerSchedule(scheduleId);
      toast.success('Report generation triggered');
    } catch (error) {
      toast.error('Failed to trigger report');
    }
  };

  const handlePause = async (scheduleId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.pauseSchedule(scheduleId);
      toast.success('Schedule paused');
    } catch (error) {
      toast.error('Failed to pause schedule');
    }
  };

  const handleResume = async (scheduleId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.resumeSchedule(scheduleId);
      toast.success('Schedule resumed');
    } catch (error) {
      toast.error('Failed to resume schedule');
    }
  };

  const handleDelete = async (scheduleId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this schedule?')) return;
    
    try {
      await api.deleteSchedule(scheduleId);
      toast.success('Schedule deleted');
    } catch (error) {
      toast.error('Failed to delete schedule');
    }
  };

  const handleEdit = (schedule: ReportSchedule) => {
    setEditingSchedule(schedule);
  };

  if (!schedules.length) {
    return (
      <div className="bg-card border border-border rounded-xl p-12 text-center">
        <Calendar className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
        <h3 className="text-lg font-semibold mb-2">No Schedules</h3>
        <p className="text-muted-foreground mb-6">Create a schedule to automatically run reports on a recurring basis.</p>
        <button className="px-4 py-2 bg-primary text-primary-foreground rounded-lg">
          Create Schedule
        </button>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-muted/50 border-b border-border">
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Schedule</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden md:table-cell">Report</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Cron Expression</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Timezone</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Next Run</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider hidden lg:table-cell">Last Run</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {schedules.map((schedule) => (
              <tr key={schedule.id} className="hover:bg-accent/50 transition-colors">
                <td className="px-4 py-3">
                  <p className="font-medium text-foreground">{schedule.id.slice(0, 8)}...</p>
                  <p className="text-xs text-muted-foreground">{schedule.cron_expression}</p>
                </td>
                <td className="px-4 py-3 hidden md:table-cell">
                  <p className="text-sm text-foreground">{getReportName(schedule.report_id)}</p>
                  <p className="text-xs text-muted-foreground">{schedule.report_id}</p>
                </td>
                <td className="px-4 py-3 hidden lg:table-cell font-mono text-sm">{schedule.cron_expression}</td>
                <td className="px-4 py-3 hidden lg:table-cell text-sm">{schedule.timezone}</td>
                <td className="px-4 py-3 hidden lg:table-cell">
                  {schedule.next_run_at ? (
                    <span className="text-sm">{format(new Date(schedule.next_run_at), 'MMM d, yyyy HH:mm')}</span>
                  ) : (
                    <span className="text-xs text-muted-foreground">Not scheduled</span>
                  )}
                </td>
                <td className="px-4 py-3 hidden lg:table-cell">
                  {schedule.last_run_at ? format(new Date(schedule.last_run_at), 'MMM d, yyyy HH:mm') : (
                    <span className="text-xs text-muted-foreground">Never</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded-full ${
                    schedule.is_active
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                  }`}>
                    {schedule.is_active ? 'Active' : 'Paused'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    {schedule.is_active ? (
                      <button
                        onClick={(e) => handlePause(schedule.id, e)}
                        className="p-1.5 border border-input rounded hover:bg-accent transition-colors"
                        title="Pause"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                    ) : (
                      <button
                        onClick={(e) => handleResume(schedule.id, e)}
                        className="p-1.5 border border-input rounded hover:bg-accent transition-colors"
                        title="Resume"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={(e) => handleTrigger(schedule.id, e)}
                      className="p-1.5 border border-input rounded hover:bg-accent transition-colors"
                      title="Run Now"
                    >
                      <Play className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleEdit(schedule)}
                      className="p-1.5 border border-input rounded hover:bg-accent transition-colors"
                      title="Edit"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => handleDelete(schedule.id, e)}
                      className="p-1.5 border border-input rounded hover:bg-accent transition-colors text-destructive"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}