import axios from 'axios';
import { Campaign, MarketingContent, KPISummary, AIIdeaResponse, AIDraftResponse, AISummaryResponse, OmnichannelRequest, OmnichannelResponse, User, Product, MarketingSchedule, ContentComplianceCheck, Workspace, BrandKit, ComplianceCheckRequest, ComplianceCheckResponse, ComplianceViolation, ChannelAttribution, AIDoctorReport, CustomApiKey, AIKeyTestRequest, AIKeyTestResponse, AIKeySaveRequest, AIKeySaveResponse, AppNotification, Task, TaskCreate, TaskUpdate, BudgetAllocation, KPITarget, CommandCenterResponse, Page, QuotaSnapshot, QuotaErrorDetail, CampaignSort, ContentSort } from '../types';
import { MarketingChannel, getChannelRegistry } from '../utils/channels';
import type {
  AIJobAccepted,
  AIJobCreateRequest,
  AIJobListResponse,
  AIJobSnapshot,
  AIJobTransport,
} from './aiJobPoller';

import { 
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

const API_BASE_URL = ((import.meta as any).env?.VITE_API_URL ||
  ((import.meta as any).env?.PROD ? '/api/v1' : 'http://127.0.0.1:8000/api/v1'));

/**
 * Base URL riêng cho nhóm endpoint AI.
 *
 * VÌ SAO PHẢI TÁCH:
 * Cloudflare Worker có giới hạn ~100 giây cho một subrequest. Đo thật trên
 * production: `POST /api/v1/ai/omnichannel` qua Worker trả về `error code: 524`
 * (Cloudflare timeout) sau ~100s, trong khi gọi thẳng Render cùng endpoint đó
 * trả 200 sau **237 giây** với `is_fallback=false`. Tức là mọi lời gọi AI qua
 * Worker đều chết, dù backend hoàn toàn ổn.
 *
 * Cách sửa: chỉ nhóm `/ai/*` đi thẳng Render, các endpoint còn lại vẫn qua
 * Worker (giữ được một domain, không lộ URL backend cho người dùng thường).
 * CORS đã cho phép sẵn origin `https://marketing.kienhieu.id.vn` qua
 * `ALLOWED_ORIGIN_REGEXES` trong backend/app/core/config.py.
 *
 * Rỗng/rỗng-không-cấu-hình => rơi về API_BASE_URL, tức hành vi cũ. Khi đó AI
 * sẽ lại gặp 524 — nhưng đó là lỗi cấu hình hiển thị được, không phải im lặng.
 */
const AI_BASE_URL = ((import.meta as any).env?.VITE_AI_API_URL || '').replace(/\/+$/, '');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  // 60s chỉ đủ cho cold start của Render Free Tier. Các endpoint AI thật cần
  // lâu hơn nhiều: /ai/omnichannel sinh đồng thời 3 kênh (Facebook + TikTok 4
  // cảnh + Email A/B) nên đo thực tế là 83–174 giây. Với timeout 60s, axios
  // huỷ request giữa chừng và trình duyệt báo ERR_ABORTED — người dùng thấy
  // "Lỗi khi gọi AI" dù backend vẫn chạy và có thể đã trả kết quả.
  // Timeout riêng cho nhóm AI được đặt ở `AI_LONG_TIMEOUT` bên dưới.
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Timeout cho các lời gọi sinh nội dung AI.
 * Backend đặt AI_TIMEOUT_SECONDS=420 và có retry, nên phía client phải chờ
 * lâu hơn để không cắt ngang. Đo thực tế /ai/omnichannel với model opencode:
 * 83–214 giây cho một lần gọi thành công (3 kênh, TikTok 4 cảnh, Email A/B).
 * Client đặt trần 600s — rộng hơn server để server kịp trả lỗi có kiểm soát,
 * không phải bị client cắt ngang.
 */
const AI_LONG_TIMEOUT = 600000;

/**
 * Danh sách path AI cần timeout dài (khớp prefix router backend `/api/v1/ai`).
 *
 * `/ai/jobs` nằm trong danh sách vì lý do NHẤT QUÁN, không vì cần thời gian chờ:
 * `POST /ai/jobs` trả 202 và `GET /ai/jobs/{id}` trả vài trăm byte, đều nhanh. Nhưng
 * đây vẫn là nhóm `/ai/*` và đi cùng đường với endpoint đồng bộ, nên cho nó cùng
 * một cơ chế định tuyến thay vì tạo ra một đường thứ hai chỉ vì "nhanh". Hệ quả:
 * nếu `VITE_AI_API_URL` rỗng (cấu hình sai), hàng đợi sẽ đi qua Worker — lỗi đó
 * hiện ra dưới dạng message có kiểm chứng thay vì im lặng.
 */
const isAiPath = (url?: string): boolean =>
  !!url && (url.includes('/ai/omnichannel') || url.includes('/ai/generate') || url.includes('/ai/draft') || url.includes('/ai/ideas') || url.includes('/ai/summary') || url.includes('/ai/summarize') || url.includes('/ai/jobs') || url.includes('/ai-doctor'));

// Helper kiểm tra chế độ Demo Offline (chỉ kích hoạt khi có cờ VITE_ENABLE_OFFLINE_DEMO=true tường minh)
//
// QUYẾT ĐỊNH CẦN NGƯỜI DÙNG CHỐT - KHÔNG tự ý thêm điều kiện `import.meta.env.PROD !== true`:
//   Demo Cloudflare Pages được phục vụ bằng chính một bản build production, nên `import.meta.env.PROD`
//   luôn là `true` ở đúng nơi demo được dùng. Thêm điều kiện đó sẽ biến cờ thành vô hiệu vĩnh viễn
//   và phá vỡ nhu cầu demo đã được ghi rõ trong .env.example ("môi trường trình diễn giao diện,
//   như Cloudflare Pages không kèm backend"). Hàng rào hiện tại là biến môi trường tường minh
//   (mặc định false trong .env, Dockerfile và .env.example đều khoá false).
export const isOfflineDemoEnabled = (): boolean => import.meta.env.VITE_ENABLE_OFFLINE_DEMO === 'true';

// Nhan nguon goc cho du lieu mau cuc bo.
//
// KHI backend khong tra loi, frontend tra ve noi dung mau gan san. Nhung doan
// do KHONG phai do AI viet, va KHONG duoc gan nhan ten model nao - neu gan,
// nguoi dung se tin rang Gemini (hoac bat ky model nao) da that su sinh ra
// noi dung, trong khi thuc te may chay hoan toan khong co mang.
//
// Nhan duoc dung o day de moi noi dung demo deu bao nguon goc dung mot cach,
// va de test kiem tra duoc rang buoc nay bang cach so sanh chuoi cu the.
export const OFFLINE_DEMO_PROVIDER = 'offline-demo-fixture';
export const OFFLINE_DEMO_MODEL_LABEL = 'Dữ liệu mẫu cục bộ (không gọi AI)';

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

// =========================================================================
// CƠ CHẾ CHỈ BÁO MÁY CHỦ THỨC DẬY (SERVER AWAKENING INDICATOR FOR RENDER)
// =========================================================================
export interface ServerAwakeningStatus {
  isWakingUp: boolean;
  elapsedSeconds: number;
  message?: string;
}

type AwakeningListener = (status: ServerAwakeningStatus) => void;
let awakeningListeners: AwakeningListener[] = [];
let activeRequestsCount = 0;
let awakeningTimer: any = null;
let secondsInterval: any = null;
let elapsedCount = 0;
let isAwakeningActive = false;

export const subscribeServerAwakening = (listener: AwakeningListener): (() => void) => {
  awakeningListeners.push(listener);
  // Cung cấp ngay trạng thái hiện tại cho subscriber mới
  listener({
    isWakingUp: isAwakeningActive,
    elapsedSeconds: elapsedCount,
    message: isAwakeningActive ? `Đang đánh thức máy chủ backend (${elapsedCount}s)...` : undefined
  });
  return () => {
    awakeningListeners = awakeningListeners.filter(l => l !== listener);
  };
};

const broadcastAwakening = (status: ServerAwakeningStatus) => {
  awakeningListeners.forEach(fn => {
    try {
      fn(status);
    } catch (e) {
      console.error('Error in awakening listener:', e);
    }
  });
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('server-awakening', { detail: status }));
  }
};

