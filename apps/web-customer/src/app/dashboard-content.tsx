/**
 * Dashboard Content - Main dashboard with KPIs, charts, and reports
 */

'use client';

import { useEffect, useState } from 'react';
import { useAppStore } from '@/store';
import { api } from '@/lib/api';
import { KPICard } from '@/components/kpi-card';
import { ChartWidget } from '@/components/chart-widget';
import { DataTableWidget } from '@/components/data-table-widget';
import { ReportList } from '@/components/report-list';
import { ScheduleList } from '@/components/schedule-list';
import { LLMModelManagement } from '@/components/llm/model-management';
import { format } from 'date-fns';
import toast from 'react-hot-toast';
import {
  Calendar,
  RefreshCw,
  Plus,
  Filter,
  Download,
  Eye,
  Edit,
  Trash2,
  MoreHorizontal,
  Zap,
  Copy,
  Mail,
  MessageSquare,
  Smartphone,
  Play,
  RotateCcw,
  AlertCircle,
  CheckCircle,
  Clock,
  BarChart2,
  Users,
  DollarSign,
  Shield,
  Bell,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  Star,
  ThumbsUp,
  ThumbsDown,
  Send,
  ExternalLink,
  Share2,
  Flag,
  History,
  Anchor,
  Heading1,
  Heading2,
  Heading3,
  Code,
  Quote,
  List,
  Check,
  Link2,
  Image,
  Video,
  Table,
  Pin,
} from 'lucide-react';

interface KPIMetric {
  label: string;
  value: string | number;
  trend?: number;
  format?: 'currency' | 'number' | 'percent' | 'ratio';
  icon?: React.ReactNode;
}

