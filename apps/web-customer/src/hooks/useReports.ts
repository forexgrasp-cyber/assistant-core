'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  ReportDefinition,
  ReportRun,
  ReportSchedule,
  ReportTemplate,
  ReportStatus,
  RunStatus,
  ExportFormat,
} from '@/types';

// ============================================================================
// Reports
// ============================================================================

export function useReports(params?: { status?: ReportStatus; vertical?: string; client_id?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => api.listReports(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useReport(reportId: string) {
  return useQuery({
    queryKey: ['report', reportId],
    queryFn: () => api.getReport(reportId),
    enabled: !!reportId,
  });
}

export function useCreateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { name: string; description?: string; template_id?: string; overrides?: any; client_ids?: string[] }) =>
      api.createReport(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
    onError: (error: any) => {
      console.error('Failed to create report:', error);
    },
  });
}

export function useUpdateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ reportId, data }: { reportId: string; data: Partial<ReportDefinition> }) =>
      api.updateReport(reportId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

export function useDeleteReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (reportId: string) => api.deleteReport(reportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

// ============================================================================
// Report Runs
// ============================================================================

export function useReportRuns(reportId: string, params?: { status?: RunStatus; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ['reportRuns', reportId, params],
    queryFn: () => api.listReportRuns(reportId, params),
    enabled: !!reportId,
  });
}

export function useReportRun(reportId: string, runId: string) {
  return useQuery({
    queryKey: ['reportRun', reportId, runId],
    queryFn: () => api.getReportRun(reportId, runId),
    enabled: !!reportId && !!runId,
  });
}

export function useRunReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ reportId, options }: { reportId: string; options?: any }) =>
      api.runReport(reportId, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reportRuns'] });
    },
    onError: (error: any) => {
      console.error('Failed to run report:', error);
    },
  });
}

export function useDownloadReport() {
  return useMutation({
    mutationFn: ({ reportId, runId, format }: { reportId: string; runId: string; format: ExportFormat }) =>
      api.downloadReport(reportId, runId, format),
    onSuccess: (blob, { format }) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${Date.now()}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    },
    onError: (error: any) => {
      console.error('Download failed:', error);
    },
  });
}

// ============================================================================
// Schedules
// ============================================================================

export function useSchedules(params?: { report_id?: string; active_only?: boolean }) {
  return useQuery({
    queryKey: ['schedules', params],
    queryFn: () => api.listSchedules(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: any) => api.createSchedule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
  });
}

export function usePauseSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (scheduleId: string) => api.pauseSchedule(scheduleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
  });
}

export function useResumeSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (scheduleId: string) => api.resumeSchedule(scheduleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
  });
}

export function useDeleteSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (scheduleId: string) => api.deleteSchedule(scheduleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
  });
}

export function useTriggerSchedule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (scheduleId: string) => api.triggerSchedule(scheduleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
  });
}

// ============================================================================
// Templates
// ============================================================================

export function useTemplates(params?: { category?: string; vertical?: string }) {
  return useQuery({
    queryKey: ['templates', params],
    queryFn: () => api.listTemplates(params),
    staleTime: 10 * 60 * 1000,
  });
}

export function useTemplate(templateId: string) {
  return useQuery({
    queryKey: ['template', templateId],
    queryFn: () => api.getTemplate(templateId),
    enabled: !!templateId,
  });
}

// ============================================================================
// Analytics
// ============================================================================

export function useDashboard(clientId?: string | null, days: number = 30) {
  return useQuery({
    queryKey: ['dashboard', clientId, days],
    queryFn: () => api.getDashboard({ client_id: clientId || undefined, days }),
    enabled: true,
    staleTime: 2 * 60 * 1000,
  });
}

export function useChannelBreakdown(clientId?: string | null, days: number = 30) {
  return useQuery({
    queryKey: ['channelBreakdown', clientId, days],
    queryFn: () => api.getChannelBreakdown({ client_id: clientId || undefined, days }),
    staleTime: 2 * 60 * 1000,
  });
}

export function useCohorts(clientId?: string | null, months: number = 12) {
  return useQuery({
    queryKey: ['cohorts', clientId, months],
    queryFn: () => api.getCohorts({ client_id: clientId || undefined, months }),
    enabled: true,
    staleTime: 5 * 60 * 1000,
  });
}

export function useRFM(clientId?: string | null) {
  return useQuery({
    queryKey: ['rfm', clientId],
    queryFn: () => api.getRFM({ client_id: clientId || undefined }),
    enabled: true,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAttribution(clientId?: string | null, days: number = 30) {
  return useQuery({
    queryKey: ['attribution', clientId, days],
    queryFn: () => api.getAttribution({ client_id: clientId || undefined, days }),
    enabled: true,
    staleTime: 5 * 60 * 1000,
  });
}

export function usePredictive(clientId?: string | null) {
  return useQuery({
    queryKey: ['predictive', clientId],
    queryFn: () => api.getPredictive({ client_id: clientId || undefined }),
    enabled: true,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAnomalies(clientId?: string | null, status: string = 'open', days: number = 30) {
  return useQuery({
    queryKey: ['anomalies', clientId, status, days],
    queryFn: () => api.getAnomalies({ client_id: clientId || undefined, status, days }),
    enabled: true,
    staleTime: 2 * 60 * 1000,
  });
}

export function useRealtime(clientId?: string | null) {
  return useQuery({
    queryKey: ['realtime', clientId],
    queryFn: () => api.getRealtime({ client_id: clientId || undefined }),
    staleTime: 60 * 1000,
  });
}

// ============================================================================
// Metadata
// ============================================================================

export function useWidgetTypes() {
  return useQuery({
    queryKey: ['widgetTypes'],
    queryFn: () => api.getWidgetTypes(),
    staleTime: 30 * 60 * 1000,
  });
}

export function useDataSources() {
  return useQuery({
    queryKey: ['dataSources'],
    queryFn: () => api.getDataSources(),
    staleTime: 30 * 60 * 1000,
  });
}

export function useExportFormats() {
  return useQuery({
    queryKey: ['exportFormats'],
    queryFn: () => api.getExportFormats(),
    staleTime: 30 * 60 * 1000,
  });
}