// Gắn Bearer token tự động, workspace hiện hành & theo dõi cold start Render
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Workspace đang chọn trên UI phải là tiêu chí lọc duy nhất phía server.
  // Thiếu header này thì backend rơi về "WorkspaceMember đầu tiên", tức là
  // người dùng chọn workspace B vẫn nhìn thấy dữ liệu của workspace A.
  const workspaceId = localStorage.getItem('active_workspace_id');
  if (workspaceId) {
    config.headers['X-Workspace-Id'] = workspaceId;
  }

  // Timeout riêng cho lời gọi AI (xem giải thích cạnh AI_LONG_TIMEOUT).
  if (isAiPath(config.url)) {
    config.timeout = AI_LONG_TIMEOUT;
    // Định tuyến AI thẳng về Render, BỎ QUA Worker. Cloudflare chặn subrequest
    // ~100s nên mọi lời gọi AI đi qua Worker đều nhận 524; đo thật trên
    // production: qua Worker = 524, gọi thẳng Render = 200 sau 237s với
    // `is_fallback=false`. Xem giải thích dài ở AI_BASE_URL.
    if (AI_BASE_URL) {
      const path = String(config.url || '').replace(/^\//, '');
      config.baseURL = AI_BASE_URL;
      config.url = path;
    }
  }

  activeRequestsCount++;
  if (activeRequestsCount === 1) {
    if (awakeningTimer) clearTimeout(awakeningTimer);
    elapsedCount = 0;
    // Nếu request kéo dài hơn 3.5 giây, máy chủ Render nhiều khả năng đang ngủ đông
    awakeningTimer = setTimeout(() => {
      isAwakeningActive = true;
      elapsedCount = 3;
      broadcastAwakening({
        isWakingUp: true,
        elapsedSeconds: elapsedCount,
        message: 'Đang đánh thức máy chủ backend (Render Cloud)...'
      });
      if (secondsInterval) clearInterval(secondsInterval);
      secondsInterval = setInterval(() => {
        elapsedCount++;
        broadcastAwakening({
          isWakingUp: true,
          elapsedSeconds: elapsedCount,
          message: `Đang đánh thức máy chủ backend (${elapsedCount}s/60s)...`
        });
      }, 1000);
    }, 3500);
  }

  return config;
});

let backendReachable = true;

const cleanupAwakeningTracking = () => {
  activeRequestsCount = Math.max(0, activeRequestsCount - 1);
  if (activeRequestsCount === 0) {
    if (awakeningTimer) {
      clearTimeout(awakeningTimer);
      awakeningTimer = null;
    }
    if (secondsInterval) {
      clearInterval(secondsInterval);
      secondsInterval = null;
    }
    if (isAwakeningActive) {
      isAwakeningActive = false;
      broadcastAwakening({
        isWakingUp: false,
        elapsedSeconds: 0,
        message: 'Máy chủ đã sẵn sàng!'
      });
    }
    elapsedCount = 0;
  }
};

apiClient.interceptors.response.use(
  (response) => {
    cleanupAwakeningTracking();
    backendReachable = true;
    return response;
  },
  (error) => {
    cleanupAwakeningTracking();
    if (!error?.response) {
      backendReachable = false;
      return Promise.reject(error);
    }
    // Phiên hết hạn / bị thu hồi: dọn token để AuthContext mount lại và hiện
    // màn hình đăng nhập. Trước đây 401 chỉ nổi lên thành một toast rời rạc,
    // người dùng phải tự đoán rồi đăng nhập lại.
    const status = error.response.status;
    if (status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('current_user');
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }
    return Promise.reject(error);
  }
);

export const isBackendConnected = (): boolean => backendReachable;

// Helper trích xuất thông báo lỗi chuẩn từ FastAPI backend hoặc lỗi mạng
export const getApiErrorMessage = (error: any): string => {
  // Lỗi hạn mứng có thân riêng — trả về thông báo cụ thể thay vì JSON.stringify
  // đống chữ. Xem `isQuotaError`.
  const quota = getQuotaError(error);
  if (quota) return quota.message;
  if (!error?.response) {
    if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
      return 'Máy chủ backend (Render) đang khởi động lại (cold start) hoặc phản hồi quá thời gian chờ (60s). Vui lòng thử lại sau giây lát.';
    }
    return 'Không thể kết nối đến máy chủ backend. Máy chủ (Render) có thể đang ngủ đông hoặc khởi động lại. Vui lòng thử lại sau 30-50 giây.';
  }
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

/**
 * Nhận diện lỗi hạn mứng (429 với `detail.error === 'quota_exceeded'`).
 *
 * Backend trả thân có cấu trúc để client KHÔNG phải đoán: `limit_code` cho biết
 * vượt trần nào, `used`/`limit` để vẽ thanh tiến trình, `resets_at` để đếm
 * ngược. Trả `null` nếu không phải lỗi hạn mứng.
 */
