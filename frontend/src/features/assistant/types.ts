import type {
  AiAction,
  AiErrorCode,
  AiMessage,
  AiThread,
  AssistantPhase,
  CampaignGoal,
  ChannelCode,
  ContentType,
  ToolCallStatus,
} from '@/lib/types';

/** Nhãn tiếng Việt thân thiện cho các công cụ AI (§5, §11). */
export const ASSISTANT_TOOL_LABELS: Record<string, string> = {
  list_campaigns: 'Tra cứu danh sách chiến dịch',
  get_campaign: 'Xem chi tiết chiến dịch',
  get_stats: 'Thống kê hiệu quả tiếp thị',
  list_contents: 'Tra cứu danh mục nội dung',
  get_content: 'Xem chi tiết nội dung',
  list_schedules: 'Tra cứu lịch đăng bài',
  list_channels: 'Tra cứu kênh truyền thông',
  get_brand_profile: 'Đọc hồ sơ thương hiệu & từ cấm',
  check_banned_keywords: 'Kiểm tra từ cấm thương hiệu',
  propose_content_drafts: 'Đề xuất bản nháp nội dung',
  propose_campaign: 'Đề xuất tạo chiến dịch mới',
  propose_campaign_update: 'Đề xuất cập nhật chiến dịch',
  propose_schedule: 'Đề xuất lịch đăng bài',
  propose_metrics: 'Đề xuất ghi nhận số liệu',
};

/** Lấy nhãn tiếng Việt của tool (loại bỏ tiền tố marketflow_ nếu có). */
export function getToolLabel(toolName: string): string {
  const clean = toolName.replace(/^marketflow_/, '');
  return ASSISTANT_TOOL_LABELS[clean] || `Công cụ: ${clean}`;
}

/** Thông điệp lỗi tiếng Việt theo mã lỗi AI (§6, §7). */
export const AI_ERROR_MESSAGES: Record<string, string> = {
  AI_UNAVAILABLE: 'Dịch vụ AI hiện không khả dụng. Vui lòng kiểm tra runner hoặc thử lại sau.',
  AI_RATE_LIMITED: 'Hệ thống AI đang chạm giới hạn sử dụng (Free Tier). Vui lòng đợi ít phút trước khi thử lại.',
  AI_TIMEOUT: 'Yêu cầu phản hồi quá lâu (vượt thời gian chờ). Vui lòng thử lại với câu lệnh ngắn gọn hơn.',
  AI_EMPTY_RESPONSE: 'Trợ lý AI không tạo được nội dung phản hồi. Vui lòng thử lại.',
  AI_INTERNAL: 'Đã có lỗi nội bộ phát sinh từ hệ thống AI runner.',
  THREAD_BUSY: 'Phiên hội thoại này đang có một lượt xử lý khác đang chạy. Vui lòng chờ kết thúc hoặc bấm Dừng.',
};

export function getAiErrorMessage(code?: AiErrorCode | string | null, fallback?: string): string {
  if (code && AI_ERROR_MESSAGES[code]) {
    return AI_ERROR_MESSAGES[code];
  }
  return fallback || 'Đã có lỗi xảy ra trong quá trình xử lý của Trợ lý AI.';
}

/** Trạng thái một luồng stream đang diễn ra ở client. */
export interface StreamingState {
  isStreaming: boolean;
  phase: AssistantPhase | null;
  queuePosition?: number;
  userMessageId?: number;
  assistantMessageId?: number;
  /** Nội dung tích luỹ đến hiện tại từ các sự kiện `text` */
  accumulatedText: string;
  /** Danh sách các tool calls thu thập được trong lượt stream */
  toolCalls: Array<{
    id: string;
    name: string;
    args: Record<string, unknown>;
    status: ToolCallStatus;
    summary?: string | null;
  }>;
  /** Danh sách các actions được tạo trong lượt stream này */
  proposedActions: AiAction[];
  error?: {
    code: string;
    message: string;
  } | null;
}

/** 5 mẫu prompt gợi ý nhanh theo yêu cầu đặc tả UI. */
export interface QuickPrompt {
  id: string;
  title: string;
  description: string;
  template: string;
}

