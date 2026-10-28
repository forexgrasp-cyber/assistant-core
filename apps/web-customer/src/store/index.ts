/**
 * Zustand Store for Customer Portal
 */

import { create } from 'zustand';
import { persist, devtools } from 'zustand/middleware';
import type {
  ReportDefinition,
  ReportTemplate,
  ReportRun,
  ReportSchedule,
  WidgetDefinition,
  User,
  Agency,
  Client,
  DashboardLayout,
} from '@/types';

interface AppState {
  // Auth
  user: User | null;
  agency: Agency | null;
  client: Client | null;
  isAuthenticated: boolean;
  
  // Reports
  reports: ReportDefinition[];
  currentReport: ReportDefinition | null;
  reportRuns: ReportRun[];
  currentRun: ReportRun | null;
  templates: ReportTemplate[];
  
  // Schedules
  schedules: ReportSchedule[];
  
  // Dashboard
  dashboards: DashboardLayout[];
  currentDashboard: DashboardLayout | null;
  
  // UI State
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
  loading: boolean;
  error: string | null;
  
  // Actions
  setAuth: (user: User | null, agency?: Agency | null, client?: Client | null) => void;
  logout: () => void;
  
  setReports: (reports: ReportDefinition[]) => void;
  addReport: (report: ReportDefinition) => void;
  updateReport: (report: ReportDefinition) => void;
  removeReport: (reportId: string) => void;
  setCurrentReport: (report: ReportDefinition | null) => void;
  
  setReportRuns: (runs: ReportRun[]) => void;
  addReportRun: (run: ReportRun) => void;
  updateReportRun: (run: ReportRun) => void;
  setCurrentRun: (run: ReportRun | null) => void;
  
  setTemplates: (templates: ReportTemplate[]) => void;
  
  setSchedules: (schedules: ReportSchedule[]) => void;
  addSchedule: (schedule: ReportSchedule) => void;
  updateSchedule: (schedule: ReportSchedule) => void;
  removeSchedule: (scheduleId: string) => void;
  
  setDashboards: (dashboards: DashboardLayout[]) => void;
  setCurrentDashboard: (dashboard: DashboardLayout | null) => void;
  
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  
  // Widget builder
  widgetBuilder: {
    availableWidgets: WidgetDefinition[];
    canvasWidgets: WidgetDefinition[];
    selectedWidget: WidgetDefinition | null;
    history: WidgetDefinition[][];
    historyIndex: number;
  };
  setAvailableWidgets: (widgets: WidgetDefinition[]) => void;
  addCanvasWidget: (widget: WidgetDefinition) => void;
  updateCanvasWidget: (widget: WidgetDefinition) => void;
  removeCanvasWidget: (widgetId: string) => void;
  setSelectedWidget: (widget: WidgetDefinition | null) => void;
  undo: () => void;
  redo: () => void;
}