export const getQuotaError = (error: any): QuotaErrorDetail | null => {
  const detail = error?.response?.data?.detail;
  if (detail && typeof detail === 'object' && detail.error === 'quota_exceeded') {
    return detail as QuotaErrorDetail;
  }
  return null;
};

/** Chuẩn hoá mọi hình dạng response về `Page<T>`.

 * Chấp nhận CẢ mảng phẳng lẫn envelope `Page`. Nhánh mảng phẳng là để các
 * endpoint chưa chuyển sang phân trang (kênh, sản phẩm, nhóm kênh — dữ liệu
 * tham chiếu tĩnh, có trần nhỏ và cố định) vẫn dùng chung được component
 * `<Pagination>` mà không phải rẽ nhánh ở từng màn hình.
 */
export const toPage = <T,>(data: any, fallbackPage = 1, fallbackPageSize = 20): Page<T> => {
  if (Array.isArray(data)) {
    return {
      items: data as T[],
      total: data.length,
      page: fallbackPage,
      page_size: fallbackPageSize,
      total_pages: data.length === 0 ? 0 : 1,
      has_next: false,
      has_prev: fallbackPage > 1,
    };
  }
  return {
    items: (data?.items ?? []) as T[],
    total: data?.total ?? 0,
    page: data?.page ?? fallbackPage,
    page_size: data?.page_size ?? fallbackPageSize,
    total_pages: data?.total_pages ?? 0,
    has_next: Boolean(data?.has_next),
    has_prev: Boolean(data?.has_prev),
  };
};

/** Bỏ các tham số phân trang rỗng khỏi query để không gửi `page=undefined`. */
export const withPaging = (
  params: Record<string, any> | undefined,
  page: number,
  pageSize: number,
): Record<string, any> => ({ ...(params || {}), page, page_size: pageSize });

export const authApi = {
  login: async (email: string, password: string): Promise<{ access_token: string; user: User }> => {
    try {
      const res = await apiClient.post('/auth/login', { email, password });
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('current_user', JSON.stringify(res.data.user));
      return res.data;
    } catch (e: any) {
      // Tuyệt đối không cấp phiên đăng nhập giả khi backend không phản hồi:
      // suy đoán quyền từ chuỗi email là đường vòng leo thang đặc quyền.
      if (e?.response) {
        throw e;
      }
      if (e?.code === 'ECONNABORTED' || e?.message?.includes('timeout')) {
        throw new Error(getApiErrorMessage(e));
      }
      throw new Error(getApiErrorMessage(e));
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
    // localStorage.getItem và JSON.parse đều có thể ném exception (current_user bị hỏng,
    // storage bị chặn ở chế độ riêng tư). Không được để lỗi này ném ra khỏi quá trình render,
    // và cũng không được coi dữ liệu đọc được là bằng chứng phiên còn hiệu lực.
    try {
      const userStr = localStorage.getItem('current_user');
      if (!userStr) return null;
      const parsed = JSON.parse(userStr);
      if (!parsed || typeof parsed !== 'object') return null;
      return parsed as User;
    } catch {
      return null;
    }
  },
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
    localStorage.removeItem('active_workspace_id');
  }
};

export const workspaceApi = {
  /** Bản có phân trang — dùng khi cần biết `total` để dựng nút trang. */
  getAllPage: async (page = 1, pageSize = 20): Promise<Page<Workspace>> => {
    try {
      const res = await apiClient.get('/workspaces', { params: { page, page_size: pageSize } });
      return toPage<Workspace>(res.data, page, pageSize);
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: workspaceApi.getAll');
      return toPage<Workspace>(getStoredList<Workspace>('mf_workspaces', MOCK_WORKSPACES), page, pageSize);
    }
  },

  getAll: async (): Promise<Workspace[]> => {
    try {
      const res = await apiClient.get('/workspaces');
      return toPage<Workspace>(res.data).items;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: workspaceApi.getAll');
      return getStoredList<Workspace>('mf_workspaces', MOCK_WORKSPACES);
    }
  },
  create: async (data: { name: string; description?: string; slug?: string }): Promise<Workspace> => {
    try {
      const res = await apiClient.post('/workspaces', data);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: workspaceApi.create');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: workspaceApi.getById');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: workspaceApi.update');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: brandKitApi.getByWorkspace');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: brandKitApi.update');
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
  /**
   * Bản có phân trang. `page`/`pageSize` được ghép SAU các tham số lọc, và
   * backend áp lọc trước rồi mới cắt trang — nên `total` là tổng của tập đã lọc.
   */
  getAllPage: async (
    page = 1,
    pageSize = 20,
    filters?: { status?: string; search?: string; workspaceId?: number; sort?: CampaignSort; objective?: string },
  ): Promise<Page<Campaign>> => {
    const params: Record<string, any> = {};
    if (filters?.status) params.status = filters.status;
    if (filters?.search) params.search = filters.search;
    if (filters?.workspaceId) params.workspace_id = filters.workspaceId;
    if (filters?.sort) params.sort = filters.sort;
    if (filters?.objective) params.objective = filters.objective;
    try {
      const res = await apiClient.get('/campaigns', { params: withPaging(params, page, pageSize) });
      return toPage<Campaign>(res.data, page, pageSize);
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.getAllPage');
      let list = getStoredList<Campaign>('mf_campaigns', MOCK_CAMPAIGNS);
      if (filters?.workspaceId) {
        list = list.filter(c => !c.workspace_id || c.workspace_id === filters.workspaceId);
      }
      if (filters?.status && filters.status !== 'ALL') {
        list = list.filter(c => c.status === filters.status);
      }
      if (filters?.search) {
        const q = filters.search.toLowerCase();
        list = list.filter(c => c.name.toLowerCase().includes(q));
      }
      if (filters?.objective) {
        const q = filters.objective.toLowerCase();
        list = list.filter(c => (c.objective || '').toLowerCase().includes(q));
      }
      const total = list.length;
      const start = (page - 1) * pageSize;
      return {
        items: list.slice(start, start + pageSize),
        total,
        page,
        page_size: pageSize,
        total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
        has_next: page * pageSize < total,
        has_prev: page > 1,
      };
    }
  },

  getAll: async (status?: string, search?: string, workspaceId?: number): Promise<Campaign[]> => {
    try {
      const params: Record<string, any> = {};
      if (status) params.status = status;
      if (search) params.search = search;
      if (workspaceId) params.workspace_id = workspaceId;
      const res = await apiClient.get('/campaigns', { params });
      return toPage<Campaign>(res.data).items;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.getAll');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.getById');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.create');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.update');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.getKpi');
      return MOCK_DASHBOARD_KPI;
    }
  },
  getAIDoctor: async (campaignId: number): Promise<AIDoctorReport> => {
    try {
      const res = await apiClient.post(`/campaigns/${campaignId}/ai-doctor`);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.getAIDoctor');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.getAttribution');
      return MOCK_CHANNEL_ATTRIBUTIONS;
    }
  },
  /** Nội dung của chiến dịch, có phân trang + lọc trạng thái / tìm kiếm / sắp xếp. */
  getContentsPage: async (
    campaignId: number,
    page = 1,
    pageSize = 20,
    filters?: { status?: string; search?: string; sort?: ContentSort },
  ): Promise<Page<MarketingContent>> => {
    const params: Record<string, any> = {};
    if (filters?.status) params.status = filters.status;
    if (filters?.search) params.search = filters.search;
    if (filters?.sort) params.sort = filters.sort;
    try {
      const res = await apiClient.get(`/campaigns/${campaignId}/contents`, {
        params: withPaging(params, page, pageSize),
      });
      return toPage<MarketingContent>(res.data, page, pageSize);
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.getContentsPage');
      let list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS)
        .filter(c => c.campaign_id === campaignId);
      if (filters?.status && filters.status !== 'ALL') {
        list = list.filter(c => c.status === filters.status);
      }
      if (filters?.search) {
        const q = filters.search.toLowerCase();
        list = list.filter(c => (c.title || '').toLowerCase().includes(q));
      }
      const total = list.length;
      const start = (page - 1) * pageSize;
      return {
        items: list.slice(start, start + pageSize),
        total,
        page,
        page_size: pageSize,
        total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
        has_next: page * pageSize < total,
        has_prev: page > 1,
      };
    }
  },

  getContents: async (campaignId: number): Promise<MarketingContent[]> => {
    try {
      const res = await apiClient.get(`/campaigns/${campaignId}/contents`);
      return toPage<MarketingContent>(res.data).items;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.getContents');
      const list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
      return list.filter(c => c.campaign_id === campaignId);
    }
  },
  delete: async (id: number): Promise<void> => {
    try {
      await apiClient.delete(`/campaigns/${id}`);
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: campaignApi.delete');
      const list = getStoredList<Campaign>('mf_campaigns', MOCK_CAMPAIGNS);
      setStoredList('mf_campaigns', list.filter(c => c.id !== id));
    }
  }
};