export const QUICK_PROMPTS: QuickPrompt[] = [
  {
    id: 'content-ideas',
    title: 'Gợi ý ý tưởng nội dung',
    description: 'Tìm ý tưởng sáng tạo theo góc tiếp cận và thông điệp',
    template:
      'Hãy gợi ý 5 ý tưởng nội dung độc đáo cho chiến dịch [Tên chiến dịch/sản phẩm] hướng đến đối tượng [Khách hàng mục tiêu]. Kèm theo góc tiếp cận (angle) và thông điệp cốt lõi cho từng ý tưởng.',
  },
  {
    id: 'channel-captions',
    title: 'Viết caption theo kênh',
    description: 'Soạn thảo bài đăng Facebook và kịch bản video TikTok',
    template:
      'Hãy soạn 1 bài đăng Facebook và 1 kịch bản ngắn TikTok giới thiệu sản phẩm [Tên sản phẩm]. Giọng văn [Hào hứng/Chuyên nghiệp], nêu bật điểm khác biệt chính và có lời kêu gọi hành động (CTA) rõ ràng.',
  },
  {
    id: 'marketing-email',
    title: 'Viết email',
    description: 'Email thông báo sản phẩm hoặc chương trình ưu đãi',
    template:
      'Soạn một email marketing gửi khách hàng hiện tại để thông báo về [Chương trình/Sản phẩm mới]. Tiêu đề thu hút, độ dài dưới 300 từ, có ưu đãi đặc biệt và nút CTA đặt hàng.',
  },
  {
    id: 'performance-summary',
    title: 'Tóm tắt hiệu quả & gợi ý cải thiện',
    description: 'Đánh giá chỉ số CTR, CVR, chi phí và đề xuất tối ưu',
    template:
      'Dựa trên số liệu các chiến dịch gần đây, hãy tóm tắt hiệu quả hoạt động theo từng kênh (CTR, CVR, chi phí) và đưa ra 3 đề xuất cụ thể để tối ưu chi phí và tăng tỷ lệ chuyển đổi.',
  },
  {
    id: 'weekly-calendar',
    title: 'Lập kế hoạch nội dung tuần',
    description: 'Kế hoạch đăng bài 7 ngày kèm chủ đề và thời gian',
    template:
      'Lập kế hoạch đăng bài chi tiết trong 7 ngày tới cho kênh Facebook và TikTok. Với mỗi ngày, nêu rõ: chủ đề, định dạng nội dung (ảnh/video ngắn), thông điệp chính và thời điểm đăng đề xuất.',
  },
];

/** Cấu trúc tham số soạn thảo bản nháp nội dung cho propose_content_drafts. */
export interface DraftItemEditable {
  campaign_id?: number | null;
  channel_code: ChannelCode;
  content_type: ContentType;
  title: string;
  body: string;
  cta?: string;
  submit_mode: 'PENDING_REVIEW' | 'DRAFT';
}

/** Cấu trúc tham số chiến dịch cho propose_campaign. */
export interface ProposeCampaignArgs {
  name: string;
  goal: CampaignGoal;
  objective: string;
  target_audience: string;
  product: string;
  start_date: string;
  end_date: string;
  budget: number;
  channels?: Array<{
    channel_id?: number;
    channel_code?: ChannelCode;
    planned_budget?: number;
  }>;
}

/** Cấu trúc tham số cập nhật chiến dịch cho propose_campaign_update. */
export interface ProposeCampaignUpdateArgs {
  campaign_id: number;
  name?: string;
  goal?: CampaignGoal;
  objective?: string;
  target_audience?: string;
  product?: string;
  start_date?: string;
  end_date?: string;
  budget?: number;
}

/** Cấu trúc tham số lịch đăng bài cho propose_schedule. */
export interface ProposeScheduleArgs {
  content_id: number;
  scheduled_at: string;
  note?: string;
}

/** Cấu trúc tham số số liệu cho propose_metrics. */
export interface ProposeMetricRow {
  campaign_id: number;
  channel_code: ChannelCode;
  metric_date: string;
  views: number;
  clicks: number;
  conversions: number;
  cost: number;
}

export interface ProposeMetricsArgs {
  rows: ProposeMetricRow[];
}

/** Định nghĩa nhóm phân loại phiên theo mốc thời gian. */
export interface ThreadGroup {
  id: 'pinned' | 'today' | 'last7days' | 'older';
  title: string;
  threads: AiThread[];
}

export type AssistantStreamEventCallback = {
  onMessageStart?: (data: { user_message: AiMessage | null; assistant_message: { id: number; status: 'STREAMING' } }) => void;
  onStatus?: (data: { phase: AssistantPhase; queue_position?: number }) => void;
  onText?: (data: { content: string }) => void;
  onToolCall?: (data: { id: string; name: string; args: Record<string, unknown>; status: ToolCallStatus; summary?: string | null }) => void;
  onAction?: (data: AiAction) => void;
  onMessageEnd?: (data: { message: AiMessage }) => void;
  onError?: (data: { code: string; message: string }) => void;
};