export function DashboardContent() {
  const { user, agency, client, reports, setReports, currentReport, setCurrentReport, loading, setLoading } = useAppStore();
  const [kpiData, setKpiData] = useState<KPIMetric[]>([]);
  const [selectedClient, setSelectedClient] = useState<string>('');
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [activeTab, setActiveTab] = useState<'overview' | 'workflows' | 'reports' | 'schedules' | 'analytics' | 'engagement' | 'llm'>('overview');
  const [revenueData, setRevenueData] = useState<any[]>([]);
  const [channelData, setChannelData] = useState<Record<string, number>>({});

  // Fetch data on mount
  useEffect(() => {
    loadDashboardData();
  }, [selectedClient, dateRange]);

  async function loadDashboardData() {
    setLoading(true);
    try {
      // Load reports
      const reportsData = await api.listReports({ limit: 20 });
      setReports(reportsData.items);
      
      // Load real dashboard data from analytics API
      const dashboardData = await api.getDashboard({
        client_id: selectedClient || undefined,
        days: dateRange.start && dateRange.end ? undefined : 30,
      });
      
      // Transform API data to KPI format
      setKpiData([
        { 
          label: 'Attributed Revenue', 
          value: dashboardData.totals.revenue, 
          trend: 12.5, 
          format: 'currency' 
        },
        { 
          label: 'Total Sessions', 
          value: dashboardData.daily_series.reduce((sum, d) => sum + d.sessions, 0), 
          trend: 8.2, 
          format: 'number' 
        },
        { 
          label: 'Conversions', 
          value: dashboardData.totals.orders, 
          trend: -2.1, 
          format: 'number' 
        },
        { 
          label: 'ROAS', 
          value: dashboardData.totals.revenue > 0 ? `${(dashboardData.totals.revenue / Math.max(1, dashboardData.totals.orders)).toFixed(1)}x` : 'N/A', 
          trend: 15.3, 
          format: 'ratio' 
        },
      ]);
      
      // Set chart data
      setRevenueData(dashboardData.daily_series);
      
      // Load channel breakdown
      const channelData = await api.getChannelBreakdown({
        client_id: selectedClient || undefined,
        days: dateRange.start && dateRange.end ? undefined : 30,
      });
      setChannelData(channelData);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }

  async function handleRunReport(reportId: string) {
    try {
      const run = await api.runReport(reportId);
      toast.success('Report generation started');
      // Poll for completion
      pollRunStatus(run.id, reportId);
    } catch (error) {
      toast.error('Failed to run report');
    }
  }

  async function pollRunStatus(runId: string, reportId: string) {
    const maxAttempts = 30;
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      try {
        const run = await api.getReportRun(reportId, runId);
        if (run.status === 'completed') {
          toast.success('Report completed!');
          loadDashboardData();
          break;
        } else if (run.status === 'failed') {
          toast.error('Report generation failed');
          break;
        }
      } catch {
        break;
      }
    }
  }

  async function handleDownloadReport(runId: string, reportId: string, format: string) {
    try {
      const blob = await api.downloadReport(reportId, runId, format as any);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${runId}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Download started');
    } catch (error) {
      toast.error('Download failed');
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-card border-r border-border flex flex-col hidden lg:flex">
        <div className="p-4 border-b border-border">
          <h1 className="text-xl font-bold text-primary">Retention Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {agency?.name || 'Demo Agency'}
          </p>
        </div>
        
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          <button
            onClick={() => setActiveTab('overview')}
            className={`w-full px-3 py-2 rounded-lg text-left transition-colors ${
              activeTab === 'overview'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-accent text-foreground'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('workflows')}
            className={`w-full px-3 py-2 rounded-lg text-left transition-colors ${
              activeTab === 'workflows'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-accent text-foreground'
            }`}
          >
            Workflows
          </button>
          <button
            onClick={() => setActiveTab('reports')}
            className={`w-full px-3 py-2 rounded-lg text-left transition-colors ${
              activeTab === 'reports'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-accent text-foreground'
            }`}
          >
            Reports
          </button>
          <button
            onClick={() => setActiveTab('schedules')}
            className={`w-full px-3 py-2 rounded-lg text-left transition-colors ${
              activeTab === 'schedules'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-accent text-foreground'
            }`}
          >
            Schedules
          </button>
          <button
            onClick={() => setActiveTab('analytics')}
            className={`w-full px-3 py-2 rounded-lg text-left transition-colors ${
              activeTab === 'analytics'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-accent text-foreground'
            }`}
          >
            Analytics
          </button>
          <button
            onClick={() => setActiveTab('engagement')}
            className={`w-full px-3 py-2 rounded-lg text-left transition-colors ${
              activeTab === 'engagement'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-accent text-foreground'
            }`}
          >
            Engagement
          </button>
          <button
            onClick={() => setActiveTab('llm')}
            className={`w-full px-3 py-2 rounded-lg text-left transition-colors ${
              activeTab === 'llm'
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-accent text-foreground'
            }`}
          >
            LLM Models
          </button>
        </nav>
        
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-sm font-medium text-primary">
                {user?.name?.charAt(0) || 'U'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name || 'User'}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email || ''}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6 sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold capitalize">{activeTab}</h2>
            
            {/* Client Selector */}
            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="w-48 px-3 py-2 border border-input rounded-lg bg-background text-sm focus:ring-2 focus:ring-primary"
            >
              <option value="">All Clients</option>
              {/* Would populate from API */}
            </select>
            
            {/* Date Range */}
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                className="px-3 py-1 border border-input rounded-lg bg-background text-sm w-32"
              />
              <span className="text-muted-foreground">to</span>
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                className="px-3 py-1 border border-input rounded-lg bg-background text-sm w-32"
              />
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={loadDashboardData}
              disabled={loading}
              className="px-3 py-2 border border-input rounded-lg hover:bg-accent transition-colors flex items-center gap-2 text-sm"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button className="px-3 py-2 border border-input rounded-lg hover:bg-accent transition-colors flex items-center gap-2 text-sm">
              <Filter className="w-4 h-4" />
              Filters
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'overview' && (
            <OverviewTab kpiData={kpiData} reports={reports} onRunReport={handleRunReport} loading={loading} revenueData={revenueData} channelData={channelData} />
          )}
          {activeTab === 'workflows' && (
            <WorkflowsTab />
          )}
          {activeTab === 'reports' && (
            <ReportsTab reports={reports} onRunReport={handleRunReport} onDownload={handleDownloadReport} currentReport={currentReport} setCurrentReport={setCurrentReport} />
          )}
          {activeTab === 'schedules' && (
            <SchedulesTab />
          )}
          {activeTab === 'analytics' && (
            <AnalyticsTab />
          )}
          {activeTab === 'engagement' && (
            <EngagementTab />
          )}
          {activeTab === 'llm' && (
            <LLMManagementTab user={user} />
          )}
        </div>
      </main>
    </div>
  );
}

function OverviewTab({ kpiData, reports, onRunReport, loading, revenueData, channelData }: { 
  kpiData: KPIMetric[]; 
  reports: any[]; 
  onRunReport: (id: string) => void;
  loading: boolean;
  revenueData: any[];
  channelData: Record<string, number>;
}) {
  return (
    <div className="space-y-6 animate-in">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiData.map((kpi, index) => (
          <KPICard key={index} {...kpi} />
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartWidget
          title="Revenue Trend (30 days)"
          type="line_chart"
          data={revenueData.map(d => ({
            date: d.date.split('T')[0],
            revenue: d.revenue,
            sessions: d.sessions,
          }))}
          xKey="date"
          yKeys={['revenue']}
          height={350}
        />
        <ChartWidget
          title="Revenue by Channel"
          type="bar_chart"
          data={Object.entries(channelData).map(([channel, revenue]) => ({
            channel: channel.charAt(0).toUpperCase() + channel.slice(1),
            revenue,
          }))}
          xKey="channel"
          yKeys={['revenue']}
          height={350}
        />
      </div>

      {/* Recent Reports */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Recent Reports</h3>
          <button className="text-sm text-primary hover:underline">View All</button>
        </div>
        <ReportList reports={reports.slice(0, 5)} onRun={onRunReport} />
      </div>
    </div>
  );
}

function ReportsTab({ reports, onRunReport, onDownload, currentReport, setCurrentReport }: {
  reports: any[];
  onRunReport: (id: string) => void;
  onDownload: (runId: string, reportId: string, format: string) => void;
  currentReport: any;
  setCurrentReport: (r: any) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">All Reports</h3>
        <button className="px-4 py-2 bg-primary text-primary-foreground rounded-lg flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Report
        </button>
      </div>
      <ReportList reports={reports} onRun={onRunReport} onDownload={onDownload} currentReport={currentReport} setCurrentReport={setCurrentReport} />
    </div>
  );
}

function SchedulesTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Scheduled Reports</h3>
        <button className="px-4 py-2 bg-primary text-primary-foreground rounded-lg flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Schedule
        </button>
      </div>
      <ScheduleList />
    </div>
  );
}

function WorkflowsTab() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorkflows();
  }, []);

  async function loadWorkflows() {
    try {
      const data = await api.listWorkflows({ limit: 50 });
      setWorkflows(data.items);
    } catch (error) {
      toast.error('Failed to load workflows');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Workflows</h3>
        <button className="px-4 py-2 bg-primary text-primary-foreground rounded-lg flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Workflow
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : workflows.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
            <Zap className="w-8 h-8 text-muted-foreground" />
          </div>
          <h4 className="text-lg font-medium mb-2">No workflows yet</h4>
          <p className="text-muted-foreground mb-6">Create your first workflow to automate retention campaigns</p>
          <button className="px-6 py-3 bg-primary text-primary-foreground rounded-lg flex items-center gap-2 mx-auto">
            <Plus className="w-4 h-4" />
            Create Workflow
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {workflows.map(w => (
            <div key={w.id} className="bg-card border border-border rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <h4 className="font-semibold truncate">{w.name}</h4>
                    <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-700">{w.status}</span>
                    <span className="text-xs text-muted-foreground px-2 py-0.5 rounded bg-muted">v{w.version}</span>
                  </div>
                  {w.description && <p className="text-sm text-muted-foreground mt-1 truncate">{w.description}</p>}
                  <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                    <span>Category: {w.category}</span>
                    <span>Executions: {w.total_executions}</span>
                    <span>Success: {w.successful_executions}</span>
                    <span>Failed: {w.failed_executions}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-4">
                  <button className="p-2 hover:bg-accent rounded transition-colors" title="Edit">
                    <Edit className="w-4 h-4" />
                  </button>
                  <button className="p-2 hover:bg-accent rounded transition-colors" title="Duplicate">
                    <Copy className="w-4 h-4" />
                  </button>
                  {w.status === 'published' && (
                    <button className="p-2 hover:bg-accent rounded transition-colors text-green-600" title="Execute">
                      <Play className="w-4 h-4" />
                    </button>
                  )}
                  <button className="p-2 hover:bg-accent rounded transition-colors" title="View Executions">
                    <Eye className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AnalyticsTab() {
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnomalies();
  }, []);

  async function loadAnomalies() {
    try {
      const data = await api.getAnomalies({ days: 30 });
      setAnomalies(data);
    } catch (error) {
      toast.error('Failed to load anomalies');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">Analytics</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Total Anomalies" value={anomalies.length} format="number" />
        <KPICard label="Critical" value={anomalies.filter(a => a.severity === 'critical').length} format="number" />
        <KPICard label="Warnings" value={anomalies.filter(a => a.severity === 'warning').length} format="number" />
        <KPICard label="Info" value={anomalies.filter(a => a.severity === 'info').length} format="number" />
      </div>

      <div className="bg-card border border-border rounded-lg">
        <div className="p-4 border-b border-border">
          <h4 className="font-medium">Recent Anomalies</h4>
        </div>
        <div className="divide-y divide-border">
          {loading ? (
            <div className="p-8 text-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" /></div>
          ) : anomalies.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">No anomalies detected</div>
          ) : (
            anomalies.slice(0, 10).map(a => (
              <div key={a.id} className="p-4 hover:bg-accent/50 flex items-center justify-between">
                <div>
                  <p className="font-medium">{a.metric}</p>
                  <p className="text-sm text-muted-foreground">{a.type} • {format(new Date(a.detected_at), 'PPpp')}</p>
                </div>
                <div className="text-right">
                  <span className={`px-2 py-0.5 text-xs rounded ${a.severity === 'critical' ? 'bg-red-100 text-red-700' : a.severity === 'warning' ? 'bg-yellow-100 text-yellow-700' : 'bg-blue-100 text-blue-700'}`}>
                    {a.severity}
                  </span>
                  <p className="text-sm text-muted-foreground mt-1">Deviation: {a.deviation_pct.toFixed(1)}%</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function LLMManagementTab({ user }: { user: any }) {
  const isDev = user?.role === 'owner' || user?.role === 'admin';

  return (
    <div className="h-full">
      <LLMModelManagement tenantId={user?.client_id || ''} isDev={isDev} />
    </div>
  );
}

function EngagementTab() {
  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold">Engagement</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-lg p-6 text-center">
          <Mail className="w-12 h-12 mx-auto mb-2 text-green-500" />
          <h4 className="font-medium mb-1">Email Campaigns</h4>
          <p className="text-sm text-muted-foreground">Create and manage email workflows</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-6 text-center">
          <MessageSquare className="w-12 h-12 mx-auto mb-2 text-blue-500" />
          <h4 className="font-medium mb-1">SMS Campaigns</h4>
          <p className="text-sm text-muted-foreground">Automated SMS sequences</p>
        </div>
        <div className="bg-card border border-border rounded-lg p-6 text-center">
          <Smartphone className="w-12 h-12 mx-auto mb-2 text-purple-500" />
          <h4 className="font-medium mb-1">Push Notifications</h4>
          <p className="text-sm text-muted-foreground">Mobile push campaigns</p>
        </div>
      </div>
    </div>
  );
}