export const channelApi = {
  getAll: async (): Promise<MarketingChannel[]> => {
    try {
      const res = await apiClient.get('/channels');
      return res.data || [];
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] No channel mock available; using the seed-order fallback registry');
      return getChannelRegistry();
    }
  }
};

export const productApi = {
  getAll: async (): Promise<Product[]> => {
    try {
      const res = await apiClient.get('/products');
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: productApi.getAll');
      return MOCK_PRODUCTS;
    }
  }
};

/** Lọc danh sách nội dung trong kho mock offline — dùng chung cho cả hai bản
 *  (`getAllPage` có phân trang và `getAll` trả mảng) để hai đường không lệch nhau. */
const _filterMockContents = (filters?: {
  campaignId?: number; status?: string; channelId?: number; search?: string; workspaceId?: number;
}): MarketingContent[] => {
  let list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
  if (filters?.workspaceId) list = list.filter(c => !c.workspace_id || c.workspace_id === filters.workspaceId);
  if (filters?.campaignId) list = list.filter(c => c.campaign_id === filters.campaignId);
  if (filters?.status && filters.status !== 'ALL') list = list.filter(c => c.status === filters.status);
  if (filters?.channelId) list = list.filter(c => c.channel_id === filters.channelId);
  if (filters?.search) {
    const q = filters.search.toLowerCase();
    list = list.filter(c =>
      (c.title || '').toLowerCase().includes(q) || (c.body || '').toLowerCase().includes(q));
  }
  return list;
};

export const contentApi = {
  /** Danh sách nội dung có phân trang + tìm kiếm + lọc + sắp xếp. */
  getAllPage: async (
    page = 1,
    pageSize = 20,
    filters?: { campaignId?: number; status?: string; channelId?: number; search?: string; sort?: ContentSort },
  ): Promise<Page<MarketingContent>> => {
    const params: Record<string, any> = {};
    if (filters?.campaignId) params.campaign_id = filters.campaignId;
    if (filters?.status) params.status = filters.status;
    if (filters?.channelId) params.channel_id = filters.channelId;
    if (filters?.search) params.search = filters.search;
    if (filters?.sort) params.sort = filters.sort;
    try {
      const res = await apiClient.get('/contents', { params: withPaging(params, page, pageSize) });
      return toPage<MarketingContent>(res.data, page, pageSize);
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: contentApi.getAllPage');
      const list = _filterMockContents(filters);
      const total = list.length;
      const start = (page - 1) * pageSize;
      return {
        items: list.slice(start, start + pageSize),
        total,
        page,
        page_size: pageSize,
        total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
        has_next: page * pageSize < total,
        has_prev: page > 1,
      };
    }
  },

  getAll: async (campaignId?: number, status?: string, workspaceId?: number): Promise<MarketingContent[]> => {
    try {
      const params: Record<string, any> = {};
      if (campaignId) params.campaign_id = campaignId;
      if (status) params.status = status;
      if (workspaceId) params.workspace_id = workspaceId;
      const res = await apiClient.get('/contents', { params });
      // Backend đã chuyển sang envelope `Page` — phải bóc `.items`, không trả
      // thẳng `res.data`. Trả thẳng sẽ đưa OBJECT vào state kiểu `MarketingContent[]`
      // và làm hỏng mọi `.filter` phía sau (biểu hiện: "p.filter is not a
      // function" và toàn bộ giao diện rơi vào ErrorBoundary).
      return toPage<MarketingContent>(res.data).items;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: contentApi.getAll');
      return _filterMockContents({ campaignId, status, workspaceId });
    }
  },

  create: async (data: Partial<MarketingContent>): Promise<MarketingContent> => {
    try {
      const res = await apiClient.post('/contents', data);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: contentApi.create');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: contentApi.update');
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
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: contentApi.checkCompliance');
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
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: contentApi.submitForReview');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: contentApi.approve');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: contentApi.reject');
      const list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
      const updated = list.map(c => c.id === id ? { ...c, status: 'REJECTED' as const, rejection_reason: reason } : c);
      setStoredList('mf_contents', updated);
      return updated.find(c => c.id === id)!;
    }
  },
  publish: async (id: number): Promise<MarketingContent> => {
    try {
      const res = await apiClient.post(`/contents/${id}/publish`);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: contentApi.publish');
      const list = getStoredList<MarketingContent>('mf_contents', MOCK_CONTENTS);
      const updated = list.map(c => c.id === id ? { ...c, status: 'PUBLISHED' as const } : c);
      setStoredList('mf_contents', updated);
      return updated.find(c => c.id === id)!;
    }
  }
};

