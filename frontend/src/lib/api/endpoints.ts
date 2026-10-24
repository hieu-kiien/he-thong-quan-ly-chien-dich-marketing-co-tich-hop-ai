import { del, get, patch, post, put, http } from './client';
import type {
  AiAction,
  AiActionConfirm,
  AiMessage,
  AiThread,
  AiThreadCreate,
  AiThreadUpdate,
  AssistantStatus,
  BrandProfile,
  BrandProfileInput,
  Campaign,
  CampaignBudgetStats,
  CampaignFilters,
  CampaignInput,
  CampaignListItem,
  ChangePasswordRequest,
  Channel,
  ChannelInput,
  ChannelStats,
  CheckBannedResponse,
  Content,
  ContentCreate,
  ContentFilters,
  ContentReview,
  ContentSubmitResponse,
  ContentUpdate,
  Granularity,
  Health,
  LoginRequest,
  LoginResponse,
  MarkPublishedInput,
  Metric,
  MetricFilters,
  MetricImportCommitResult,
  MetricImportPreview,
  MetricImportRow,
  MetricInput,
  MetricUpdate,
  NotificationList,
  Page,
  Schedule,
  ScheduleCreate,
  ScheduleFilters,
  ScheduleUpdate,
  StatsFilters,
  StatsOverview,
  TimeseriesPoint,
  User,
  UserCreate,
  UserUpdate,
} from '../types';

export const healthApi = {
  get: () => get<Health>('/health'),
};

export const authApi = {
  login: (body: LoginRequest) => post<LoginResponse>('/auth/login', body),
  me: () => get<User>('/auth/me'),
  logout: () => post<void>('/auth/logout'),
  changePassword: (body: ChangePasswordRequest) => post<void>('/auth/change-password', body),
};

export const usersApi = {
  list: (params?: { page?: number; page_size?: number; q?: string }) => get<Page<User>>('/users', params),
  create: (body: UserCreate) => post<User>('/users', body),
  update: (id: number, body: UserUpdate) => patch<User>(`/users/${id}`, body),
  resetPassword: (id: number, new_password: string) => post<void>(`/users/${id}/reset-password`, { new_password }),
};

export const channelsApi = {
  list: (include_inactive = false) => get<Channel[]>('/channels', { include_inactive: include_inactive || undefined }),
  create: (body: ChannelInput) => post<Channel>('/channels', body),
  update: (id: number, body: ChannelInput) => patch<Channel>(`/channels/${id}`, body),
  remove: (id: number) => del(`/channels/${id}`),
};

export const campaignsApi = {
  list: (filters: CampaignFilters) => get<Page<CampaignListItem>>('/campaigns', filters),
  get: (id: number) => get<Campaign>(`/campaigns/${id}`),
  create: (body: CampaignInput) => post<Campaign>('/campaigns', body),
  update: (id: number, body: Partial<CampaignInput>) => patch<Campaign>(`/campaigns/${id}`, body),
  remove: (id: number) => del(`/campaigns/${id}`),
};

export const contentsApi = {
  list: (filters: ContentFilters) => get<Page<Content>>('/contents', filters),
  get: (id: number) => get<Content>(`/contents/${id}`),
  create: (body: ContentCreate) => post<Content>('/contents', body),
  update: (id: number, body: ContentUpdate) => patch<Content>(`/contents/${id}`, body),
  remove: (id: number) => del(`/contents/${id}`),
  submit: (id: number) => post<ContentSubmitResponse>(`/contents/${id}/submit`),
  approve: (id: number, comment?: string) => post<Content>(`/contents/${id}/approve`, { comment: comment || null }),
  reject: (id: number, comment: string) => post<Content>(`/contents/${id}/reject`, { comment }),
  markPublished: (id: number, body: MarkPublishedInput) => post<Content>(`/contents/${id}/mark-published`, body),
  reviews: (id: number) => get<ContentReview[]>(`/contents/${id}/reviews`),
  checkBanned: (text: string) => post<CheckBannedResponse>('/contents/check-banned', { text }),
};

