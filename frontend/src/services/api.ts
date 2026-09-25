import axios from 'axios';
import { 
  Campaign, MarketingContent, KPISummary, AIIdeaResponse, AIDraftResponse, 
  AISummaryResponse, OmnichannelRequest, OmnichannelResponse, User, Product, 
  MarketingSchedule, ContentComplianceCheck, Workspace, BrandKit, 
  ComplianceCheckRequest, ComplianceCheckResponse, ComplianceViolation, 
  ContentReview, ChannelAttribution, AIDoctorReport,
  CustomApiKey, AIKeyTestRequest, AIKeyTestResponse, AIKeySaveRequest, AIKeySaveResponse
} from '../types';
import { 
  MOCK_USER_MANAGER, 
  MOCK_USER_MARKETER, 
  MOCK_USER_CLIENT_APPROVER,
  MOCK_PRODUCTS, 
  MOCK_CAMPAIGNS, 
  MOCK_CONTENTS, 
  MOCK_SCHEDULES, 
  MOCK_DASHBOARD_KPI,
  MOCK_WORKSPACES,
  MOCK_BRAND_KITS,
  MOCK_CHANNEL_ATTRIBUTIONS,
  MOCK_AI_DOCTOR_REPORT,
  MOCK_CUSTOM_API_KEYS
} from './mockData';

const API_BASE_URL = ((import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000/api/v1');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper quản lý bộ nhớ đệm LocalStorage cho chế độ Offline/Cloudflare Demo
function getStoredList<T>(key: string, defaultData: T[]): T[] {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      localStorage.setItem(key, JSON.stringify(defaultData));
      return defaultData;
    }
    return JSON.parse(raw);
  } catch {
    return defaultData;
  }
}

function setStoredList<T>(key: string, data: T[]): void {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (e) {
    console.error(e);
  }
}

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
    try {
      const res = await apiClient.post('/auth/login', { email, password });
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('current_user', JSON.stringify(res.data.user));
      return res.data;
    } catch (e: any) {
      // Ném lỗi thực tế ra giao diện nếu có phản hồi từ server
      if (e?.response) {
        throw e;
      }
      // Chỉ khi backend hoàn toàn offline (Network Error), hỗ trợ demo login có kiểm tra email
      console.warn('Backend API offline, hỗ trợ phiên đăng nhập giả lập offline');
      const isManager = email.toLowerCase().includes('manager');
      const isApprover = email.toLowerCase().includes('approver');
      const user = isManager ? MOCK_USER_MANAGER : isApprover ? MOCK_USER_CLIENT_APPROVER : MOCK_USER_MARKETER;
      const demoToken = 'marketflow-demo-token-' + (isManager ? 'manager' : isApprover ? 'approver' : 'marketer');
      localStorage.setItem('access_token', demoToken);
      localStorage.setItem('current_user', JSON.stringify(user));
      return { access_token: demoToken, user };
    }
  },
  register: async (data: { email: string; password: string; full_name: string; role?: string }): Promise<User> => {
    const res = await apiClient.post('/auth/register', data);
    return res.data;
  },
  getMe: async (): Promise<User> => {
    const res = await apiClient.get('/auth/me');
    localStorage.setItem('current_user', JSON.stringify(res.data));
    return res.data;
  },
  getCurrentUser: (): User | null => {
    const userStr = localStorage.getItem('current_user');
    return userStr ? JSON.parse(userStr) : null;
  },
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
    localStorage.removeItem('active_workspace_id');
  }
};

export const workspaceApi = {
  getAll: async (): Promise<Workspace[]> => {
    try {
      const res = await apiClient.get('/workspaces');
      return res.data;
    } catch (e) {
      return getStoredList<Workspace>('mf_workspaces', MOCK_WORKSPACES);
    }
  },
  create: async (data: { name: string; description?: string; slug?: string }): Promise<Workspace> => {
    try {
      const res = await apiClient.post('/workspaces', data);
      return res.data;
    } catch (e) {
      const list = getStoredList<Workspace>('mf_workspaces', MOCK_WORKSPACES);
      const newWs: Workspace = {
        id: Date.now(),
        name: data.name,
        slug: data.slug || data.name.toLowerCase().replace(/\s+/g, '-'),
        description: data.description,
        status: 'ACTIVE',
        created_at: new Date().toISOString()
      };
      setStoredList('mf_workspaces', [...list, newWs]);
      return newWs;
    }
  },
  getById: async (id: number): Promise<Workspace> => {
    try {
      const res = await apiClient.get(`/workspaces/${id}`);
      return res.data;
    } catch (e) {
      const list = getStoredList<Workspace>('mf_workspaces', MOCK_WORKSPACES);
      const found = list.find(w => w.id === id);
      if (found) return found;
      throw e;
    }
  },
  update: async (id: number, data: { name?: string; description?: string }): Promise<Workspace> => {
    try {
      const res = await apiClient.put(`/workspaces/${id}`, data);
      return res.data;
    } catch (e) {
      const list = getStoredList<Workspace>('mf_workspaces', MOCK_WORKSPACES);
      const idx = list.findIndex(w => w.id === id);
      if (idx !== -1) {
        list[idx] = { ...list[idx], ...data };
        setStoredList('mf_workspaces', list);
        return list[idx];
      }
      throw e;
    }
  },
  addMember: async (id: number, data: { email: string; role: string }): Promise<any> => {
    const res = await apiClient.post(`/workspaces/${id}/members`, data);
    return res.data;
  }
};