// ===========================================================================
// HÀNG ĐỢI AI BẤT ĐỒNG BỘ (POST /ai/jobs → poll GET /ai/jobs/{id})
// ===========================================================================
//
// VÌ SAO THÊM, KHI CÁC ENDPOINT ĐỒNG BỘ VẪN CÒN:
// Endpoint đồng bộ (`aiApi` bên dưới) là hàm `def`, mỗi lượt gọi giữ một thread
// của worker suốt thời gian chờ LLM. Đo thật trên production: `/ai/omnichannel`
// mất 237 giây, Cloudflare Worker phía trước cắt ở ~100 giây và trả
// `error code: 524`. Hàng đợi mới trả 202 ngay và để worker nền gọi LLM.
//
// Endpoint đồng bộ GIỮ NGUYÊN vì backend đánh dấu deprecated nhưng vẫn có thể
// còn được dùng. Ở đây chỉ thêm đường mới, không sửa đường cũ.

/**
 * Job "ảo" cho chế độ Demo Offline.
 *
 * Chỉ dùng khi `VITE_ENABLE_OFFLINE_DEMO=true` và backend không phản hồi: khi
 * đó `POST /ai/jobs` không có nơi để đẩy job, nên ta tự tạo một job đã xong ngay
 * với nội dung mẫu của `aiApi`. Nhãn nguồn gốc vẫn do `aiApi` gán
 * (`is_fallback=true`, `model_used=OFFLINE_DEMO_MODEL_LABEL`) nên không bao giờ
 * bị trình bày như kết quả do AI thật tạo ra.
 */
const offlineDemoJobs = new Map<number, AIJobSnapshot>();
let nextOfflineDemoJobId = 1;

const buildOfflineDemoSnapshot = async (
  request: AIJobCreateRequest,
): Promise<AIJobSnapshot> => {
  // Gọi lại đúng hàm đồng bộ để dùng lại đúng bộ nội dung mẫu và đúng nhãn
  // nguồn gốc (`is_fallback=true`, `model_used=OFFLINE_DEMO_MODEL_LABEL`).
  const campaignId = typeof request.campaign_id === 'number' ? request.campaign_id : null;
  let result: Record<string, unknown>;
  switch (request.kind) {
    case 'ideas':
      result = (await aiApi.generateIdeas(campaignId, request.channel_code ?? 'facebook', request.prompt_version ?? 'v3', {
        topic: request.custom_topic,
        product: request.custom_product,
        usp: request.custom_usp,
        tone: request.tone,
      })) as unknown as Record<string, unknown>;
      break;
    case 'draft':
      result = (await aiApi.generateDraft(campaignId, request.selected_idea, request.channel_code ?? 'facebook', request.prompt_version ?? 'v3', {
        product: request.custom_product,
        usp: request.custom_usp,
      })) as unknown as Record<string, unknown>;
      break;
    case 'summary':
      result = (await aiApi.generateSummary(campaignId ?? 1, request.prompt_version ?? 'v3')) as unknown as Record<string, unknown>;
      break;
    case 'omnichannel':
      result = (await aiApi.generateOmnichannel({
        brief: request.brief ?? 'Demo offline',
        campaign_id: campaignId,
        channels: request.channels ?? ['facebook', 'tiktok', 'email'],
        product_name: request.product_name,
        product_usp: request.product_usp,
        prompt_version: request.prompt_version,
      })) as unknown as Record<string, unknown>;
      break;
    default:
      result = {};
  }
  const id = nextOfflineDemoJobId++;
  const snapshot: AIJobSnapshot = {
    job_id: id,
    kind: request.kind,
    status: 'succeeded',
    attempts: 1,
    max_attempts: 3,
    error: null,
    result,
    queued_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
  };
  offlineDemoJobs.set(id, snapshot);
  return snapshot;
};

export const aiJobsApi = {
  /**
   * Đẩy một tác vụ AI vào hàng đợi. Trả 202 ngay, không chờ LLM.
   *
   * `idempotency_key` do `createAIJobTask` sinh: gửi lại cùng khoá + cùng payload
   * thì backend trả lại đúng job cũ, không tạo thêm lượt gọi AI nào (và không
   * trừ hạn mứng lần hai).
   */
  enqueue: async (request: AIJobCreateRequest): Promise<AIJobAccepted> => {
    try {
      const res = await apiClient.post('/ai/jobs', request);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] aiJobsApi.enqueue: không có backend, dựng job mẫu cục bộ');
      const snapshot = await buildOfflineDemoSnapshot(request);
      return {
        job_id: snapshot.job_id,
        status: snapshot.status,
        kind: snapshot.kind,
        deduplicated: false,
        poll_url: `/api/v1/ai/jobs/${snapshot.job_id}`,
      };
    }
  },

  getJob: async (jobId: number): Promise<AIJobSnapshot> => {
    const demo = offlineDemoJobs.get(jobId);
    if (demo) {
      offlineDemoJobs.delete(jobId);
      return demo;
    }
    const res = await apiClient.get(`/ai/jobs/${jobId}`);
    return res.data;
  },

  cancelJob: async (jobId: number): Promise<AIJobAccepted> => {
    const demo = offlineDemoJobs.get(jobId);
    if (demo) {
      offlineDemoJobs.delete(jobId);
      return { job_id: jobId, status: 'cancelled', kind: demo.kind, deduplicated: false, poll_url: `/api/v1/ai/jobs/${jobId}` };
    }
    const res = await apiClient.post(`/ai/jobs/${jobId}/cancel`);
    return res.data;
  },

  list: async (params?: {
    status?: string;
    kind?: string;
    page?: number;
    page_size?: number;
  }): Promise<AIJobListResponse> => {
    const res = await apiClient.get('/ai/jobs', { params });
    return res.data;
  },
};

/** Transport đưa hàng đợi thật vào `createAIJobTask`. */
export const aiJobTransport: AIJobTransport = {
  enqueue: (request) => aiJobsApi.enqueue(request),
  getJob: (jobId) => aiJobsApi.getJob(jobId),
  cancelJob: (jobId) => aiJobsApi.cancelJob(jobId),
};

/**
 * Hạn mức gói miễn phí của workspace — dùng để hiện số đã dùng / trần và đếm
 * ngược tới lúc hết hạn, để người dùng thấy trước khi bị chặn.
 */
