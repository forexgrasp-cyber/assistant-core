/**
 * API Client for the Developer Console.
 * Wires console tabs to the real backend endpoints.
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8765';

// ── Types ─────────────────────────────────────────────────────────────────

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  status: string;
  client_id: string;
  created_at: string;
  updated_at: string;
}

export interface VerticalPack {
  id: string;
  name: string;
  slug: string;
  description?: string;
  version: string;
  price: number;
  currency: string;
  status: string;
  is_published: boolean;
  is_featured: boolean;
  downloads: number;
  rating: number;
  review_count: number;
  tags: string[];
}

export interface PackEntity {
  id: string;
  name: string;
  slug: string;
  display_name?: string;
  description?: string;
  category?: string;
  is_system: boolean;
  is_required: boolean;
}

export interface Agency {
  id: string;
  name: string;
  slug: string;
  is_active?: boolean;
  created_at?: string;
}

export interface ClientSummary {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
}

export interface DashboardSummary {
  period_days: number;
  totals: { revenue: number; orders: number; new_customers: number };
  channel_breakdown: Record<string, number>;
  daily_series: Array<{ date: string; revenue: number; orders: number; sessions: number }>;
}

export interface QueryResult {
  data: Record<string, any>[];
  columns: string[];
  row_count: number;
  execution_time_ms: number;
  source?: string;
  metadata?: Record<string, any>;
}

// ── Client ────────────────────────────────────────────────────────────────

class DevApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000,
    });

    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401 && typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // ── Workflows ───────────────────────────────────────────────────────────

  async listWorkflows(params?: { limit?: number; offset?: number }): Promise<any> {
    const response = await this.client.get('/workflows', { params });
    return response.data;
  }

  async createWorkflow(data: Partial<Workflow>): Promise<Workflow> {
    const response = await this.client.post('/workflows', data);
    return response.data;
  }

  async deleteWorkflow(workflowId: string): Promise<void> {
    await this.client.delete(`/workflows/${workflowId}`);
  }

  async executeWorkflow(workflowId: string, data?: Record<string, any>): Promise<any> {
    const response = await this.client.post(`/workflows/${workflowId}/execute`, data || {});
    return response.data;
  }

  // ── Vertical Packs ──────────────────────────────────────────────────────

  async listPacks(params?: { limit?: number; offset?: number; status?: string }): Promise<any> {
    const response = await this.client.get('/vertical-packs', { params });
    return response.data;
  }

  async getPack(packId: string): Promise<VerticalPack> {
    const response = await this.client.get(`/vertical-packs/${packId}`);
    return response.data;
  }

  async listPackEntities(packId: string): Promise<PackEntity[]> {
    const response = await this.client.get(`/vertical-packs/${packId}/entities`);
    return response.data;
  }

  async installPack(packId: string, config: Record<string, any> = {}): Promise<any> {
    const response = await this.client.post(`/vertical-packs/${packId}/install`, config);
    return response.data;
  }

  // ── Tenants (Agencies + Clients) ────────────────────────────────────────

  async listAgencies(params?: { limit?: number; offset?: number }): Promise<any> {
    const response = await this.client.get('/tenants', { params });
    return response.data;
  }

  async listClients(params?: { limit?: number; offset?: number }): Promise<any> {
    const response = await this.client.get('/clients', { params });
    return response.data;
  }

  // ── Analytics Explorer ──────────────────────────────────────────────────

  async getDashboard(params?: { client_id?: string; days?: number }): Promise<DashboardSummary> {
    const response = await this.client.get('/analytics/dashboard', { params });
    return response.data;
  }

  async executeQuery(data: {
    source: { type: string; metrics: string[]; dimensions?: string[] };
    date_range?: Record<string, any>;
    client_ids?: string[];
  }): Promise<QueryResult> {
    const response = await this.client.post('/query', data);
    return response.data;
  }

  async getAnomalies(params?: { days?: number; status?: string }): Promise<any[]> {
    const response = await this.client.get('/analytics/anomalies', { params });
    return response.data;
  }
}

export const api = new DevApiClient();