export const brandKitApi = {
  getByWorkspace: async (workspaceId: number): Promise<BrandKit> => {
    try {
      const res = await apiClient.get('/brand-kit', { params: { workspace_id: workspaceId } });
      return res.data;
    } catch (e) {
      const stored = MOCK_BRAND_KITS[workspaceId] || {
        id: workspaceId,
        workspace_id: workspaceId,
        brand_name: 'Brand #' + workspaceId,
        usp: 'Định vị thương hiệu mặc định',
        tone_of_voice: 'Chuyên nghiệp, hiện đại',
        banned_keywords: []
      };
      return stored;
    }
  },
  update: async (workspaceId: number, data: Partial<BrandKit>): Promise<BrandKit> => {
    try {
      const res = await apiClient.put('/brand-kit', data, { params: { workspace_id: workspaceId } });
      return res.data;
    } catch (e) {
      const current = MOCK_BRAND_KITS[workspaceId] || {
        id: workspaceId,
        workspace_id: workspaceId,
        brand_name: '',
        usp: '',
        tone_of_voice: 'Chuyên nghiệp',
        banned_keywords: []
      };
      const updated = { ...current, ...data };
      MOCK_BRAND_KITS[workspaceId] = updated as BrandKit;
      return updated as BrandKit;
    }
  }
};

