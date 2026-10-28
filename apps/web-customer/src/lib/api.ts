/**
 * API Client for Retention Analytics Platform
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type {
  ReportDefinition,
  ReportTemplate,
  ReportRun,
  ReportSchedule,
  WidgetDefinition,
  DataSourceConfig,
  ExportFormat,
  ReportStatus,
  RunStatus,
  QueryResult,
  PaginatedResponse,
  RenderedReport,
  OutputFile,
  DashboardData,
  CohortData,
  RFMSegment,
  AttributionData,
  PredictiveMetrics,
  AnomalyEvent,
  RealtimeMetrics,
  WorkflowDefinition,
  WorkflowExecution,
  WorkflowTriggerDto,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Request interceptor for auth
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add auth token if available
        const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Handle unauthorized - redirect to login
          if (typeof window !== 'undefined') {
            localStorage.removeItem('auth_token');
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // ========================================================================
  // Generic methods (auth, etc.)
  // ========================================================================

  async post(path: string, data?: any): Promise<any> {
    const response = await this.client.post(path, data);
    return response;
  }

  async get(path: string, params?: any): Promise<any> {
    const response = await this.client.get(path, { params });
    return response;
  }

  async delete(path: string): Promise<any> {
    const response = await this.client.delete(path);
    return response;
  }

  // ========================================================================
  // Templates
  // ========================================================================

  async listTemplates(params?: { category?: string; vertical?: string }): Promise<ReportTemplate[]> {
    const response = await this.client.get('/templates', { params });
    return response.data;
  }

  async getTemplate(templateId: string): Promise<ReportTemplate> {
    const response = await this.client.get(`/templates/${templateId}`);
    return response.data;
  }

  // ========================================================================
  // Reports
  // ========================================================================

  async createReport(data: Partial<ReportDefinition> & { template_id?: string; overrides?: any; client_ids?: string[] }): Promise<{ id: string; name: string; status: ReportStatus }> {
    const response = await this.client.post('/reports', data);
    return response.data;
  }

  async listReports(params?: {
    status?: ReportStatus;
    vertical?: string;
    client_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<ReportDefinition>> {
    const response = await this.client.get('/reports', { params });
    return response.data;
  }

  async getReport(reportId: string): Promise<ReportDefinition> {
    const response = await this.client.get(`/reports/${reportId}`);
    return response.data;
  }

  async updateReport(reportId: string, data: Partial<ReportDefinition>): Promise<ReportDefinition> {
    const response = await this.client.patch(`/reports/${reportId}`, data);
    return response.data;
  }

  async deleteReport(reportId: string): Promise<void> {
    await this.client.delete(`/reports/${reportId}`);
  }

  async runReport(reportId: string, options?: {
    parameters?: Record<string, any>;
    filters?: any[];
    date_range?: { start: string; end: string };
    formats?: ExportFormat[];
  }): Promise<ReportRun> {
    const response = await this.client.post(`/reports/${reportId}/run`, options);
    return response.data;
  }

  async listReportRuns(reportId: string, params?: {
    status?: RunStatus;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<ReportRun>> {
    const response = await this.client.get(`/reports/${reportId}/runs`, { params });
    return response.data;
  }

  async getReportRun(reportId: string, runId: string): Promise<ReportRun> {
    const response = await this.client.get(`/reports/${reportId}/runs/${runId}`);
    return response.data;
  }

  async downloadReport(reportId: string, runId: string, format: ExportFormat): Promise<Blob> {
    const response = await this.client.get(
      `/reports/${reportId}/runs/${runId}/download/${format}`,
      { responseType: 'blob' }
    );
    return response.data;
  }

  // ========================================================================
  // Schedules
  // ========================================================================

  async createSchedule(data: {
    report_id: string;
    cron_expression: string;
    timezone?: string;
    start_date?: string;
    end_date?: string;
    default_parameters?: Record<string, any>;
    recipients?: string[];
    slack_channels?: string[];
    webhook_urls?: string[];
  }): Promise<ReportSchedule> {
    const response = await this.client.post('/schedules', data);
    return response.data;
  }

  async listSchedules(params?: { report_id?: string; active_only?: boolean }): Promise<ReportSchedule[]> {
    const response = await this.client.get('/schedules', { params });
    return response.data;
  }

  async triggerSchedule(scheduleId: string): Promise<{ run_id: string }> {
    const response = await this.client.post(`/schedules/${scheduleId}/trigger`);
    return response.data;
  }

  async pauseSchedule(scheduleId: string): Promise<void> {
    await this.client.post(`/schedules/${scheduleId}/pause`);
  }

  async resumeSchedule(scheduleId: string): Promise<void> {
    await this.client.post(`/schedules/${scheduleId}/resume`);
  }

  async deleteSchedule(scheduleId: string): Promise<void> {
    await this.client.delete(`/schedules/${scheduleId}`);
  }

  // ========================================================================
  // Ad-hoc Queries
  // ========================================================================

  async executeQuery(data: {
    source: DataSourceConfig;
    client_ids?: string[];
    date_range?: Record<string, any>;
  }): Promise<QueryResult> {
    const response = await this.client.post('/query', data);
    return response.data;
  }

  // ========================================================================
  // Scheduler
  // ========================================================================

  async getSchedulerStatus(): Promise<any> {
    const response = await this.client.get('/scheduler/status');
    return response.data;
  }

  async getUpcomingRuns(hours: number = 24): Promise<any[]> {
    const response = await this.client.get('/scheduler/upcoming', { params: { hours } });
    return response.data.runs;
  }

  // ========================================================================
  // Metadata
  // ========================================================================

  async getWidgetTypes(): Promise<any[]> {
    const response = await this.client.get('/meta/widget-types');
    return response.data.widget_types;
  }

  async getDataSources(): Promise<any[]> {
    const response = await this.client.get('/meta/data-sources');
    return response.data.data_sources;
  }

  async getExportFormats(): Promise<any[]> {
    const response = await this.client.get('/meta/export-formats');
    return response.data.formats;
  }

  async getVerticals(): Promise<any[]> {
    const response = await this.client.get('/verticals');
    return response.data.verticals;
  }

  async getVerticalMetrics(vertical: string): Promise<string[]> {
    const response = await this.client.get(`/verticals/${vertical}/metrics`);
    return response.data.metrics;
  }

  // ========================================================================
  // Analytics
  // ========================================================================

  async getDashboard(params?: { client_id?: string; days?: number }): Promise<DashboardData> {
    const response = await this.client.get('/analytics/dashboard', { params });
    return response.data;
  }

  async getCohorts(params?: { client_id?: string; months?: number }): Promise<CohortData> {
    const response = await this.client.get('/analytics/cohorts', { params });
    return response.data;
  }

  async getRFM(params?: { client_id?: string }): Promise<{ segments: RFMSegment[] }> {
    const response = await this.client.get('/analytics/rfm', { params });
    return response.data;
  }

  async getAttribution(params?: { client_id?: string; days?: number }): Promise<AttributionData> {
    const response = await this.client.get('/analytics/attribution', { params });
    return response.data;
  }

  async getPredictive(params?: { client_id?: string }): Promise<PredictiveMetrics> {
    const response = await this.client.get('/analytics/predictive', { params });
    return response.data;
  }

  async getAnomalies(params?: { client_id?: string; status?: string; days?: number }): Promise<AnomalyEvent[]> {
    const response = await this.client.get('/analytics/anomalies', { params });
    return response.data;
  }

  async getRealtime(params?: { client_id?: string }): Promise<RealtimeMetrics> {
    const response = await this.client.get('/analytics/realtime', { params });
    return response.data;
  }

  async exportAnalytics(params: { 
    client_id?: string; 
    start_date: string; 
    end_date: string; 
    format?: 'csv' | 'json' 
  }): Promise<Blob> {
    const response = await this.client.get('/analytics/export', { 
      params,
      responseType: 'blob'
    });
    return response.data;
  }

  async getChannelBreakdown(params?: { client_id?: string; days?: number }): Promise<Record<string, number>> {
    const response = await this.client.get('/analytics/channel-breakdown', { params });
    return response.data;
  }

  // ========================================================================
  // Workflows
  // ========================================================================

  async listWorkflows(params?: {
    status?: string;
    category?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<WorkflowDefinition>> {
    const response = await this.client.get('/workflows', { params });
    return response.data;
  }

  async getWorkflow(workflowId: string): Promise<WorkflowDefinition> {
    const response = await this.client.get(`/workflows/${workflowId}`);
    return response.data;
  }

  async createWorkflow(data: Partial<WorkflowDefinition>): Promise<WorkflowDefinition> {
    const response = await this.client.post('/workflows', data);
    return response.data;
  }

  async updateWorkflow(workflowId: string, data: Partial<WorkflowDefinition>): Promise<WorkflowDefinition> {
    const response = await this.client.patch(`/workflows/${workflowId}`, data);
    return response.data;
  }

  async deleteWorkflow(workflowId: string): Promise<void> {
    await this.client.delete(`/workflows/${workflowId}`);
  }

  async publishWorkflow(workflowId: string): Promise<{ version: number }> {
    const response = await this.client.post(`/workflows/${workflowId}/publish`);
    return response.data;
  }

  async executeWorkflow(workflowId: string, triggerData?: Record<string, any>, triggerSource?: string): Promise<{ executionId: string }> {
    const response = await this.client.post(`/workflows/${workflowId}/execute`, { trigger_data: triggerData, trigger_source: triggerSource });
    return response.data;
  }

  async listExecutions(workflowId: string, params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<WorkflowExecution>> {
    const response = await this.client.get(`/workflows/${workflowId}/executions`, { params });
    return response.data;
  }

  async getExecution(workflowId: string, executionId: string): Promise<WorkflowExecution> {
    const response = await this.client.get(`/workflows/${workflowId}/executions/${executionId}`);
    return response.data;
  }

  async cancelExecution(workflowId: string, executionId: string): Promise<void> {
    await this.client.post(`/workflows/${workflowId}/executions/${executionId}/cancel`);
  }

  async triggerWorkflowByEvent(eventType: string, eventData: Record<string, any>, clientId?: string): Promise<{ executions: any[] }> {
    const response = await this.client.post('/workflows/trigger', { event_type: eventType, event_data: eventData, client_id: clientId });
    return response.data;
  }

  async triggerWorkflow(workflowId: string, triggerData?: Record<string, any>): Promise<{ executionId: string }> {
    const response = await this.client.post(`/workflows/${workflowId}/trigger`, { trigger_data: triggerData });
    return response.data;
  }

  async listTriggers(workflowId: string): Promise<WorkflowTriggerDto[]> {
    const response = await this.client.get(`/workflows/${workflowId}/triggers`);
    return response.data;
  }

  async createTrigger(workflowId: string, data: Partial<WorkflowTriggerDto>): Promise<WorkflowTriggerDto> {
    const response = await this.client.post(`/workflows/${workflowId}/triggers`, data);
    return response.data;
  }

  async updateTrigger(workflowId: string, triggerId: string, data: Partial<WorkflowTriggerDto>): Promise<WorkflowTriggerDto> {
    const response = await this.client.patch(`/workflows/${workflowId}/triggers/${triggerId}`, data);
    return response.data;
  }

  async deleteTrigger(workflowId: string, triggerId: string): Promise<void> {
    await this.client.delete(`/workflows/${workflowId}/triggers/${triggerId}`);
  }
}

// Export singleton instance
export const api = new ApiClient();

// React hook for API calls
export function useApi() {
  return api;
}