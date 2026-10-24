/**
 * Kiểu dữ liệu dùng chung, phản chiếu docs/rebuild/CONTRACT.md §3, §4, §6.
 * Quy ước: ngày `YYYY-MM-DD` (string), thời điểm ISO-8601 có timezone (string),
 * tiền là số nguyên VND (number). Tỷ lệ có mẫu số 0 trả về `null`.
 */

// ---------------------------------------------------------------- Enums

export type Role = 'MANAGER' | 'MARKETER';

export type ChannelCode =
  | 'FACEBOOK'
  | 'INSTAGRAM'
  | 'TIKTOK'
  | 'ZALO_OA'
  | 'EMAIL'
  | 'GOOGLE_ADS'
  | 'WEBSITE';

export type CampaignGoal = 'AWARENESS' | 'TRAFFIC' | 'LEADS' | 'SALES';
export type CampaignStatus = 'PLANNED' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'CANCELLED';

export type ContentType = 'SOCIAL_POST' | 'EMAIL' | 'AD_COPY' | 'VIDEO_SCRIPT' | 'OTHER';
export type ContentStatus = 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'PUBLISHED';
export type ContentOrigin = 'MANUAL' | 'AI';

export type ReviewDecision = 'APPROVED' | 'REJECTED';
export type ScheduleStatus = 'PLANNED' | 'DONE' | 'CANCELLED';
export type MetricSource = 'MANUAL' | 'CSV' | 'SEED';

export type AiMessageRole = 'USER' | 'ASSISTANT';
export type AiMessageStatus = 'STREAMING' | 'COMPLETE' | 'ERROR' | 'STOPPED';
export type AiActionStatus = 'PROPOSED' | 'EXECUTED' | 'REJECTED' | 'FAILED';
export type AiErrorCode =
  | 'AI_UNAVAILABLE'
  | 'AI_RATE_LIMITED'
  | 'AI_TIMEOUT'
  | 'AI_EMPTY_RESPONSE'
  | 'AI_INTERNAL';

// ---------------------------------------------------------------- Common

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/** Body lỗi chuẩn: `{"detail": {"code", "message", "fields"?}}` (§4). */
export interface ApiErrorBody {
  code: string;
  message: string;
  fields?: Record<string, string>;
}

export interface Timestamps {
  created_at: string;
  updated_at: string;
}

export interface UserRef {
  id: number;
  full_name: string;
}

export interface ChannelRef {
  id: number;
  code: ChannelCode;
  name: string;
}

export interface CampaignRef {
  id: number;
  name: string;
}

export type StatusCounts<S extends string> = Partial<Record<S, number>>;

// ---------------------------------------------------------------- Health & auth

export interface Health {
  status: string;
  db: string;
  ai_runner: string;
}

