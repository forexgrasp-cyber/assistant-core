/**
 * TypeScript types for the customer portal.
 * Mirrors the Python models from the reporting engine.
 */

export type UUID = string;

export type ExportFormat = 'pdf' | 'html' | 'csv' | 'json' | 'xlsx' | 'md';
export type ReportStatus = 'draft' | 'active' | 'paused' | 'archived';
export type RunStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export type WidgetType = 
  | 'line_chart' | 'bar_chart' | 'area_chart' | 'pie_chart' | 'donut_chart'
  | 'scatter_plot' | 'heatmap' | 'funnel_chart' | 'cohort_heatmap' | 'gauge'
  | 'data_table' | 'pivot_table' | 'summary_table'
  | 'kpi_card' | 'metric_card' | 'progress_bar'
  | 'markdown' | 'text_block' | 'ai_summary'
  | 'image' | 'iframe' | 'custom';

export type DataSourceType = 
  | 'daily_facts' | 'program_revenue' | 'dimension_facts' | 'payment_facts'
  | 'revenue_events' | 'usage_events' | 'custom_sql' | 'mcp_tool'
  | 'api_endpoint' | 'vertical_pack';

export interface DataSourceConfig {
  type: DataSourceType;
  metrics: string[];
  dimensions: string[];
  filters: FilterConfig[];
  date_range?: DateRangeConfig;
  group_by: string[];
  order_by: OrderByConfig[];
  limit?: number;
  query?: string;
  params?: Record<string, any>;
  tool_name?: string;
  tool_params?: Record<string, any>;
  endpoint?: string;
  method?: string;
  headers?: Record<string, string>;
  vertical?: string;
  pack_metric?: string;
}

export interface FilterConfig {
  field: string;
  operator: FilterOperator;
  value: any;
}

export type FilterOperator = 
  | 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte'
  | 'in' | 'not_in' | 'contains' | 'not_contains'
  | 'starts_with' | 'ends_with' | 'regex'
  | 'is_null' | 'is_not_null' | 'between';

export interface DateRangeConfig {
  start?: string;
  end?: string;
  days?: number;
  grain?: 'hour' | 'day' | 'week' | 'month' | 'quarter' | 'year';
}

export interface OrderByConfig {
  field: string;
  dir: 'asc' | 'desc';
}

export interface WidgetConfig {
  type: WidgetType;
  title: string;
  subtitle?: string;
  data_source: DataSourceConfig;
  transformations?: TransformationConfig[];
  width: number;
  height?: number;
  options: Record<string, any>;
  conditions?: ConditionConfig[];
  drill_down?: DrillDownConfig;
  ai_summary?: boolean;
  ai_prompt?: string;
}

export interface TransformationConfig {
  type: string;
  config: Record<string, any>;
}

export interface ConditionConfig {
  field: string;
  operator: FilterOperator;
  value: any;
}

export interface DrillDownConfig {
  target_widget_id?: string;
  target_report_id?: string;
  parameters: Record<string, any>;
}

export interface WidgetDefinition {
  id: string;
  config: WidgetConfig;
  x: number;
  y: number;
  w: number;
  h: number;
  description?: string;
  tags: string[];
}

export interface ReportSection {
  id: string;
  title: string;
  description?: string;
  widgets: WidgetDefinition[];
  content?: string;
  page_break_before: boolean;
  conditions: ConditionConfig[];
}

export interface ReportTemplate {
  id: string;
  name: string;
  description?: string;
  category?: string;
  sections: ReportSection[];
  default_filters: FilterConfig[];
  default_schedule?: string;
  default_formats: ExportFormat[];
  tags: string[];
  vertical?: string;
  is_system: boolean;
}

export interface ReportDefinition {
  id: string;
  name: string;
  description?: string;
  template_id?: string;
  sections: ReportSection[];
  filters: FilterConfig[];
  schedule?: string;
  timezone: string;
  formats: ExportFormat[];
  export_options?: ExportOptions;
  recipients: string[];
  slack_channels: string[];
  webhook_urls: string[];
  client_ids: UUID[];
  is_public: boolean;
  status: ReportStatus;
  tags: string[];
  vertical?: string;
  created_by?: UUID;
  created_at: string;
  updated_at: string;
  last_run_at?: string;
  next_run_at?: string;
}