const initialWidgetBuilder = {
  availableWidgets: [],
  canvasWidgets: [],
  selectedWidget: null,
  history: [[]],
  historyIndex: 0,
};

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        // Auth
        user: null,
        agency: null,
        client: null,
        isAuthenticated: false,
        
        // Reports
        reports: [],
        currentReport: null,
        reportRuns: [],
        currentRun: null,
        templates: [],
        
        // Schedules
        schedules: [],
        
        // Dashboard
        dashboards: [],
        currentDashboard: null,
        
        // UI State
        sidebarOpen: true,
        theme: 'system',
        loading: false,
        error: null,
        
        // Widget Builder
        widgetBuilder: initialWidgetBuilder,
        
        // Actions
        setAuth: (user, agency, client) => set({
          user,
          agency,
          client,
          isAuthenticated: !!user,
        }),
        
        logout: () => set({
          user: null,
          agency: null,
          client: null,
          isAuthenticated: false,
          reports: [],
          currentReport: null,
          reportRuns: [],
          currentRun: null,
          schedules: [],
          dashboards: [],
          currentDashboard: null,
        }),
        
        setReports: (reports) => set({ reports }),
        addReport: (report) => set((state) => ({ reports: [report, ...state.reports] })),
        updateReport: (report) => set((state) => ({
          reports: state.reports.map((r) => (r.id === report.id ? report : r)),
          currentReport: state.currentReport?.id === report.id ? report : state.currentReport,
        })),
        removeReport: (reportId) => set((state) => ({
          reports: state.reports.filter((r) => r.id !== reportId),
          currentReport: state.currentReport?.id === reportId ? null : state.currentReport,
        })),
        setCurrentReport: (report) => set({ currentReport: report }),
        
        setReportRuns: (runs) => set({ reportRuns: runs }),
        addReportRun: (run) => set((state) => ({ reportRuns: [run, ...state.reportRuns] })),
        updateReportRun: (run) => set((state) => ({
          reportRuns: state.reportRuns.map((r) => (r.id === run.id ? run : r)),
          currentRun: state.currentRun?.id === run.id ? run : state.currentRun,
        })),
        setCurrentRun: (run) => set({ currentRun: run }),
        
        setTemplates: (templates) => set({ templates }),
        
        setSchedules: (schedules) => set({ schedules }),
        addSchedule: (schedule) => set((state) => ({ schedules: [schedule, ...state.schedules] })),
        updateSchedule: (schedule) => set((state) => ({
          schedules: state.schedules.map((s) => (s.id === schedule.id ? schedule : s)),
        })),
        removeSchedule: (scheduleId) => set((state) => ({
          schedules: state.schedules.filter((s) => s.id !== scheduleId),
        })),
        
        setDashboards: (dashboards) => set({ dashboards }),
        setCurrentDashboard: (dashboard) => set({ currentDashboard: dashboard }),
        
        setSidebarOpen: (open) => set({ sidebarOpen: open }),
        toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
        setTheme: (theme) => set({ theme }),
        setLoading: (loading) => set({ loading }),
        setError: (error) => set({ error }),
        
        // Widget Builder
        setAvailableWidgets: (widgets) => set((state) => ({
          widgetBuilder: { ...state.widgetBuilder, availableWidgets: widgets },
        })),
        
        addCanvasWidget: (widget) => set((state) => {
          const newCanvas = [...state.widgetBuilder.canvasWidgets, widget];
          const newHistory = state.widgetBuilder.history.slice(0, state.widgetBuilder.historyIndex + 1);
          newHistory.push(newCanvas);
          return {
            widgetBuilder: {
              ...state.widgetBuilder,
              canvasWidgets: newCanvas,
              history: newHistory,
              historyIndex: newHistory.length - 1,
            },
          };
        }),
        
        updateCanvasWidget: (widget) => set((state) => {
          const newCanvas = state.widgetBuilder.canvasWidgets.map((w) =>
            w.id === widget.id ? widget : w
          );
          const newHistory = state.widgetBuilder.history.slice(0, state.widgetBuilder.historyIndex + 1);
          newHistory.push(newCanvas);
          return {
            widgetBuilder: {
              ...state.widgetBuilder,
              canvasWidgets: newCanvas,
              history: newHistory,
              historyIndex: newHistory.length - 1,
            },
          };
        }),
        
        removeCanvasWidget: (widgetId) => set((state) => {
          const newCanvas = state.widgetBuilder.canvasWidgets.filter((w) => w.id !== widgetId);
          const newHistory = state.widgetBuilder.history.slice(0, state.widgetBuilder.historyIndex + 1);
          newHistory.push(newCanvas);
          return {
            widgetBuilder: {
              ...state.widgetBuilder,
              canvasWidgets: newCanvas,
              history: newHistory,
              historyIndex: newHistory.length - 1,
            },
          };
        }),
        
        setSelectedWidget: (widget) => set((state) => ({
          widgetBuilder: { ...state.widgetBuilder, selectedWidget: widget },
        })),
        
        undo: () => set((state) => {
          if (state.widgetBuilder.historyIndex > 0) {
            const newIndex = state.widgetBuilder.historyIndex - 1;
            return {
              widgetBuilder: {
                ...state.widgetBuilder,
                canvasWidgets: state.widgetBuilder.history[newIndex],
                historyIndex: newIndex,
              },
            };
          }
          return state;
        }),
        
        redo: () => set((state) => {
          if (state.widgetBuilder.historyIndex < state.widgetBuilder.history.length - 1) {
            const newIndex = state.widgetBuilder.historyIndex + 1;
            return {
              widgetBuilder: {
                ...state.widgetBuilder,
                canvasWidgets: state.widgetBuilder.history[newIndex],
                historyIndex: newIndex,
              },
            };
          }
          return state;
        }),
      }),
      {
        name: 'retention-analytics-store',
        partialize: (state) => ({
          theme: state.theme,
          sidebarOpen: state.sidebarOpen,
          user: state.user,
          agency: state.agency,
          client: state.client,
        }),
      }
    ),
    { name: 'RetentionAnalyticsStore' }
  )
);