export const schedulesApi = {
  list: (filters: ScheduleFilters) => get<Schedule[]>('/schedules', filters),
  create: (body: ScheduleCreate) => post<Schedule>('/schedules', body),
  update: (id: number, body: ScheduleUpdate) => patch<Schedule>(`/schedules/${id}`, body),
  done: (id: number, published_url?: string | null) => post<Schedule>(`/schedules/${id}/done`, { published_url: published_url || null }),
  cancel: (id: number) => post<Schedule>(`/schedules/${id}/cancel`),
};

export const metricsApi = {
  list: (filters: MetricFilters) => get<Page<Metric>>('/metrics', filters),
  create: (body: MetricInput) => post<Metric>('/metrics', body),
  update: (id: number, body: MetricUpdate) => patch<Metric>(`/metrics/${id}`, body),
  remove: (id: number) => del(`/metrics/${id}`),
  template: async (): Promise<Blob> => {
    const res = await http.get('/metrics/import/template', { responseType: 'blob' });
    return res.data as Blob;
  },
  preview: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return post<MetricImportPreview>('/metrics/import/preview', form, { timeout: 60_000 });
  },
  commit: (rows: MetricImportRow[]) => post<MetricImportCommitResult>('/metrics/import/commit', { rows }, { timeout: 60_000 }),
};

export const statsApi = {
  overview: (f: StatsFilters) => get<StatsOverview>('/stats/overview', f),
  timeseries: (f: StatsFilters & { granularity: Granularity }) => get<TimeseriesPoint[]>('/stats/timeseries', f),
  byChannel: (f: StatsFilters) => get<ChannelStats[]>('/stats/by-channel', f),
  byCampaign: (f: StatsFilters) => get<CampaignBudgetStats[]>('/stats/by-campaign', f),
};

export const brandApi = {
  get: () => get<BrandProfile>('/brand-profile'),
  update: (body: BrandProfileInput) => put<BrandProfile>('/brand-profile', body),
};

export const notificationsApi = {
  list: (params?: { unread_only?: boolean; page?: number; page_size?: number }) =>
    get<NotificationList>('/notifications', params),
  read: (id: number) => post<void>(`/notifications/${id}/read`),
  readAll: () => post<void>('/notifications/read-all'),
};

/**
 * REST của trợ lý (§4). Luồng SSE (`POST .../messages`, `/regenerate`) dùng fetch —
 * xem `assistantStreamUrl` và `authHeaders()` trong client.ts.
 */
export const assistantApi = {
  status: () => get<AssistantStatus>('/assistant/status'),
  listThreads: (q?: string) => get<AiThread[]>('/assistant/threads', { q }),
  createThread: (body: AiThreadCreate) => post<AiThread>('/assistant/threads', body),
  getThread: (id: number) => get<AiThread>(`/assistant/threads/${id}`),
  updateThread: (id: number, body: AiThreadUpdate) => patch<AiThread>(`/assistant/threads/${id}`, body),
  deleteThread: (id: number) => del(`/assistant/threads/${id}`),
  messages: (threadId: number) => get<AiMessage[]>(`/assistant/threads/${threadId}/messages`),
  stop: (threadId: number) => post<void>(`/assistant/threads/${threadId}/stop`),
  listActions: (params: { thread_id?: number; status?: AiAction['status'] }) => get<AiAction[]>('/assistant/actions', params),
  confirmAction: (id: number, body: AiActionConfirm = {}) => post<AiAction>(`/assistant/actions/${id}/confirm`, body),
  rejectAction: (id: number) => post<AiAction>(`/assistant/actions/${id}/reject`),
};

export const assistantStreamUrl = {
  sendMessage: (threadId: number) => `/assistant/threads/${threadId}/messages`,
  regenerate: (messageId: number) => `/assistant/messages/${messageId}/regenerate`,
};

