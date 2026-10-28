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

export const GOAL_TONE: Record<CampaignGoal, Tone> = {
  AWARENESS: 'info',
  TRAFFIC: 'accent',
  LEADS: 'warning',
  SALES: 'success',
};

export interface GoalKpiMeta {
  primaryMetricKey: 'views' | 'clicks' | 'conversions';
  primaryKpiLabel: string;
  secondaryKpiLabel: string;
  contentDirection: string;
  defaultCta: string;
}

/**
 * Định hướng KPI trọng tâm và góc tiếp cận nội dung bám sát từng Mục tiêu chiến dịch (CampaignGoal).
 */
export const GOAL_KPI_META: Record<CampaignGoal, GoalKpiMeta> = {
  AWARENESS: {
    primaryMetricKey: 'views',
    primaryKpiLabel: 'Lượt xem (Views) & độ phủ',
    secondaryKpiLabel: 'Chi phí mỗi 1.000 lượt hiển thị (CPM)',
    contentDirection:
      'Tập trung kể câu chuyện sản phẩm, nêu bật điểm khác biệt và hình ảnh bắt mắt để mở rộng độ nhận biết thương hiệu.',
    defaultCta: 'Khám phá câu chuyện thương hiệu',
  },
  TRAFFIC: {
    primaryMetricKey: 'clicks',
    primaryKpiLabel: 'Lượt nhấp (Clicks) & Tỷ lệ nhấp (CTR)',
    secondaryKpiLabel: 'Chi phí mỗi lượt nhấp (CPC)',
    contentDirection:
      'Mở đầu bằng câu hỏi hoặc lợi ích trực diện, dẫn dắt người đọc nhấp vào liên kết để xem chi tiết trên trang đích.',
    defaultCta: 'Xem chi tiết tại trang sản phẩm',
  },
  LEADS: {
    primaryMetricKey: 'conversions',
    primaryKpiLabel: 'Lượt đăng ký (Conversions) & Tỷ lệ chuyển đổi (CVR)',
    secondaryKpiLabel: 'Chi phí mỗi khách hàng tiềm năng (CPA)',
    contentDirection:
      'Nhấn mạnh giá trị thực tế khách hàng nhận được (vé tham dự, buổi thử mẫu, ưu đãi thành viên) để khuyến khích để lại thông tin.',
    defaultCta: 'Đăng ký giữ chỗ ngay hôm nay',
  },
  SALES: {
    primaryMetricKey: 'conversions',
    primaryKpiLabel: 'Đơn hàng chuyển đổi (Conversions) & CVR',
    secondaryKpiLabel: 'Chi phí trên mỗi đơn hàng (CPA)',
    contentDirection:
      'Nêu rõ sản phẩm chủ lực, mức ưu đãi hiện hành, cam kết chất lượng và thúc đẩy hành động đặt mua ngay.',
    defaultCta: 'Đặt mua ngay để nhận ưu đãi',
  },
};

export function buildGoalContentDraft(campaign: {
  name: string;
  goal: CampaignGoal;
  objective: string;
  product: string;
  target_audience: string;
  key_message?: string | null;
}): { title: string; body: string; cta: string } {
  const meta = GOAL_KPI_META[campaign.goal];
  const coreMsg = campaign.key_message ? `\n\nThông điệp chủ đạo: "${campaign.key_message}"` : '';
  return {
    title: `[${GOAL_LABEL[campaign.goal]}] ${campaign.product} — ${campaign.name}`,
    body: `Dành cho: ${campaign.target_audience}\nSản phẩm trọng tâm: ${campaign.product}${coreMsg}\n\nĐiểm nhấn nội dung (${GOAL_LABEL[campaign.goal]}):\n- ${meta.contentDirection}\n- Bám sát mục tiêu chiến dịch: ${campaign.objective}\n- Lợi ích nổi bật dành cho khách hàng khi trải nghiệm ${campaign.product}.`,
    cta: meta.defaultCta,
  };
}

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