export interface User extends Timestamps {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  user: User;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface UserCreate {
  email: string;
  full_name: string;
  role: Role;
  password: string;
}

export interface UserUpdate {
  full_name?: string;
  role?: Role;
  is_active?: boolean;
}

// ---------------------------------------------------------------- Channels

export interface Channel extends Timestamps {
  id: number;
  code: ChannelCode;
  name: string;
  format_rules: string | null;
  is_active: boolean;
}

export interface ChannelInput {
  code?: ChannelCode;
  name?: string;
  format_rules?: string | null;
  is_active?: boolean;
}

// ---------------------------------------------------------------- Campaigns

export interface CampaignChannel extends ChannelRef {
  planned_budget: number | null;
}

export interface CampaignListItem {
  id: number;
  name: string;
  goal: CampaignGoal;
  status: CampaignStatus;
  start_date: string;
  end_date: string;
  budget: number;
  owner: UserRef;
  channels: CampaignChannel[];
  spent: number;
  content_counts: StatusCounts<ContentStatus>;
}

export interface CampaignStats {
  views: number;
  clicks: number;
  conversions: number;
  cost: number;
  ctr: number | null;
  cvr: number | null;
  cpc: number | null;
  cpa: number | null;
  budget_used_pct: number | null;
}

export interface Campaign extends CampaignListItem, Timestamps {
  objective: string;
  target_audience: string;
  product: string;
  key_message: string | null;
  stats: CampaignStats;
}

export interface CampaignChannelInput {
  channel_id: number;
  planned_budget?: number | null;
}

export interface CampaignInput {
  name: string;
  goal: CampaignGoal;
  objective: string;
  target_audience: string;
  product: string;
  key_message?: string | null;
  start_date: string;
  end_date: string;
  budget: number;
  status?: CampaignStatus;
  channels: CampaignChannelInput[];
}

export interface CampaignFilters {
  q?: string;
  status?: CampaignStatus;
  goal?: CampaignGoal;
  channel_id?: number;
  date_from?: string;
  date_to?: string;
  owner_id?: number;
  sort?: string;
  page?: number;
  page_size?: number;
}

// ---------------------------------------------------------------- Contents

export interface Content extends Timestamps {
  id: number;
  campaign_id: number;
  campaign: CampaignRef;
  channel_id: number;
  channel: ChannelRef;
  content_type: ContentType;
  title: string;
  body: string;
  cta: string | null;
  status: ContentStatus;
  origin: ContentOrigin;
  ai_message_id: number | null;
  created_by: UserRef;
  published_url: string | null;
  published_at: string | null;
  published_by: UserRef | null;
}

export interface ContentCreate {
  campaign_id: number;
  channel_id: number;
  content_type: ContentType;
  title: string;
  body: string;
  cta?: string | null;
}

export type ContentUpdate = Partial<ContentCreate>;

export interface ContentFilters {
  campaign_id?: number;
  channel_id?: number;
  status?: ContentStatus;
  origin?: ContentOrigin;
  created_by?: number;
  q?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export interface BannedMatch {
  keyword: string;
  count: number;
}

export interface CheckBannedResponse {
  matches: BannedMatch[];
}

/** `POST /contents/{id}/submit` trả nội dung đã cập nhật kèm `banned_matches`. */
export interface ContentSubmitResponse extends Content {
  banned_matches?: BannedMatch[];
}

export interface ContentReview {
  id: number;
  content_id: number;
  reviewer: UserRef;
  decision: ReviewDecision;
  comment: string | null;
  created_at: string;
}

export interface MarkPublishedInput {
  published_url?: string | null;
  published_at?: string | null;
}

// ---------------------------------------------------------------- Schedules

export interface ScheduleContentSummary {
  id: number;
  title: string;
  status: ContentStatus;
  content_type: ContentType;
  created_by?: UserRef;
}

export interface Schedule extends Timestamps {
  id: number;
  content_id: number;
  scheduled_at: string;
  assignee: UserRef | null;
  status: ScheduleStatus;
  note: string | null;
  done_at: string | null;
  content: ScheduleContentSummary;
  campaign: CampaignRef;
  channel: ChannelRef;
}

export interface ScheduleCreate {
  content_id: number;
  scheduled_at: string;
  assignee_id?: number | null;
  note?: string | null;
}

export interface ScheduleUpdate {
  scheduled_at?: string;
  assignee_id?: number | null;
  note?: string | null;
}

export interface ScheduleFilters {
  date_from?: string;
  date_to?: string;
  channel_id?: number;
  campaign_id?: number;
  assignee_id?: number;
  status?: ScheduleStatus;
}

// ---------------------------------------------------------------- Metrics

export interface Metric extends Timestamps {
  id: number;
  campaign_id: number;
  campaign?: CampaignRef;
  channel_id: number;
  channel: ChannelRef;
  metric_date: string;
  views: number;
  clicks: number;
  conversions: number;
  cost: number;
  source: MetricSource;
  entered_by: UserRef | null;
  import_batch: string | null;
}

export interface MetricInput {
  campaign_id: number;
  channel_id: number;
  metric_date: string;
  views: number;
  clicks: number;
  conversions: number;
  cost: number;
}

export type MetricUpdate = Partial<Pick<MetricInput, 'views' | 'clicks' | 'conversions' | 'cost'>>;

export interface MetricFilters {
  campaign_id?: number;
  channel_id?: number;
  date_from?: string;
  date_to?: string;
  source?: MetricSource;
  page?: number;
  page_size?: number;
}

/** Một dòng hợp lệ trong kết quả preview CSV — gửi nguyên lại ở bước commit. */
export interface MetricImportRow {
  row: number;
  metric_date: string;
  campaign_id: number;
  campaign_name?: string;
  channel_id?: number;
  channel_code: ChannelCode;
  views: number;
  clicks: number;
  conversions: number;
  cost: number;
  /** true nếu bản ghi (campaign, channel, date) đã tồn tại và sẽ bị ghi đè. */
  exists?: boolean;
}

export interface MetricImportError {
  row: number;
  message: string;
}

export interface MetricImportPreview {
  rows: MetricImportRow[];
  errors: MetricImportError[];
  summary: Record<string, number>;
}

export interface MetricImportCommitResult {
  inserted: number;
  updated: number;
  import_batch: string;
}

// ---------------------------------------------------------------- Stats

export interface StatsFilters {
  date_from?: string;
  date_to?: string;
  campaign_id?: number;
  channel_id?: number;
  status?: CampaignStatus;
}

export interface Rates {
  ctr: number | null;
  cvr: number | null;
  cpc: number | null;
  cpa: number | null;
  cpm: number | null;
}

export interface Totals {
  views: number;
  clicks: number;
  conversions: number;
  cost: number;
}

export interface StatsOverview {
  totals: Totals;
  rates: Rates;
  budget: { total_budget: number; spent: number; used_pct: number | null };
  campaigns: { by_status: StatusCounts<CampaignStatus> };
  contents: { by_status: StatusCounts<ContentStatus> };
  pending_reviews: number;
  schedules_today: number;
  has_seed_data: boolean;
}

export type Granularity = 'day' | 'week' | 'month';

export interface TimeseriesPoint extends Totals {
  period: string;
}

export interface ChannelStats extends Totals {
  channel: ChannelRef;
  ctr: number | null;
  cvr: number | null;
  cpc: number | null;
  cpa: number | null;
}

export interface CampaignBudgetStats {
  campaign: { id: number; name: string; status: CampaignStatus };
  budget: number;
  cost: number;
  used_pct: number | null;
  views: number;
  clicks: number;
  conversions: number;
  ctr: number | null;
  cpa: number | null;
}

// ---------------------------------------------------------------- Brand

export interface BannedKeyword {
  id?: number;
  keyword: string;
  note: string | null;
}

export interface BrandProfile {
  brand_name: string;
  description: string;
  tone_of_voice: string;
  target_audience: string;
  guidelines: string;
  banned_keywords: BannedKeyword[];
}

export interface BrandProfileInput {
  brand_name: string;
  description: string;
  tone_of_voice: string;
  target_audience: string;
  guidelines: string;
  banned_keywords: { keyword: string; note?: string | null }[];
}

// ---------------------------------------------------------------- Notifications

export interface Notification {
  id: number;
  type: string;
  message: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationList extends Page<Notification> {
  unread_count?: number;
}

// ---------------------------------------------------------------- Assistant (§5–§6)

export interface AssistantStatus {
  available: boolean;
  runner: { ok: boolean; version: string | null; model: string | null };
  last_error?: string | null;
  queue_length: number;
  /** Số giây còn lại trước khi thử gọi AI lại (nhà cung cấp báo hết hạn mức) */
  rate_limited_for_s?: number;
}

export interface AiThread extends Timestamps {
  id: number;
  user_id: number;
  campaign_id: number | null;
  campaign?: CampaignRef | null;
  title: string;
  pinned: boolean;
  last_message_at: string | null;
}

export interface AiThreadCreate {
  title?: string;
  campaign_id?: number | null;
}

export interface AiThreadUpdate {
  title?: string;
  campaign_id?: number | null;
  pinned?: boolean;
}

export type ToolCallStatus = 'running' | 'done' | 'error';

export interface AiToolCallPart {
  type: 'tool_call';
  id: string;
  name: string;
  args: Record<string, unknown>;
  status: ToolCallStatus;
  summary?: string | null;
}

export interface AiActionPart {
  type: 'action';
  action_id: number;
}

export type AiMessagePart = AiToolCallPart | AiActionPart;

export interface AiMessage extends Timestamps {
  id: number;
  thread_id: number;
  role: AiMessageRole;
  content: string;
  parts_json: AiMessagePart[];
  status: AiMessageStatus;
  error_code: AiErrorCode | string | null;
  model: string | null;
  latency_ms: number | null;
}

export type AiTool =
  | 'propose_content_drafts'
  | 'propose_campaign'
  | 'propose_campaign_update'
  | 'propose_schedule'
  | 'propose_metrics';

export interface AiAction extends Timestamps {
  id: number;
  thread_id: number;
  message_id: number;
  user_id: number;
  tool: AiTool | string;
  args_json: Record<string, unknown>;
  summary: string;
  status: AiActionStatus;
  result_json: Record<string, unknown> | null;
  error: string | null;
  executed_at: string | null;
}

export interface AiActionConfirm {
  args?: Record<string, unknown>;
}

export type AssistantPhase = 'queued' | 'thinking' | 'tool' | 'writing';

/** Sự kiện SSE từ `POST /assistant/threads/{id}/messages` và `/regenerate` (§6). */
export type AssistantStreamEvent =
  | {
      event: 'message_start';
      data: { user_message: AiMessage | null; assistant_message: { id: number; status: 'STREAMING' } };
    }
  | { event: 'status'; data: { phase: AssistantPhase; queue_position?: number } }
  | { event: 'text'; data: { content: string } }
  | {
      event: 'tool_call';
      data: {
        id: string;
        name: string;
        args: Record<string, unknown>;
        status: ToolCallStatus;
        summary?: string | null;
      };
    }
  | { event: 'action'; data: AiAction }
  | { event: 'message_end'; data: { message: AiMessage } }
  | { event: 'error'; data: { code: AiErrorCode | string; message: string } };

export type AssistantStreamEventType = AssistantStreamEvent['event'];