export const quotaApi = {
  get: async (workspaceId: number): Promise<QuotaSnapshot | null> => {
    try {
      const res = await apiClient.get(`/workspaces/${workspaceId}/quota`);
      return res.data as QuotaSnapshot;
    } catch (e: any) {
      // Hạn mức chỉ là thông tin hiển thị: không có nó thì màn hình vẫn dùng
      // được, nên nuốt lỗi thay vì làm hỏng cả trang. Endpoint thực thi hạn
      // mứng vẫn chặn ở server như thường.
      console.warn('[Quota] Không đọc được hạn mứng, tiếp tục không hiển thị.', e?.message);
      return null;
    }
  },
};

/** Định dạng mốc hết hạn cho UI: "còn 2 giờ 15 phút" hoặc "23:59 ngày mai". */
export const describeQuotaReset = (resetsAt: string | null, now: Date = new Date()): string => {
  if (!resetsAt) return 'Không tự đặt lại';
  const target = new Date(resetsAt);
  if (Number.isNaN(target.getTime())) return '';
  const ms = target.getTime() - now.getTime();
  if (ms <= 0) return 'Đã hết hạn';
  const minutes = Math.floor(ms / 60000);
  const hours = Math.floor(minutes / 60);
  if (hours >= 1) return hours >= 24 ? `${Math.floor(hours / 24)} ngày` : `còn ${hours} giờ ${minutes % 60} phút`;
  if (minutes >= 1) return `còn ${minutes} phút`;
  return `còn ${Math.max(1, Math.floor(ms / 1000))} giây`;
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: aiApi.generateIdeas');
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
        model_used: OFFLINE_DEMO_MODEL_LABEL,
        model_provider: OFFLINE_DEMO_PROVIDER,
        is_fallback: true,
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: aiApi.generateDraft');
      return {
        task_type: 'DRAFT',
        title: 'Bí quyết Bứt phá Doanh số Đa kênh 2026 Nhờ Tự Động Hóa AI',
        body: 'Thị trường marketing số 2026 đòi hỏi tốc độ thử nghiệm và tối ưu hóa vượt bậc. Với sự trợ giúp từ MarketFlow AI, bạn có thể triển khai hàng chục mẫu quảng cáo tuân thủ chính sách, theo dõi ROI theo thời gian thực và phân bổ ngân sách chuẩn xác.',
        cta: 'Đăng ký nhận tài liệu và dùng thử miễn phí',
        warnings: [],
        assumptions: ['Định dạng kênh tương thích cao'],
        model_used: OFFLINE_DEMO_MODEL_LABEL,
        model_provider: OFFLINE_DEMO_PROVIDER,
        is_fallback: true,
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: aiApi.generateSummary');
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
        model_used: OFFLINE_DEMO_MODEL_LABEL,
        model_provider: OFFLINE_DEMO_PROVIDER,
        is_fallback: true,
        prompt_version: 'v3'
      };
    }
  },
  generateOmnichannel: async (req: OmnichannelRequest): Promise<OmnichannelResponse> => {
    try {
      const res = await apiClient.post('/ai/omnichannel', req);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: aiApi.generateOmnichannel');
      const briefName = req.brief || 'Chiến dịch Tiếp thị Toàn diện';
      return {
        task_type: 'OMNICHANNEL',
        model_used: OFFLINE_DEMO_MODEL_LABEL,
        model_provider: OFFLINE_DEMO_PROVIDER,
        is_fallback: true,
        warnings: [],
        compliance_score: 100,
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
      // KHÔNG gắn `|| MOCK_*` vào đường online. Trước đây response backend không
      // có `channel_attributions`, nên Dashboard âm thầm vẽ mảng số liệu bịa đặt và
      // người dùng không có cách nào biết đó không phải số đo thật. Giờ thiếu dữ
      // liệu thì hiển thị trạng thái rỗng trung thực.
      return {
        ...data,
        channel_attributions: data.channel_attributions ?? [],
        // Nguồn gốc số liệu từ backend. `has_demo_data=true` nghĩa là trong tổng
        // số đang hiển thị có dòng do dữ liệu MẪU nạp vào, không phải số đo
        // thật từ nền tảng quảng cáo. Dashboard dùng field này để hiện cảnh báo
        // — mặc định an toàn là coi như CÓ dữ liệu mẫu khi backend chưa trả
        // field, thay vì âm thầm coi mọi thứ là số thật.
        data_provenance: data.data_provenance ?? {
          has_demo_data: false,
          has_unverified_data: false,
          seed_rows: 0,
          unverified_rows: 0,
          real_rows: 0,
          total_rows: 0,
        },
        // Chi phí theo chiến dịch để bảng tính nhịp chi tiêu; mặc định rỗng nghĩa
        // là chưa có chỉ số nào để hiển thị (không phải 0 đã chi).
        campaign_spend: data.campaign_spend ?? {},
        kpi: {
          ...data.kpi,
          channel_metrics: data.kpi?.channel_metrics ?? []
        }
      };
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: analyticsApi.getDashboard');
      return {
        kpi: MOCK_DASHBOARD_KPI,
        channel_attributions: MOCK_CHANNEL_ATTRIBUTIONS
      };
    }
  }
};

export const metricsApi = {
  getCampaignMetrics: async (campaignId: number): Promise<any[]> => {
    try {
      const res = await apiClient.get(`/campaigns/${campaignId}/metrics`);
      return res.data || [];
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: metricsApi.getCampaignMetrics');
      return [];
    }
  },
  getCampaignKpi: async (campaignId: number): Promise<KPISummary> => {
    return campaignApi.getKpi(campaignId);
  },
  getCampaignAttribution: async (campaignId: number): Promise<ChannelAttribution[]> => {
    return campaignApi.getAttribution(campaignId);
  },
  getDashboardOverview: async () => {
    return analyticsApi.getDashboard();
  },
  getAllCampaignsMetrics: async (signal?: AbortSignal): Promise<any[]> => {
    try {
      const campaigns = await campaignApi.getAll();
      if (!campaigns || campaigns.length === 0) return [];
      // KHÔNG nuốt lỗi ở tầng per-campaign. `.catch(() => [])` trước đây biến 401/403/500
      // của từng chiến dịch thành "không có số liệu", đúng cái che lỗi cần loại bỏ.
      // Lỗi giờ nổi lên Promise.all rồi được xử lý bằng cùng khuôn mẫu chuẩn của file này.
      const metricPromises = campaigns.map(c =>
        apiClient.get(`/campaigns/${c.id}/metrics`, { signal }).then(r => r.data || [])
      );
      const results = await Promise.all(metricPromises);
      return results.flat();
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      // Không có biến mock nào cho campaign metrics trong mockData.ts, nên KHÔNG bịa dữ liệu:
      // ném lỗi để tầng gọi tự hiển thị trạng thái lỗi thay vì trả về danh sách rỗng giả.
      console.warn('[OFFLINE DEMO] No campaign metrics mock available; metricsApi.getAllCampaignsMetrics cannot serve local data');
      throw e;
    }
  }
};

