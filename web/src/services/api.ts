import axios from 'axios';
import { SearchRequest, SearchResponse, SystemStatus, ThemeConfig } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const searchAPI = {
  async search(request: SearchRequest): Promise<SearchResponse> {
    const response = await apiClient.post<SearchResponse>('/search', request);
    return response.data;
  },

  async getStatus(): Promise<SystemStatus> {
    const response = await apiClient.get<SystemStatus>('/status');
    return response.data;
  },

  async getModalities(): Promise<any[]> {
    const response = await apiClient.get('/modalities');
    return response.data.modalities;
  },

  async getConfig(): Promise<ThemeConfig> {
    const response = await apiClient.get<ThemeConfig>('/config');
    return response.data;
  },

  async updateConfig(config: Partial<ThemeConfig>): Promise<void> {
    await apiClient.post('/config', config);
  },

  async exportResults(results: any[], format: 'json' | 'csv'): Promise<Blob> {
    if (format === 'json') {
      const json = JSON.stringify(results, null, 2);
      return new Blob([json], { type: 'application/json' });
    } else {
      // Convert to CSV
      const headers = Object.keys(results[0] || {}).join(',');
      const rows = results.map(r =>
        Object.values(r).map(v =>
          typeof v === 'string' && v.includes(',') ? `"${v}"` : v
        ).join(',')
      );
      const csv = [headers, ...rows].join('\n');
      return new Blob([csv], { type: 'text/csv' });
    }
  },
};