export interface ExportOptions {
  pdf_page_size?: 'A4' | 'Letter' | 'Legal';
  pdf_orientation?: 'portrait' | 'landscape';
  pdf_margins?: { top: string; bottom: string; left: string; right: string };
  pdf_header?: string;
  pdf_footer?: string;
  pdf_toc?: boolean;
  pdf_page_numbers?: boolean;
  html_embed_assets?: boolean;
  html_standalone?: boolean;
  html_theme?: string;
  csv_delimiter?: string;
  csv_encoding?: string;
  csv_include_header?: boolean;
  timezone?: string;
  locale?: string;
  currency?: string;
  number_format?: Record<string, any>;
  date_format?: string;
  datetime_format?: string;
}

export interface ReportRun {
  id: string;
  report_id: string;
  report_name: string;
  triggered_by: 'schedule' | 'manual' | 'api' | 'webhook';
  triggered_by_user?: UUID;
  parameters: Record<string, any>;
  filters_applied: FilterConfig[];
  date_range?: { start: string; end: string };
  status: RunStatus;
  progress: number;
  current_step?: string;
  output_files: OutputFile[];
  widgets_rendered: number;
  widgets_failed: number;
  total_data_rows: number;
  render_time_ms: number;
  total_time_ms: number;
  error_message?: string;
  error_details?: Record<string, any>;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface OutputFile {
  format: ExportFormat;
  filename: string;
  path: string;
  url: string;
  size_bytes: number;
  size_human: string;
}

export interface ReportSchedule {
  id: string;
  report_id: string;
  cron_expression: string;
  timezone: string;
  start_date?: string;
  end_date?: string;
  default_parameters: Record<string, any>;
  recipients: string[];
  slack_channels: string[];
  webhook_urls: string[];
  is_active: boolean;
  last_run_at?: string;
  next_run_at?: string;
  run_count: number;
  failure_count: number;
  created_by?: UUID;
  created_at: string;
  updated_at: string;
}

export interface QueryResult {
  data: Record<string, any>[];
  columns: string[];
  row_count: number;
  execution_time_ms: number;
  query?: string;
  source: DataSourceType;
  metadata: Record<string, any>;
}

export interface RenderedWidget {
  widget_id: string;
  type: WidgetType;
  title: string;
  html?: string;
  markdown?: string;
  data?: Record<string, any>[];
  chart_config?: Record<string, any>;
  render_time_ms: number;
  data_rows: number;
  errors: string[];
  warnings: string[];
}

export interface RenderedSection {
  section_id: string;
  title: string;
  widgets: RenderedWidget[];
  content?: string;
  page_break_before: boolean;
}

export interface RenderedReport {
  report_id: string;
  run_id: string;
  name: string;
  generated_at: string;
  sections: RenderedSection[];
  total_widgets: number;
  failed_widgets: number;
  total_data_rows: number;
  total_render_time_ms: number;
  ai_summary?: string;
  export_options: ExportOptions;
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

// Dashboard types
export interface DashboardLayout {
  id: string;
  name: string;
  widgets: WidgetDefinition[];
  global_filters: FilterConfig[];
  auto_refresh_seconds?: number;
}

export interface DashboardData {
  period_days: number;
  totals: {
    revenue: number;
    orders: number;
    new_customers: number;
  };
  channel_breakdown: {
    email: number;
    sms: number;
    push: number;
    organic: number;
  };
  daily_series: Array<{
    date: string;
    revenue: number;
    orders: number;
    sessions: number;
  }>;
}

export interface CohortData {
  cohorts: Array<{
    cohort_month: string;
    cohort_size: number;
    periods: Array<{
      period: number;
      retained: number;
      repeat_rate: number;
      revenue_per_customer: number;
    }>;
  }>;
}

export interface RFMSegment {
  segment: string;
  count: number;
  total_revenue: number;
  avg_ltv: number;
}

export interface AttributionData {
  period_days: number;
  channels: Record<string, { revenue: number; touchpoints: number }>;
  total_attributed_revenue: number;
}

export interface PredictiveMetrics {
  total_customers: number;
  high_churn_risk: number;
  avg_predicted_ltv: number;
  avg_churn_probability: number;
}

export interface AnomalyEvent {
  id: string;
  metric: string;
  type: string;
  severity: string;
  expected: number;
  actual: number;
  deviation: number;
  deviation_pct: number;
  status: string;
  detected_at: string;
}

export interface RealtimeMetrics {
  date: string;
  revenue: number;
  orders: number;
  sessions: number;
  conversion_rate: number;
}

export interface ChannelBreakdown {
  email: number;
  sms: number;
  push: number;
  organic: number;
  direct: number;
  referral: number;
}

// Workflow types
export interface WorkflowNode {
  id: string;
  type: 'action' | 'condition' | 'delay' | 'branch' | 'loop' | 'subflow' | 'webhook' | 'trigger';
  name: string;
  position: { x: number; y: number };
  data: {
    label: string;
    description?: string;
    config?: Record<string, any>;
    service?: 'analytics' | 'engagement' | 'ecommerce' | 'reporting' | 'custom';
    action?: string;
    icon?: string;
    color?: string;
  };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  type?: 'default' | 'straight' | 'step' | 'smoothstep';
  animated?: boolean;
  label?: string;
  data?: Record<string, any>;
}

export interface WorkflowTrigger {
  id: string;
  name: string;
  type: 'schedule' | 'event' | 'webhook' | 'api' | 'manual';
  config: Record<string, any>;
  conditions: Array<{
    field: string;
    operator: string;
    value: any;
  }>;
  isActive: boolean;
}

export interface WorkflowSettings {
  concurrencyLimit: number;
  timeoutSeconds: number;
  retryPolicy: {
    maxRetries: number;
    backoffSeconds: number;
  };
  errorHandling: 'stop' | 'continue' | 'retry';
  notifications: {
    onFailure: string[];
    onSuccess: string[];
  };
}

export interface WorkflowViewport {
  x: number;
  y: number;
  zoom: number;
}

export interface WorkflowDefinition {
  id: string;
  name: string;
  slug: string;
  description?: string;
  category: string;
  tags: string[];
  version: number;
  status: 'draft' | 'published' | 'deprecated' | 'archived';
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  viewport: WorkflowViewport;
  triggers: WorkflowTrigger[];
  settings: WorkflowSettings;
  maxConcurrentExecutions: number;
  timeoutSeconds: number;
  maxRetries: number;
  retryBackoffSeconds: number;
  schedule?: string;
  timezone: string;
  publishedAt?: string;
  totalExecutions: number;
  successfulExecutions: number;
  failedExecutions: number;
  avgExecutionTimeMs: number;
  createdAt: string;
  updatedAt: string;
}

export interface WorkflowExecution {
  id: string;
  workflowId: string;
  workflowName: string;
  triggerType: string;
  triggerData: Record<string, any>;
  triggerSource: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'paused' | 'retrying';
  currentNodeId?: string;
  completedNodes: number;
  totalNodes: number;
  progressPercent: number;
  retryCount: number;
  error?: string;
  errorNodeId?: string;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  output: Record<string, any>;
  revenueAttributed: number;
  queuedAt?: string;
}

export interface WorkflowNodeExecution {
  id: string;
  executionId: string;
  nodeId: string;
  nodeType: string;
  nodeName?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'retrying';
  inputData: Record<string, any>;
  outputData: Record<string, any>;
  error?: string;
  attempt: number;
  maxAttempts: number;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  dependsOn: string[];
  branchCondition?: Record<string, any>;
  branchTaken?: 'true' | 'false';
}

export interface WorkflowNodeData {
  label: string;
  description?: string;
  config?: Record<string, any>;
  service?: 'analytics' | 'engagement' | 'ecommerce' | 'reporting' | 'custom';
  action?: string;
  icon?: string;
  color?: string;
  status?: 'idle' | 'running' | 'completed' | 'failed' | 'skipped';
  error?: string;
}

export interface WorkflowTriggerDto {
  id: string;
  name: string;
  type: string;
  isActive: boolean;
  config: Record<string, any>;
  totalTriggers: number;
  successfulTriggers: number;
  failedTriggers: number;
  lastTriggeredAt?: string;
}

// User/Org types
export interface User {
  id: UUID;
  email: string;
  name: string;
  avatar_url?: string;
  role: 'owner' | 'admin' | 'manager' | 'analyst' | 'viewer' | 'client';
  agency_id: UUID;
  client_id?: UUID;
  timezone: string;
  locale: string;
}

export interface Agency {
  id: UUID;
  name: string;
  slug: string;
  white_label_domain?: string;
  white_label_enabled: boolean;
  primary_color?: string;
  secondary_color?: string;
}

export interface Client {
  id: UUID;
  agency_id: UUID;
  name: string;
  slug: string;
  shop_domain?: string;
  timezone: string;
  currency: string;
  is_active: boolean;
}