export const scheduleApi = {
  getAllPage: async (
    page = 1,
    pageSize = 20,
    filters?: { workspace_id?: number; status?: string; content_id?: number },
    signal?: AbortSignal,
  ): Promise<Page<MarketingSchedule>> => {
    const params: Record<string, any> = {};
    if (filters?.workspace_id) params.workspace_id = filters.workspace_id;
    if (filters?.status) params.status = filters.status;
    if (filters?.content_id) params.content_id = filters.content_id;
    try {
      const res = await apiClient.get('/schedules', { params: withPaging(params, page, pageSize), signal });
      return toPage<MarketingSchedule>(res.data, page, pageSize);
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: scheduleApi.getAllPage');
      let list = getStoredList<MarketingSchedule>('mf_schedules', MOCK_SCHEDULES);
      if (filters?.status) list = list.filter(s => s.status === filters.status);
      if (filters?.content_id) list = list.filter(s => s.content_id === filters.content_id);
      const total = list.length;
      const start = (page - 1) * pageSize;
      return {
        items: list.slice(start, start + pageSize),
        total,
        page,
        page_size: pageSize,
        total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
        has_next: page * pageSize < total,
        has_prev: page > 1,
      };
    }
  },

  getAll: async (signal?: AbortSignal): Promise<MarketingSchedule[]> => {
    try {
      const res = await apiClient.get('/schedules', { signal });
      return toPage<MarketingSchedule>(res.data).items;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: scheduleApi.getAll');
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
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: scheduleApi.create');
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
      // KHÔNG trả `e.response.data` cho mọi lỗi HTTP: envelope lỗi của FastAPI là
      // `{detail: ...}`, không có field `success`, nên Settings nhận undefined cho
      // cả nhánh thành công lẫn thất bại và không hiển thị gì cả. Đây là lỗi
      // truyền dữ liệu chứ không phải kết quả kiểm tra — phải ném ra cho caller.
      if (e?.response?.status === 401 || e?.response?.status === 403) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Không thể kiểm tra kết nối AI khi backend offline.');
      throw new Error('Không thể kiểm tra kết nối AI: máy chủ backend không phản hồi. Vui lòng thử lại.');
    }
  },

  getKeys: async (workspaceId?: number): Promise<CustomApiKey> => {
    try {
      const params = workspaceId ? { workspace_id: workspaceId } : {};
      const res = await apiClient.get('/settings/ai-keys', { params });
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: settingsApi.getKeys');
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
      return toPage<CustomApiKey>(res.data).items;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: settingsApi.getKeysList');
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
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: settingsApi.saveKey');
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
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: settingsApi.deleteKey');
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
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: settingsApi.deleteKeyById');
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
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: settingsApi.toggleKey');
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

// =========================================================================
// NOTIFICATION API (M3: Database Notifications Table & Endpoints)
// =========================================================================
function formatNotificationRelativeTime(dateStr?: string): string {
  if (!dateStr) return 'Vừa xong';
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (diffSec < 60) return 'Vừa xong';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin} phút trước`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours} giờ trước`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays} ngày trước`;
    return date.toLocaleDateString('vi-VN');
  } catch {
    return 'Gần đây';
  }
}

/** Ánh xạ một dòng notification của API sang shape dùng ở UI. */
const _toAppNotification = (item: any): AppNotification => ({
  id: String(item.id),
  title: item.title,
  message: item.message,
  type: item.type || 'info',
  timestamp: formatNotificationRelativeTime(item.created_at),
  read: Boolean(item.read),
  targetTab: item.target_tab || undefined,
  actionLabel: item.target_tab === 'reviews'
    ? 'Mở hàng đợi duyệt'
    : (item.target_tab === 'campaigns'
        ? 'Xem Chiến dịch'
        : (item.target_tab === 'ai_studio' ? 'Mở AI Studio' : undefined)),
});

export const notificationApi = {
  /** Bản có phân trang; trả về luôn envelope để UI biết còn bao nhiêu thông báo. */
  getAllPage: async (
    page = 1,
    pageSize = 20,
    params?: { workspace_id?: number; unread_only?: boolean },
    signal?: AbortSignal,
  ): Promise<Page<AppNotification>> => {
    const query: Record<string, any> = {};
    if (params?.workspace_id) query.workspace_id = params.workspace_id;
    if (params?.unread_only) query.unread_only = true;
    try {
      const res = await apiClient.get('/notifications', {
        params: withPaging(query, page, pageSize),
        signal,
      });
      const envelope = toPage<any>(res.data, page, pageSize);
      return { ...envelope, items: envelope.items.map((item: any) => _toAppNotification(item)) };
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: notificationApi.getAll');
      const list = getStoredList<AppNotification>('mf_notifications', []);
      return toPage<AppNotification>(list, page, pageSize);
    }
  },

  getAll: async (signal?: AbortSignal, params?: { workspace_id?: number; unread_only?: boolean }): Promise<AppNotification[]> => {
    try {
      const res = await apiClient.get('/notifications', { params, signal });
      return toPage<any>(res.data).items.map((item: any) => _toAppNotification(item));
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: notificationApi.getAll');
      return getStoredList<AppNotification>('mf_notifications', []);
    }
  },

  markAsRead: async (notificationId: string | number): Promise<any> => {
    try {
      const res = await apiClient.patch(`/notifications/${notificationId}/read`);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: notificationApi.markAsRead');
      const list = getStoredList<AppNotification>('mf_notifications', []);
      const updated = list.map(n => n.id === String(notificationId) ? { ...n, read: true } : n);
      setStoredList('mf_notifications', updated);
      return { success: true };
    }
  },

  markAllAsRead: async (workspaceId?: number): Promise<{ success: boolean; count: number }> => {
    try {
      const params = workspaceId ? { workspace_id: workspaceId } : {};
      const res = await apiClient.post('/notifications/mark-all-read', null, { params });
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      console.warn('[OFFLINE DEMO] Operating on local mock storage: notificationApi.markAllAsRead');
      const list = getStoredList<AppNotification>('mf_notifications', []);
      const updated = list.map(n => ({ ...n, read: true }));
      setStoredList('mf_notifications', updated);
      return { success: true, count: list.length };
    }
  }
};

// --- TASK & OPERATIONS API SERVICES ---

export const taskApi = {
  getCampaignTasksPage: async (
    campaignId: number,
    page = 1,
    pageSize = 20,
    filters?: { status?: string; priority?: string; assignee_id?: number },
  ): Promise<Page<Task>> => {
    try {
      const res = await apiClient.get(`/campaigns/${campaignId}/tasks`, {
        params: withPaging(filters as Record<string, any>, page, pageSize),
      });
      return toPage<Task>(res.data, page, pageSize);
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      const tasks = getStoredList<Task>('mf_tasks', []).filter(t => t.campaign_id === campaignId);
      const total = tasks.length;
      const start = (page - 1) * pageSize;
      return {
        items: tasks.slice(start, start + pageSize),
        total,
        page,
        page_size: pageSize,
        total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
        has_next: page * pageSize < total,
        has_prev: page > 1,
      };
    }
  },

  getCampaignTasks: async (campaignId: number, filters?: { status?: string; priority?: string; assignee_id?: number }): Promise<Task[]> => {
    try {
      const res = await apiClient.get(`/campaigns/${campaignId}/tasks`, { params: filters });
      return toPage<Task>(res.data).items;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      const tasks = getStoredList<Task>('mf_tasks', []);
      return tasks.filter(t => t.campaign_id === campaignId);
    }
  },

  createTask: async (campaignId: number, data: TaskCreate): Promise<Task> => {
    try {
      const res = await apiClient.post(`/campaigns/${campaignId}/tasks`, data);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      const tasks = getStoredList<Task>('mf_tasks', []);
      const newTask: Task = {
        id: Date.now(),
        campaign_id: campaignId,
        workspace_id: 1,
        creator_id: 1,
        assignee_id: data.assignee_id,
        title: data.title,
        description: data.description,
        task_type: data.task_type || 'OTHER',
        status: data.status || 'TODO',
        priority: data.priority || 'MEDIUM',
        due_date: data.due_date,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      tasks.push(newTask);
      setStoredList('mf_tasks', tasks);
      return newTask;
    }
  },

  /** Bốn con số tổng hợp phạm vi toàn bộ, không theo trang — cho các thẻ thống kê. */
  getMyTasksSummary: async (): Promise<{ overdue: number; today: number; in_progress: number; done: number; total: number }> => {
    try {
      const res = await apiClient.get('/tasks/my-tasks/summary');
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      return { overdue: 0, today: 0, in_progress: 0, done: 0, total: 0 };
    }
  },

  getMyTasksPage: async (
    page = 1,
    pageSize = 20,
    filters?: {
      status?: string;
      priority?: string;
      include_completed?: boolean;
      campaign_id?: number;
      search?: string;
      due?: 'today' | 'overdue';
    },
  ): Promise<Page<Task>> => {
    const params: Record<string, any> = {};
    if (filters?.status) params.status = filters.status;
    if (filters?.priority) params.priority = filters.priority;
    if (filters?.include_completed !== undefined) params.include_completed = filters.include_completed;
    if (filters?.campaign_id) params.campaign_id = filters.campaign_id;
    if (filters?.search) params.search = filters.search;
    if (filters?.due) params.due = filters.due;
    try {
      const res = await apiClient.get('/tasks/my-tasks', { params: withPaging(params, page, pageSize) });
      return toPage<Task>(res.data, page, pageSize);
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      const tasks = getStoredList<Task>('mf_tasks', []);
      const total = tasks.length;
      const start = (page - 1) * pageSize;
      return {
        items: tasks.slice(start, start + pageSize),
        total,
        page,
        page_size: pageSize,
        total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
        has_next: page * pageSize < total,
        has_prev: page > 1,
      };
    }
  },

  getMyTasks: async (filters?: { status?: string; priority?: string; include_completed?: boolean }): Promise<Task[]> => {
    try {
      const res = await apiClient.get('/tasks/my-tasks', { params: filters });
      return toPage<Task>(res.data).items;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      return getStoredList<Task>('mf_tasks', []);
    }
  },

  getTask: async (taskId: number): Promise<Task> => {
    try {
      const res = await apiClient.get(`/tasks/${taskId}`);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      const tasks = getStoredList<Task>('mf_tasks', []);
      const t = tasks.find(x => x.id === taskId);
      if (!t) throw new Error('Task not found');
      return t;
    }
  },

  updateTask: async (taskId: number, data: TaskUpdate): Promise<Task> => {
    try {
      const res = await apiClient.patch(`/tasks/${taskId}`, data);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      const tasks = getStoredList<Task>('mf_tasks', []);
      const idx = tasks.findIndex(x => x.id === taskId);
      if (idx !== -1) {
        tasks[idx] = { ...tasks[idx], ...data, updated_at: new Date().toISOString() };
        setStoredList('mf_tasks', tasks);
        return tasks[idx];
      }
      throw new Error('Task not found');
    }
  },

  deleteTask: async (taskId: number): Promise<void> => {
    try {
      await apiClient.delete(`/tasks/${taskId}`);
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      const tasks = getStoredList<Task>('mf_tasks', []).filter(t => t.id !== taskId);
      setStoredList('mf_tasks', tasks);
    }
  }
};

export const budgetApi = {
  getBudgetAllocations: async (campaignId: number): Promise<BudgetAllocation[]> => {
    try {
      const res = await apiClient.get(`/campaigns/${campaignId}/budget-allocations`);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      return [];
    }
  },

  updateBudgetAllocations: async (campaignId: number, data: { channel_id: number; planned_amount: number }[]): Promise<BudgetAllocation[]> => {
    try {
      const res = await apiClient.put(`/campaigns/${campaignId}/budget-allocations`, data);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      return data.map((d, i) => ({ id: i + 1, campaign_id: campaignId, ...d }));
    }
  }
};

export const kpiApi = {
  getKPITargets: async (campaignId: number): Promise<KPITarget[]> => {
    try {
      const res = await apiClient.get(`/campaigns/${campaignId}/kpi-targets`);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      return [];
    }
  },

  updateKPITargets: async (campaignId: number, data: { metric_name: string; target_value: number; unit: string }[]): Promise<KPITarget[]> => {
    try {
      const res = await apiClient.put(`/campaigns/${campaignId}/kpi-targets`, data);
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      return data.map((d, i) => ({ id: i + 1, campaign_id: campaignId, ...d }));
    }
  }
};

export const commandCenterApi = {
  getCommandCenter: async (): Promise<CommandCenterResponse> => {
    try {
      const res = await apiClient.get('/analytics/command-center');
      return res.data;
    } catch (e: any) {
      if (e?.response) throw e;
      if (!isOfflineDemoEnabled()) throw e;
      return {
        attention_items: [],
        my_work_today: [],
        campaigns_health: [],
        summary_counts: {
          total_active_campaigns: 0,
          total_my_tasks: 0,
          total_overdue_tasks: 0,
          total_pending_approvals: 0,
          critical_issues: 0
        }
      };
    }
  }
};



