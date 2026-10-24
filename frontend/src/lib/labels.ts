import type {
  AiActionStatus,
  CampaignGoal,
  CampaignStatus,
  ChannelCode,
  ContentOrigin,
  ContentStatus,
  ContentType,
  MetricSource,
  ReviewDecision,
  Role,
  ScheduleStatus,
} from './types';

/** Tông màu cho Badge — ánh xạ sang màu ngữ nghĩa trong UI kit. */
export type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

export const ROLE_LABEL: Record<Role, string> = {
  MANAGER: 'Quản lý',
  MARKETER: 'Nhân viên marketing',
};

export const GOAL_LABEL: Record<CampaignGoal, string> = {
  AWARENESS: 'Nhận diện thương hiệu',
  TRAFFIC: 'Tăng lượt truy cập',
  LEADS: 'Thu khách hàng tiềm năng',
  SALES: 'Tăng doanh số',
};

export const CAMPAIGN_STATUS_LABEL: Record<CampaignStatus, string> = {
  PLANNED: 'Lên kế hoạch',
  ACTIVE: 'Đang chạy',
  PAUSED: 'Tạm dừng',
  COMPLETED: 'Hoàn thành',
  CANCELLED: 'Đã huỷ',
};

export const CAMPAIGN_STATUS_TONE: Record<CampaignStatus, Tone> = {
  PLANNED: 'info',
  ACTIVE: 'success',
  PAUSED: 'warning',
  COMPLETED: 'neutral',
  CANCELLED: 'danger',
};

export const CONTENT_STATUS_LABEL: Record<ContentStatus, string> = {
  DRAFT: 'Bản nháp',
  PENDING_REVIEW: 'Chờ duyệt',
  APPROVED: 'Đã duyệt',
  REJECTED: 'Bị từ chối',
  PUBLISHED: 'Đã đăng',
};

export const CONTENT_STATUS_TONE: Record<ContentStatus, Tone> = {
  DRAFT: 'neutral',
  PENDING_REVIEW: 'warning',
  APPROVED: 'info',
  REJECTED: 'danger',
  PUBLISHED: 'success',
};

export const CONTENT_TYPE_LABEL: Record<ContentType, string> = {
  SOCIAL_POST: 'Bài đăng mạng xã hội',
  EMAIL: 'Email',
  AD_COPY: 'Nội dung quảng cáo',
  VIDEO_SCRIPT: 'Kịch bản video',
  OTHER: 'Khác',
};

export const ORIGIN_LABEL: Record<ContentOrigin, string> = {
  MANUAL: 'Tự soạn',
  AI: 'Trợ lý AI',
};

export const REVIEW_DECISION_LABEL: Record<ReviewDecision, string> = {
  APPROVED: 'Đã duyệt',
  REJECTED: 'Từ chối',
};

export const SCHEDULE_STATUS_LABEL: Record<ScheduleStatus, string> = {
  PLANNED: 'Đã lên lịch',
  DONE: 'Đã đăng',
  CANCELLED: 'Đã huỷ',
};

export const SCHEDULE_STATUS_TONE: Record<ScheduleStatus, Tone> = {
  PLANNED: 'info',
  DONE: 'success',
  CANCELLED: 'neutral',
};

export const METRIC_SOURCE_LABEL: Record<MetricSource, string> = {
  MANUAL: 'Nhập tay',
  CSV: 'Nhập CSV',
  SEED: 'Dữ liệu mẫu',
};

export const METRIC_SOURCE_TONE: Record<MetricSource, Tone> = {
  MANUAL: 'neutral',
  CSV: 'info',
  SEED: 'warning',
};

export const AI_ACTION_STATUS_LABEL: Record<AiActionStatus, string> = {
  PROPOSED: 'Chờ xác nhận',
  EXECUTED: 'Đã thực hiện',
  REJECTED: 'Đã bỏ qua',
  FAILED: 'Thất bại',
};

export const AI_ACTION_STATUS_TONE: Record<AiActionStatus, Tone> = {
  PROPOSED: 'warning',
  EXECUTED: 'success',
  REJECTED: 'neutral',
  FAILED: 'danger',
};

export const CHANNEL_LABEL: Record<ChannelCode, string> = {
  FACEBOOK: 'Facebook',
  INSTAGRAM: 'Instagram',
  TIKTOK: 'TikTok',
  ZALO_OA: 'Zalo OA',
  EMAIL: 'Email',
  GOOGLE_ADS: 'Google Ads',
  WEBSITE: 'Website',
};

export function options<K extends string>(labels: Record<K, string>): { value: K; label: string }[] {
  return (Object.keys(labels) as K[]).map((value) => ({ value, label: labels[value] }));
}