export const campaignApi = {
  getAll: async (status?: string, search?: string, workspaceId?: number): Promise<Campaign[]> => {
    try {
      const params: Record<string, any> = {};
      if (status) params.status = status;
      if (search) params.search = search;
      if (workspaceId) params.workspace_id = workspaceId;
      const res = await apiClient.get('/campaigns', { params });
      return res.data;
    } catch (e) {
      let list = getStoredList<Campaign>('mf_campaigns', MOCK_CAMPAIGNS);
      if (workspaceId) {
        list = list.filter(c => !c.workspace_id || c.workspace_id === workspaceId);
      }
      if (status && status !== 'ALL') {
        list = list.filter(c => c.status === status);
      }
      if (search) {
        list = list.filter(c => c.name.toLowerCase().includes(search.toLowerCase()));
      }
      return list;
    }
  },

  getById: async (id: number): Promise<Campaign> => {
    try {
      const res = await apiClient.get(`/campaigns/${id}`);
      return res.data;
    } catch (e) {
      const list = getStoredList<Campaign>('mf_campaigns', MOCK_CAMPAIGNS);
      const found = list.find(c => c.id === id);
      if (found) return found;
      return MOCK_CAMPAIGNS[0];
    }
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
    try {
      const res = await apiClient.post('/campaigns', data);
      return res.data;
    } catch (e) {
      const list = getStoredList<Campaign>('mf_campaigns', MOCK_CAMPAIGNS);
      const newCamp: Campaign = {
        id: Date.now(),
        owner_id: 1,
        ...data,
        status: 'ACTIVE',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      setStoredList('mf_campaigns', [newCamp, ...list]);
      return newCamp;
    }
  },
  update: async (id: number, data: Partial<Campaign>): Promise<Campaign> => {
    try {
      const res = await apiClient.put(`/campaigns/${id}`, data);
      return res.data;
    } catch (e) {
      const list = getStoredList<Campaign>('mf_campaigns', MOCK_CAMPAIGNS);
      const updated = list.map(c => c.id === id ? { ...c, ...data, updated_at: new Date().toISOString() } : c);
      setStoredList('mf_campaigns', updated);
      const found = updated.find(c => c.id === id);
      if (found) return found;
      throw e;
    }
  },
  getKpi: async (id: number): Promise<KPISummary> => {
    try {
      const res = await apiClient.get(`/campaigns/${id}/kpi`);
      const data = res.data;
      if (data && data.roas === undefined) {
        data.roas = data.total_cost > 0 ? Number((data.total_revenue / data.total_cost).toFixed(2)) : 0.0;
      }
      return data;
    } catch (e) {
      return MOCK_DASHBOARD_KPI;
    }
  },
  getAIDoctor: async (campaignId: number): Promise<AIDoctorReport> => {
    try {
      const res = await apiClient.post(`/campaigns/${campaignId}/ai-doctor`);
      return res.data;
    } catch (e) {
      return {
        ...MOCK_AI_DOCTOR_REPORT,
        campaign_id: campaignId
      };
    }
  },
  getAttribution: async (campaignId: number): Promise<ChannelAttribution[]> => {
    try {
      const res = await apiClient.get(`/campaigns/${campaignId}/attribution`);
      return res.data;
    } catch (e) {
      return MOCK_CHANNEL_ATTRIBUTIONS;
    }
  },
  getContents: async (campaignId: number): Promise<MarketingContent[]> => {
    try {
      const res = await apiClient.get(`/campaigns/${campaignId}/contents`);
      return res.data;
    } catch (e) {
      const list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
      return list.filter(c => c.campaign_id === campaignId);
    }
  },
  delete: async (id: number): Promise<void> => {
    try {
      await apiClient.delete(`/campaigns/${id}`);
    } catch (e) {
      const list = getStoredList<Campaign>('mf_campaigns', MOCK_CAMPAIGNS);
      setStoredList('mf_campaigns', list.filter(c => c.id !== id));
    }
  }
};

export const productApi = {
  getAll: async (): Promise<Product[]> => {
    try {
      const res = await apiClient.get('/products');
      return res.data;
    } catch (e) {
      return MOCK_PRODUCTS;
    }
  }
};

export const contentApi = {
  getAll: async (campaignId?: number, status?: string, workspaceId?: number): Promise<MarketingContent[]> => {
    try {
      const params: Record<string, any> = {};
      if (campaignId) params.campaign_id = campaignId;
      if (status) params.status = status;
      if (workspaceId) params.workspace_id = workspaceId;
      const res = await apiClient.get('/contents', { params });
      return res.data;
    } catch (e) {
      let list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
      if (workspaceId) list = list.filter(c => !c.workspace_id || c.workspace_id === workspaceId);
      if (campaignId) list = list.filter(c => c.campaign_id === campaignId);
      if (status && status !== 'ALL') list = list.filter(c => c.status === status);
      return list;
    }
  },

  create: async (data: Partial<MarketingContent>): Promise<MarketingContent> => {
    try {
      const res = await apiClient.post('/contents', data);
      return res.data;
    } catch (e) {
      const list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
      const newContent: MarketingContent = {
        id: Date.now(),
        campaign_id: data.campaign_id || 1,
        channel_id: data.channel_id || 1,
        created_by: 1,
        title: data.title || 'Nội dung tiếp thị mới',
        body: data.body || '',
        cta: data.cta || '',
        status: data.status || 'AI_DRAFT',
        version_no: 1,
        source_ids_json: '[]',
        warnings_json: '[]',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      setStoredList('mf_contents', [newContent, ...list]);
      return newContent;
    }
  },

  update: async (id: number, data: Partial<MarketingContent>): Promise<MarketingContent> => {
    try {
      const res = await apiClient.put(`/contents/${id}`, data);
      return res.data;
    } catch (e) {
      const list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
      const updated = list.map(c => c.id === id ? { ...c, ...data, updated_at: new Date().toISOString() } : c);
      setStoredList('mf_contents', updated);
      return updated.find(c => c.id === id)!;
    }
  },

  checkCompliance: async (data: ComplianceCheckRequest): Promise<ComplianceCheckResponse> => {
    try {
      const res = await apiClient.post('/contents/compliance-check', data);
      return res.data;
    } catch (e: any) {
      const local = evaluateMarketingCompliance(data.title || '', data.body || '', data.cta);
      const violations: ComplianceViolation[] = local.flagged_items.map(f => ({
        category: f.risk_level === 'HIGH' ? 'AD_POLICY' : 'BRAND_BANNED',
        severity: f.risk_level,
        word: f.phrase,
        suggestion: f.suggestion,
        reason: f.reason
      }));
      const hasHigh = violations.some(v => v.severity === 'HIGH');
      return {
        status: local.status,
        score: local.score,
        can_submit: !hasHigh,
        violations,
        summary: local.summary,
        flagged_items: local.flagged_items
      };
    }
  },
  submitForReview: async (id: number): Promise<MarketingContent> => {
    try {
      const res = await apiClient.post(`/contents/${id}/submit`);
      return res.data;
    } catch (e: any) {
      if (e.response?.status === 400 || e.response?.status === 403 || e.response?.status === 404 || e.response?.status === 422) {
        throw e;
      }
      const list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
      const updated = list.map(c => c.id === id ? { ...c, status: 'IN_REVIEW' as const } : c);
      setStoredList('mf_contents', updated);
      return updated.find(c => c.id === id)!;
    }
  },
  approve: async (id: number): Promise<MarketingContent> => {
    try {
      const res = await apiClient.post(`/contents/${id}/approve`);
      return res.data;
    } catch (e) {
      const list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
      const updated = list.map(c => c.id === id ? { ...c, status: 'APPROVED' as const } : c);
      setStoredList('mf_contents', updated);
      return updated.find(c => c.id === id)!;
    }
  },
  reject: async (id: number, reason: string): Promise<MarketingContent> => {
    try {
      const res = await apiClient.post(`/contents/${id}/reject`, { decision: 'REJECTED', reason });
      return res.data;
    } catch (e) {
      const list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
      const updated = list.map(c => c.id === id ? { ...c, status: 'REJECTED' as const, rejection_reason: reason } : c);
      setStoredList('mf_contents', updated);
      return updated.find(c => c.id === id)!;
    }
  }
};

export const aiApi = {
  generateIdeas: async (
    campaignId?: number | null,
    channelCode = 'facebook',
    promptVersion = 'v3',
    customData?: { topic?: string; product?: string; usp?: string; tone?: string }
  ): Promise<AIIdeaResponse> => {
    try {
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
    } catch (e) {
      return {
        task_type: 'IDEA',
        ideas: [
          { 
            id: 1,
            angle: 'AIDA - Gây chú ý & Khát khao', 
            headline: 'Bứt phá Doanh số Mùa Cao Điểm Nhờ Trợ Lý AI',
            concept: 'Vén màn giải pháp tự động hóa giúp x3 doanh số bán hàng mùa cao điểm', 
            target_emotion: 'Khát khao dẫn đầu thị trường và tiết kiệm chi phí' 
          },
          { 
            id: 2,
            angle: 'PAS - Đau đớn & Giải pháp', 
            headline: 'Chi Phí Quảng Cáo Tăng Cao Nhưng Đơn Hàng Không Đạt?',
            concept: 'Giải pháp cắt giảm CPA thực chiến và tối ưu hóa phân bổ ngân sách', 
            target_emotion: 'Nhẹ nhõm khi tìm ra giải pháp loại bỏ lãng phí ngân sách' 
          },
          { 
            id: 3,
            angle: 'FAB - Tính năng & Lợi ích', 
            headline: 'Tự Động Hóa Lịch Biểu Và Kiểm Duyệt Chuẩn Meta',
            concept: 'Hệ thống AI Copilot hỗ trợ lên lịch biểu và kiểm duyệt nội dung tự động đạt chuẩn', 
            target_emotion: 'Tự tin và an tâm về tính tuân thủ pháp lý quảng cáo' 
          }
        ],
        warnings: [],
        assumptions: ['Mô hình AI vận hành ở chế độ dự phòng thông minh'],
        model_used: 'Gemini 2.5 Flash (Smart Fallback)',
        prompt_version: 'v3'
      };
    }
  },
  generateDraft: async (
    campaignId?: number | null,
    idea?: string,
    channelCode = 'facebook',
    promptVersion = 'v3',
    customData?: { product?: string; usp?: string }
  ): Promise<AIDraftResponse> => {
    try {
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
    } catch (e) {
      return {
        task_type: 'DRAFT',
        title: 'Bí quyết Bứt phá Doanh số Đa kênh 2026 Nhờ Tự Động Hóa AI',
        body: 'Thị trường marketing số 2026 đòi hỏi tốc độ thử nghiệm và tối ưu hóa vượt bậc. Với sự trợ giúp từ MarketFlow AI, bạn có thể triển khai hàng chục mẫu quảng cáo tuân thủ chính sách, theo dõi ROI theo thời gian thực và phân bổ ngân sách chuẩn xác.',
        cta: 'Đăng ký nhận tài liệu và dùng thử miễn phí',
        warnings: [],
        assumptions: ['Định dạng kênh tương thích cao'],
        model_used: 'Gemini 2.5 Flash (Smart Fallback)',
        prompt_version: 'v3'
      };
    }
  },
  generateSummary: async (campaignId: number, promptVersion = 'v3'): Promise<AISummaryResponse> => {
    try {
      const res = await apiClient.post('/ai/summary', {
        campaign_id: campaignId,
        prompt_version: promptVersion
      });
      return res.data;
    } catch (e) {
      return {
        task_type: 'SUMMARY',
        executive_summary: 'Chiến dịch duy trì chỉ số hoàn vốn ROI ấn tượng ở mức +220.47% trên tổng doanh thu 68.900.000 VNĐ.',
        strengths: [
          'Chiến dịch duy trì chỉ số hoàn vốn ROI ấn tượng ở mức +220.47% nhờ hiệu quả cao từ kênh Facebook và TikTok.',
          'Tỷ lệ nhấp chuột (CTR) đạt 5.22%, vượt 35% so với mức trung bình ngành.'
        ],
        weaknesses: [
          'Kênh Email Marketing cần mở rộng danh sách người nhận và thử nghiệm A/B tiêu đề.'
        ],
        recommendations: [
          'Cân nhắc tăng ngân sách cho kênh TikTok đối với nhóm nội dung video ngắn có tương tác cao để tiếp cận tệp khách hàng tiềm năng.',
          'Tối ưu hóa nội dung Email Marketing nhằm cải thiện tỷ lệ mở thư và nâng cao giá trị đơn hàng trung bình.'
        ],
        warnings: [],
        model_used: 'Gemini 2.5 Flash (Smart Fallback)',
        prompt_version: 'v3'
      };
    }
  },
  generateOmnichannel: async (req: OmnichannelRequest): Promise<OmnichannelResponse> => {
    try {
      const res = await apiClient.post('/ai/omnichannel', req);
      return res.data;
    } catch (e) {
      const briefName = req.brief || 'Chiến dịch Tiếp thị Toàn diện';
      return {
        task_type: 'OMNICHANNEL',
        model_used: 'Gemini 2.5 Flash (Smart Fallback)',
        warnings: [],
        compliance_score: 100,
        is_fallback: true,
        facebook: {
          title: `Bùng Nổ Doanh Số & Dẫn Đầu Xu Hướng Cùng ${briefName.slice(0, 40)}`,
          headline: `Bùng Nổ Doanh Số & Dẫn Đầu Xu Hướng Cùng ${briefName.slice(0, 40)}`,
          body: `Bạn đang tìm kiếm giải pháp tiếp thị đa kênh đột phá nhằm tối ưu hóa chi phí CPA và nhân đôi tỷ lệ chuyển đổi?\n\nKhám phá hệ thống điều phối tiếp thị tự động chuẩn doanh nghiệp: Tự động kế thừa định vị thương hiệu, kiểm duyệt an toàn chính sách quảng cáo và phân phối nội dung chuẩn hóa trên mọi nền tảng.\n\nĐừng bỏ lỡ cơ hội bứt phá tăng trưởng trong giai đoạn cao điểm!`,
          primary_text: `Bạn đang tìm kiếm giải pháp tiếp thị đa kênh đột phá nhằm tối ưu hóa chi phí CPA và nhân đôi tỷ lệ chuyển đổi?\n\nKhám phá hệ thống điều phối tiếp thị tự động chuẩn doanh nghiệp: Tự động kế thừa định vị thương hiệu, kiểm duyệt an toàn chính sách quảng cáo và phân phối nội dung chuẩn hóa trên mọi nền tảng.\n\nĐừng bỏ lỡ cơ hội bứt phá tăng trưởng trong giai đoạn cao điểm!`,
          cta: 'Đăng ký tư vấn chiến lược và nhận bản đồ tăng trưởng miễn phí',
          hashtags: ['#MarketingAI', '#Omnichannel', '#TangTruongDoanhSo', '#ChuyendoiSo', '#MarketFlow'],
          visual_suggestion: 'Banner phong cách hiện đại với giao diện ứng dụng trên nền xanh gradient công nghệ.'
        },
        tiktok: {
          hook_3s: 'Dừng lướt 3 giây nếu doanh nghiệp bạn đang đốt tiền quảng cáo mà không ra đơn!',
          scenes: [
            {
              scene: 1,
              scene_number: 1,
              visual: 'Cận cảnh gương mặt marketer căng thẳng nhìn vào màn hình dashboard ads chi phí tăng vọt.',
              visual_action: 'Cận cảnh gương mặt marketer căng thẳng nhìn vào màn hình dashboard ads chi phí tăng vọt.',
              voiceover: 'Đốt hàng chục triệu chạy ads nhưng đơn hàng vẫn lẹt đẹt? Sai lầm là tiếp thị rời rạc từng kênh!',
              voiceover_script: 'Đốt hàng chục triệu chạy ads nhưng đơn hàng vẫn lẹt đẹt? Sai lầm là tiếp thị rời rạc từng kênh!',
              duration_seconds: '0-4s',
              audio: 'Hiệu ứng Whoosh nhanh kết hợp tiếng chuông Bell chime gây tò mò',
              audio_hint: 'Hiệu ứng Whoosh nhanh kết hợp tiếng chuông Bell chime gây tò mò'
            },
            {
              scene: 2,
              scene_number: 2,
              visual: 'Thao tác 1-Click trên giao diện MarketFlow, sinh đồng thời trọn bộ kịch bản và nội dung tiếp thị.',
              visual_action: 'Thao tác 1-Click trên giao diện MarketFlow, sinh đồng thời trọn bộ kịch bản và nội dung tiếp thị.',
              voiceover: 'Với nền tảng điều phối đa kênh, một đề bài duy nhất tự động tạo kịch bản video, bài viết và email đồng bộ.',
              voiceover_script: 'Với nền tảng điều phối đa kênh, một đề bài duy nhất tự động tạo kịch bản video, bài viết và email đồng bộ.',
              duration_seconds: '4-9s',
              audio: 'Tiết tấu trống dồn dập, hồi hộp',
              audio_hint: 'Tiết tấu trống dồn dập, hồi hộp'
            },
            {
              scene: 3,
              scene_number: 3,
              visual: 'Biểu đồ ROI chuyển sang màu xanh dương tăng trưởng mạnh, thông báo đơn hàng liên tục xuất hiện.',
              visual_action: 'Biểu đồ ROI chuyển sang màu xanh dương tăng trưởng mạnh, thông báo đơn hàng liên tục xuất hiện.',
              voiceover: 'Kiểm soát chi phí theo thời gian thực và đo lường tỷ suất lợi nhuận ROAS minh bạch trên từng điểm chạm.',
              voiceover_script: 'Kiểm soát chi phí theo thời gian thực và đo lường tỷ suất lợi nhuận ROAS minh bạch trên từng điểm chạm.',
              duration_seconds: '9-13s',
              audio: 'Nhạc nền EDM tươi sáng, phấn khởi',
              audio_hint: 'Nhạc nền EDM tươi sáng, phấn khởi'
            },
            {
              scene: 4,
              scene_number: 4,
              visual: 'Màn hình hiển thị điện thoại kèm logo thương hiệu và nút bấm kêu gọi hành động trải nghiệm.',
              visual_action: 'Màn hình hiển thị điện thoại kèm logo thương hiệu và nút bấm kêu gọi hành động trải nghiệm.',
              voiceover: 'Nhấp ngay liên kết ở bio để nhận tài khoản trải nghiệm miễn phí hôm nay!',
              voiceover_script: 'Nhấp ngay liên kết ở bio để nhận tài khoản trải nghiệm miễn phí hôm nay!',
              duration_seconds: '13-16s',
              audio: 'Sound effect Pop-up click + Âm thanh jingle kết thúc',
              audio_hint: 'Sound effect Pop-up click + Âm thanh jingle kết thúc'
            }
          ],
          suggested_audio: 'Nhạc nền synthwave hiện đại, nhịp bass dồn dập kích thích tò mò',
          sound_recommendation: 'Nhạc nền synthwave hiện đại, nhịp bass dồn dập kích thích tò mò',
          audio_suggestion: 'Nhạc nền synthwave hiện đại, nhịp bass dồn dập kích thích tò mò',
          cta: 'Nhấp vào liên kết ở bio để dùng thử miễn phí',
          hashtags: ['#marketingtips', '#tiktokbusiness', '#tudonghoa', '#marketflow', '#kinhdoanhtiktok']
        },
        email: {
          subject_options: [
            `[Độc quyền] Giải pháp bứt phá hiệu quả chiến dịch ${briefName.slice(0, 30)}`,
            'Chiến lược tiếp thị 3 kênh chủ lực giúp tối ưu hóa 40% chi phí chuyển đổi',
            'Bản tin điều hành: Cách doanh nghiệp đón đầu tăng trưởng tiếp thị 2026'
          ],
          subject_line_a: `[Độc quyền] Giải pháp bứt phá hiệu quả chiến dịch ${briefName.slice(0, 30)}`,
          subject_line_b: 'Chiến lược tiếp thị 3 kênh chủ lực giúp tối ưu hóa 40% chi phí chuyển đổi',
          preheader: 'Khám phá phương pháp điều phối tiếp thị tự động chuẩn doanh nghiệp',
          greeting: 'Kính gửi Quý Khách hàng,',
          body: `Thị trường tiếp thị số hiện nay đòi hỏi sự gắn kết liền mạch giữa các kênh truyền thông. Khi thông điệp trên mạng xã hội, video ngắn và email được đồng bộ hóa, tỷ lệ ghi nhớ thương hiệu tăng lên 3.5 lần.\n\nGiải pháp điều phối thông minh của chúng tôi giúp doanh nghiệp tự động hóa toàn diện từ khâu lập đề bài, sinh nội dung chuẩn hóa đến chốt chặn kiểm duyệt con người an toàn và đo lường chỉ số ROI thực tế.\n\nChúng tôi sẵn sàng đồng hành cùng Quý đối tác để hiện thực hóa mục tiêu tăng trưởng trong chiến dịch này.`,
          body_content: `Thị trường tiếp thị số hiện nay đòi hỏi sự gắn kết liền mạch giữa các kênh truyền thông. Khi thông điệp trên mạng xã hội, video ngắn và email được đồng bộ hóa, tỷ lệ ghi nhớ thương hiệu tăng lên 3.5 lần.\n\nGiải pháp điều phối thông minh của chúng tôi giúp doanh nghiệp tự động hóa toàn diện từ khâu lập đề bài, sinh nội dung chuẩn hóa đến chốt chặn kiểm duyệt con người an toàn và đo lường chỉ số ROI thực tế.\n\nChúng tôi sẵn sàng đồng hành cùng Quý đối tác để hiện thực hóa mục tiêu tăng trưởng trong chiến dịch này.`,
          cta_button: 'Đăng Ký Tư Vấn & Nhận Bản Phân Tích Chiến Lược',
          cta_button_text: 'Đăng Ký Tư Vấn & Nhận Bản Phân Tích Chiến Lược',
          cta_destination_type: 'Landing Page',
          ps_note: 'P.S. Chương trình tư vấn chuyên sâu 1-1 chỉ dành cho 50 đối tác đăng ký sớm nhất trong tuần này.',
          ps: 'P.S. Chương trình tư vấn chuyên sâu 1-1 chỉ dành cho 50 đối tác đăng ký sớm nhất trong tuần này.'
        }
      };
    }
  }
};

export const analyticsApi = {
  getDashboard: async () => {
    try {
      const res = await apiClient.get('/analytics/dashboard');
      const data = res.data;
      if (data?.kpi && data.kpi.roas === undefined) {
        data.kpi.roas = data.kpi.total_cost > 0 ? Number((data.kpi.total_revenue / data.kpi.total_cost).toFixed(2)) : 0.0;
      }
      return {
        ...data,
        channel_attributions: data.channel_attributions || MOCK_CHANNEL_ATTRIBUTIONS
      };
    } catch (e) {
      return { 
        kpi: MOCK_DASHBOARD_KPI,
        channel_attributions: MOCK_CHANNEL_ATTRIBUTIONS
      };
    }
  }
};

export const scheduleApi = {
  getAll: async (): Promise<MarketingSchedule[]> => {
    try {
      const res = await apiClient.get('/schedules');
      return res.data;
    } catch (e) {
      return getStoredList<MarketingSchedule>('mf_schedules', MOCK_SCHEDULES);
    }
  },
  create: async (contentId: number, scheduledAt: string, timezone = 'Asia/Ho_Chi_Minh'): Promise<MarketingSchedule> => {
    try {
      const res = await apiClient.post(`/contents/${contentId}/schedule`, {
        content_id: contentId,
        scheduled_at: scheduledAt,
        timezone
      });
      return res.data;
    } catch (e) {
      const list = getStoredList<MarketingSchedule>('mf_schedules', MOCK_SCHEDULES);
      const newSched: MarketingSchedule = {
        id: Date.now(),
        content_id: contentId,
        scheduled_at: scheduledAt,
        timezone,
        status: 'PLANNED',
        created_by: 1,
        created_at: new Date().toISOString()
      };
      setStoredList('mf_schedules', [newSched, ...list]);
      return newSched;
    }
  }
};

// AI Marketing Compliance & Policy Guardrail (Meta/Google Ads Standards)
export const evaluateMarketingCompliance = (title: string, body: string, cta?: string, bannedKeywords?: string[]): ContentComplianceCheck => {
  const fullText = `${title} ${body} ${cta || ''}`.toLowerCase();
  const flaggedItems: ContentComplianceCheck['flagged_items'] = [];
  let score = 100;

  // Rule 0: Brand Kit Banned Keywords
  if (bannedKeywords && bannedKeywords.length > 0) {
    for (const kw of bannedKeywords) {
      if (kw && kw.trim() && fullText.includes(kw.toLowerCase().trim())) {
        flaggedItems.push({
          phrase: kw.trim(),
          risk_level: 'HIGH',
          reason: 'Từ khóa cấm trong danh mục Brand Kit của Workspace',
          suggestion: `Thay thế hoặc loại bỏ từ khóa '${kw.trim()}' theo quy chuẩn thương hiệu`
        });
        score -= 35;
      }
    }
  }

  // Rule 1: Exaggerated absolute claims
  const absoluteClaims = [
    { pattern: /chắc chắn 100%/gi, phrase: 'chắc chắn 100%', reason: 'Cam kết tuyệt đối vi phạm chính sách Meta/Google Ads', suggestion: 'thay bằng "cam kết đồng hành uy tín" hoặc số liệu thực chứng' },
    { pattern: /cam kết 100%/gi, phrase: 'cam kết 100%', reason: 'Tuyên bố cam kết tuyệt đối dễ bị thuật toán quảng cáo gắn cờ', suggestion: 'thay bằng "cam kết chất lượng đào tạo chuẩn quốc tế"' },
    { pattern: /làm giàu nhanh/gi, phrase: 'làm giàu nhanh', reason: 'Nội dung hứa hẹn thu nhập thiếu căn cứ bị cấm trên mọi nền tảng', suggestion: 'thay bằng "gia tăng thu nhập bền vững nhờ kỹ năng thực chiến"' },
    { pattern: /chữa dứt điểm/gi, phrase: 'chữa dứt điểm', reason: 'Tuyên bố y tế/sức khỏe tuyệt đối bị cấm nghiêm ngặt', suggestion: 'thay bằng "hỗ trợ cải thiện rõ rệt theo lộ trình"' },
    { pattern: /kiếm tiền dễ dàng/gi, phrase: 'kiếm tiền dễ dàng', reason: 'Cụm từ bị xếp vào danh mục quảng cáo lừa đảo hoặc đa cấp', suggestion: 'thay bằng "mở rộng cơ hội việc làm công nghệ lương cao"' }
  ];

  for (const claim of absoluteClaims) {
    if (claim.pattern.test(fullText)) {
      flaggedItems.push({
        phrase: claim.phrase,
        risk_level: 'HIGH',
        reason: claim.reason,
        suggestion: claim.suggestion
      });
      score -= 25;
    }
  }

  // Rule 2: Clickbait / Spam Triggers
  const spamTriggers = [
    { pattern: /click ngay/gi, phrase: 'click ngay', reason: 'Ngôn từ ép buộc tương tác (Engagement Bait) làm giảm phân phối tự nhiên', suggestion: 'thay bằng "Khám phá ngay", "Tìm hiểu thêm" hoặc "Đăng ký tư vấn"' },
    { pattern: /rẻ nhất thị trường/gi, phrase: 'rẻ nhất thị trường', reason: 'So sánh nhất tuyệt đối thiếu chứng nhận từ cơ quan kiểm định', suggestion: 'thay bằng "mức học phí tối ưu cùng chính sách học bổng đa dạng"' }
  ];

  for (const trigger of spamTriggers) {
    if (trigger.pattern.test(fullText)) {
      flaggedItems.push({
        phrase: trigger.phrase,
        risk_level: 'MEDIUM',
        reason: trigger.reason,
        suggestion: trigger.suggestion
      });
      score -= 15;
    }
  }

  // Rule 3: Missing CTA Check
  if (!cta || cta.trim().length === 0) {
    flaggedItems.push({
      phrase: '(Thiếu Call To Action)',
      risk_level: 'LOW',
      reason: 'Bài viết chưa có nút hoặc lời kêu gọi hành động cụ thể',
      suggestion: 'Bổ sung CTA như "Đăng ký tư vấn miễn phí" hoặc "Tham gia ngay"'
    });
    score -= 10;
  }

  score = Math.max(0, Math.min(100, score));

  let status: ContentComplianceCheck['status'] = 'PASSED';
  let summary = 'Bài viết hoàn toàn đạt chuẩn tuân thủ chính sách quảng cáo của Meta và Google Ads.';

  if (score < 60) {
    status = 'VIOLATION';
    summary = 'Bài viết chứa ngôn từ có nguy cơ cao vi phạm chính sách và bị tạm khóa tài khoản quảng cáo. Cần hiệu chỉnh trước khi gửi duyệt.';
  } else if (score < 85) {
    status = 'WARNING';
    summary = 'Bài viết có một số từ ngữ nhạy cảm có thể làm giảm điểm chất lượng (Quality Score) của quảng cáo.';
  }

  return {
    score,
    status,
    summary,
    flagged_items: flaggedItems
  };
};

export const settingsApi = {
  testConnection: async (data: AIKeyTestRequest): Promise<AIKeyTestResponse> => {
    try {
      const res = await apiClient.post('/settings/test-ai-connection', data);
      return res.data;
    } catch (e: any) {
      if (e?.response?.data) {
        return e.response.data;
      }
      return {
        success: true,
        latency_ms: 120,
        message: 'Kết nối Google Gemini AI Studio thành công (Chế độ mô phỏng offline: 120ms)',
        provider: data.provider,
        model: data.model || 'gemini-2.5-flash'
      };
    }
  },

  getKeys: async (workspaceId?: number): Promise<CustomApiKey> => {
    try {
      const params = workspaceId ? { workspace_id: workspaceId } : {};
      const res = await apiClient.get('/settings/ai-keys', { params });
      return res.data;
    } catch (e: any) {
      const list = getStoredList<CustomApiKey>('custom_api_keys', MOCK_CUSTOM_API_KEYS);
      const found = workspaceId 
        ? list.find(k => k.workspace_id === workspaceId)
        : list[0];
      return found || {
        provider: 'gemini',
        model: 'gemini-2.5-flash',
        masked_key: '',
        is_active: false,
        scope: 'personal',
        status: 'NOT_CONFIGURED'
      };
    }
  },

  getKeysList: async (workspaceId?: number): Promise<CustomApiKey[]> => {
    try {
      const params = workspaceId ? { workspace_id: workspaceId } : {};
      const res = await apiClient.get('/settings/ai-keys/list', { params });
      return res.data;
    } catch (e: any) {
      const list = getStoredList<CustomApiKey>('custom_api_keys', MOCK_CUSTOM_API_KEYS);
      if (workspaceId) {
        return list.filter(k => k.workspace_id === workspaceId);
      }
      return list;
    }
  },

  saveKey: async (data: AIKeySaveRequest): Promise<AIKeySaveResponse> => {
    try {
      const res = await apiClient.post('/settings/ai-keys', data);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      const cleanKey = data.api_key.trim();
      const masked = cleanKey.length >= 10 
        ? `${cleanKey.slice(0, 6)}...${cleanKey.slice(-4)}`
        : (cleanKey.length >= 4 ? `${cleanKey.slice(0, 2)}...${cleanKey.slice(-2)}` : '...');
      
      const newKey: CustomApiKey = {
        id: Date.now(),
        provider: data.provider || 'gemini',
        model: data.model || 'gemini-2.5-flash',
        masked_key: masked,
        is_active: data.is_active !== undefined ? data.is_active : true,
        workspace_id: data.workspace_id || null,
        scope: data.workspace_id ? 'workspace' : 'personal',
        status: 'SAVED',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      const list = getStoredList<CustomApiKey>('custom_api_keys', MOCK_CUSTOM_API_KEYS);
      const filtered = list.filter(k => k.workspace_id !== data.workspace_id || !data.workspace_id);
      filtered.unshift(newKey);
      setStoredList('custom_api_keys', filtered);
      return newKey;
    }
  },

  deleteKey: async (workspaceId?: number): Promise<{ status: string; message: string }> => {
    try {
      const params = workspaceId ? { workspace_id: workspaceId } : {};
      const res = await apiClient.delete('/settings/ai-keys', { params });
      return res.data;
    } catch (e: any) {
      const list = getStoredList<CustomApiKey>('custom_api_keys', MOCK_CUSTOM_API_KEYS);
      const filtered = workspaceId ? list.filter(k => k.workspace_id !== workspaceId) : [];
      setStoredList('custom_api_keys', filtered);
      return { status: 'DEACTIVATED', message: 'Đã vô hiệu hóa khóa AI thành công.' };
    }
  },

  deleteKeyById: async (keyId: number): Promise<{ status: string; message: string }> => {
    try {
      const res = await apiClient.delete(`/settings/ai-keys/${keyId}`);
      return res.data;
    } catch (e: any) {
      const list = getStoredList<CustomApiKey>('custom_api_keys', MOCK_CUSTOM_API_KEYS);
      const filtered = list.filter(k => k.id !== keyId);
      setStoredList('custom_api_keys', filtered);
      return { status: 'DELETED', message: 'Đã xóa khóa thành công.' };
    }
  },

  toggleKey: async (keyId: number): Promise<CustomApiKey> => {
    try {
      const res = await apiClient.patch(`/settings/ai-keys/${keyId}/toggle`);
      return res.data;
    } catch (e: any) {
      const list = getStoredList<CustomApiKey>('custom_api_keys', MOCK_CUSTOM_API_KEYS);
      const item = list.find(k => k.id === keyId);
      if (item) {
        item.is_active = !item.is_active;
        item.status = item.is_active ? 'ACTIVE' : 'INACTIVE';
        setStoredList('custom_api_keys', list);
        return item;
      }
      throw e;
    }
  }
};

