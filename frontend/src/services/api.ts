import axios from 'axios';
import { Campaign, MarketingContent, KPISummary, AIIdeaResponse, AIDraftResponse, AISummaryResponse, User, Product } from '../types';

const API_BASE_URL = ((import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000/api/v1');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Gắn Bearer token tự động
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Helper trích xuất thông báo lỗi chuẩn từ FastAPI backend
export const getApiErrorMessage = (error: any): string => {
  if (error?.response?.data?.detail) {
    const detail = error.response.data.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
    }
    return JSON.stringify(detail);
  }
  return error?.message || 'Đã xảy ra lỗi không xác định';
};

export const authApi = {
  login: async (email: string, password: string): Promise<{ access_token: string; user: User }> => {
    const res = await apiClient.post('/auth/login', { email, password });
    localStorage.setItem('access_token', res.data.access_token);
    localStorage.setItem('current_user', JSON.stringify(res.data.user));
    return res.data;
  },
  getCurrentUser: (): User | null => {
    const userStr = localStorage.getItem('current_user');
    return userStr ? JSON.parse(userStr) : null;
  },
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
  }
};

export const campaignApi = {
  getAll: async (status?: string, search?: string): Promise<Campaign[]> => {
    const params: Record<string, string> = {};
    if (status) params.status = status;
    if (search) params.search = search;
    const res = await apiClient.get('/campaigns', { params });
    return res.data;
  },
  getById: async (id: number): Promise<Campaign> => {
    const res = await apiClient.get(`/campaigns/${id}`);
    return res.data;
  },
  create: async (data: {
    product_id: number;
    name: string;
    objective: string;
    audience: string;
    start_date: string;
    end_date: string;
    budget: number;
  }): Promise<Campaign> => {
    const res = await apiClient.post('/campaigns', data);
    return res.data;
  },
  getKpi: async (id: number): Promise<KPISummary> => {
    const res = await apiClient.get(`/campaigns/${id}/kpi`);
    return res.data;
  },
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/campaigns/${id}`);
  }
};

export const productApi = {
  getAll: async (): Promise<Product[]> => {
    const res = await apiClient.get('/products');
    return res.data;
  }
};

export const contentApi = {
  getAll: async (campaignId?: number, status?: string): Promise<MarketingContent[]> => {
    const params: Record<string, any> = {};
    if (campaignId) params.campaign_id = campaignId;
    if (status) params.status = status;
    const res = await apiClient.get('/contents', { params });
    return res.data;
  },
  create: async (data: Partial<MarketingContent>): Promise<MarketingContent> => {
    const res = await apiClient.post('/contents', data);
    return res.data;
  },
  submitForReview: async (id: number): Promise<MarketingContent> => {
    const res = await apiClient.post(`/contents/${id}/submit`);
    return res.data;
  },
  approve: async (id: number): Promise<MarketingContent> => {
    const res = await apiClient.post(`/contents/${id}/approve`);
    return res.data;
  },
  reject: async (id: number, reason: string): Promise<MarketingContent> => {
    const res = await apiClient.post(`/contents/${id}/reject`, { decision: 'REJECTED', reason });
    return res.data;
  }
};

export const aiApi = {
  generateIdeas: async (
    campaignId?: number | null,
    channelCode = 'facebook',
    promptVersion = 'v3',
    customData?: { topic?: string; product?: string; usp?: string; tone?: string }
  ): Promise<AIIdeaResponse> => {
    const payload: any = {
      channel_code: channelCode,
      prompt_version: promptVersion
    };
    if (campaignId) payload.campaign_id = campaignId;
    if (customData?.topic) payload.custom_topic = customData.topic;
    if (customData?.product) payload.custom_product = customData.product;
    if (customData?.usp) payload.custom_usp = customData.usp;
    if (customData?.tone) payload.tone = customData.tone;
    const res = await apiClient.post('/ai/ideas', payload);
    return res.data;
  },
  generateDraft: async (
    campaignId?: number | null,
    idea?: string,
    channelCode = 'facebook',
    promptVersion = 'v3',
    customData?: { product?: string; usp?: string }
  ): Promise<AIDraftResponse> => {
    const payload: any = {
      selected_idea: idea || 'Giải pháp marketing sáng tạo tiếp cận khách hàng tiềm năng',
      channel_code: channelCode,
      prompt_version: promptVersion
    };
    if (campaignId) payload.campaign_id = campaignId;
    if (customData?.product) payload.custom_product = customData.product;
    if (customData?.usp) payload.custom_usp = customData.usp;
    const res = await apiClient.post('/ai/draft', payload);
    return res.data;
  },
  generateSummary: async (campaignId: number, promptVersion = 'v3'): Promise<AISummaryResponse> => {
    const res = await apiClient.post('/ai/summary', {
      campaign_id: campaignId,
      prompt_version: promptVersion
    });
    return res.data;
  }
};

export const analyticsApi = {
  getDashboard: async () => {
    const res = await apiClient.get('/analytics/dashboard');
    return res.data;
  }
};
