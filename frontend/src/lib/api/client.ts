import axios, { AxiosError, type AxiosRequestConfig } from 'axios';
import type { ApiErrorBody } from '../types';

/** Gốc API, mặc định cùng origin `/api/v1` (Vite proxy khi dev, Nginx khi production). */
export const API_BASE = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '');

const TOKEN_KEY = 'mf-token';

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* bỏ qua */
  }
}

/** Header Authorization cho các lời gọi không qua axios (vd fetch SSE của trợ lý). */
export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Lỗi API đã chuẩn hoá theo CONTRACT §4. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = 'ApiError';
    this.status = status;
    this.code = body.code;
    this.fields = body.fields ?? {};
  }
}

const GENERIC_MESSAGES: Record<number, string> = {
  400: 'Yêu cầu không hợp lệ.',
  401: 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
  403: 'Bạn không có quyền thực hiện thao tác này.',
  404: 'Không tìm thấy dữ liệu.',
  409: 'Thao tác xung đột với trạng thái hiện tại.',
  413: 'Tệp quá lớn.',
  422: 'Dữ liệu không hợp lệ.',
  429: 'Bạn thao tác quá nhanh. Vui lòng thử lại sau.',
  500: 'Máy chủ gặp lỗi. Vui lòng thử lại sau.',
  502: 'Máy chủ tạm thời không phản hồi.',
  503: 'Dịch vụ tạm thời không khả dụng.',
};

/** Chuyển body lỗi bất kỳ thành ApiErrorBody. */
export function normalizeErrorBody(status: number, data: unknown): ApiErrorBody {
  const detail = (data as { detail?: unknown } | null)?.detail;
  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const d = detail as Partial<ApiErrorBody>;
    if (typeof d.message === 'string') {
      return { code: d.code ?? `HTTP_${status}`, message: d.message, fields: d.fields };
    }
  }
  if (typeof detail === 'string') return { code: `HTTP_${status}`, message: detail };
  return { code: `HTTP_${status}`, message: GENERIC_MESSAGES[status] ?? `Lỗi không xác định (HTTP ${status}).` };
}

/** Đọc lỗi từ một `Response` của fetch (dùng cho SSE). */
export async function errorFromResponse(res: Response): Promise<ApiError> {
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    /* body không phải JSON */
  }
  if (res.status === 401) handleUnauthorized();
  return new ApiError(res.status, normalizeErrorBody(res.status, data));
}

export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  if (axios.isAxiosError(err)) {
    const ax = err as AxiosError;
    if (ax.response) return new ApiError(ax.response.status, normalizeErrorBody(ax.response.status, ax.response.data));
    if (ax.code === 'ECONNABORTED') return new ApiError(0, { code: 'TIMEOUT', message: 'Máy chủ phản hồi quá lâu.' });
    return new ApiError(0, { code: 'NETWORK_ERROR', message: 'Không kết nối được máy chủ. Kiểm tra mạng và thử lại.' });
  }
  return new ApiError(0, { code: 'UNKNOWN', message: err instanceof Error ? err.message : 'Đã có lỗi xảy ra.' });
}

/** Thông báo tiếng Việt từ lỗi bất kỳ. */
export function errorMessage(err: unknown): string {
  return toApiError(err).message;
}

// ---------------------------------------------------------------- 401 handling

type UnauthorizedListener = () => void;
const unauthorizedListeners = new Set<UnauthorizedListener>();

export function onUnauthorized(fn: UnauthorizedListener): () => void {
  unauthorizedListeners.add(fn);
  return () => unauthorizedListeners.delete(fn);
}

function handleUnauthorized(): void {
  if (!getToken()) return;
  setToken(null);
  unauthorizedListeners.forEach((fn) => fn());
}

// ---------------------------------------------------------------- axios instance

export const http = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { Accept: 'application/json' },
});

http.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.set('Authorization', `Bearer ${token}`);
  return config;
});

http.interceptors.response.use(
  (res) => res,
  (err: unknown) => {
    if (axios.isAxiosError(err) && err.response?.status === 401) {
      const url = err.config?.url ?? '';
      if (!url.includes('/auth/login')) handleUnauthorized();
    }
    return Promise.reject(toApiError(err));
  },
);

/** Bỏ các tham số rỗng để URL gọn và đúng ngữ nghĩa lọc. */
export function cleanParams(params?: object): Record<string, unknown> | undefined {
  if (!params) return undefined;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue;
    out[k] = v;
  }
  return out;
}

export async function get<T>(url: string, params?: object, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.get<T>(url, { ...config, params: cleanParams(params) });
  return res.data;
}

export async function post<T>(url: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.post<T>(url, body, config);
  return res.data;
}

export async function patch<T>(url: string, body?: unknown): Promise<T> {
  const res = await http.patch<T>(url, body);
  return res.data;
}

export async function put<T>(url: string, body?: unknown): Promise<T> {
  const res = await http.put<T>(url, body);
  return res.data;
}

export async function del<T = void>(url: string): Promise<T> {
  const res = await http.delete<T>(url);
  return res.data;
}
