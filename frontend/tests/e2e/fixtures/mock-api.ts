import { Page, Route } from '@playwright/test';

export interface MockUser {
  id: number;
  email: string;
  full_name: string;
  role: 'MARKETER' | 'MANAGER' | 'CLIENT_APPROVER' | 'AGENCY_MANAGER';
  status: string;
  created_at: string;
}

export const USERS: Record<string, MockUser> = {
  marketer: {
    id: 2,
    email: 'marketer@gmail.com',
    full_name: 'Chuyên Viên Tiếp Thị',
    role: 'MARKETER',
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
  },
  manager: {
    id: 1,
    email: 'manager@gmail.com',
    full_name: 'Quản Lý Chiến Dịch',
    role: 'MANAGER',
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
  },
  approver: {
    id: 3,
    email: 'approver@gmail.com',
    full_name: 'Đại Diện Khách Hàng (Approver)',
    role: 'CLIENT_APPROVER',
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
  },
  agency_mgr: {
    id: 4,
    email: 'agency_mgr@gmail.com',
    full_name: 'Giám Đốc Agency (Agency Mgr)',
    role: 'AGENCY_MANAGER',
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
  },
};

export const INITIAL_WORKSPACES = [
  {
    id: 1,
    name: 'Default Agency Workspace',
    slug: 'default-agency',
    description: 'Không gian làm việc điều phối chiến dịch tiếp thị tổng lực đa kênh',
    owner_id: 1,
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    name: 'VinFast Auto - Brand Campaign',
    slug: 'vinfast-auto',
    description: 'Không gian cách ly chuyên biệt cho thương hiệu VinFast',
    owner_id: 1,
    status: 'ACTIVE',
    created_at: '2026-01-15T00:00:00Z',
  },
];

export const INITIAL_BRAND_KITS: Record<number, any> = {
  1: {
    id: 1,
    workspace_id: 1,
    brand_name: 'MarketFlow AI',
    usp: 'Nền tảng Quản trị & Sáng tạo Tiếp thị Đa kênh Thông minh Chuẩn Doanh nghiệp',
    tone_of_voice: 'Chuyên nghiệp, Đáng tin cậy, Tràn đầy năng lượng chuyển đổi',
    banned_keywords: ['cam kết 100%', 'chữa dứt điểm', 'làm giàu nhanh', 'đa cấp', 'hoàn tiền không lý do'],
  },
  2: {
    id: 2,
    workspace_id: 2,
    brand_name: 'VinFast Auto',
    usp: 'Mãnh liệt tinh thần Việt Nam - Xe điện thông minh toàn cầu',
    tone_of_voice: 'Tiên phong, Đẳng cấp, Tự hào dân tộc',
    banned_keywords: ['xả kho giá rẻ', 'giảm sốc sập sàn', 'hàng chợ', 'kém chất lượng'],
  },
};

export const INITIAL_CAMPAIGNS = [
  {
    id: 1,
    workspace_id: 1,
    product_id: 1,
    owner_id: 2,
    name: 'Chiến dịch Tuyển sinh AI 2026',
    objective: 'Thu hút 500 hồ sơ ứng tuyển chất lượng cao cho chuyên ngành AI',
    audience: 'Học sinh THPT, sinh viên CNTT đam mê trí tuệ nhân tạo',
    start_date: '2026-06-01',
    end_date: '2026-09-30',
    budget: 50000000,
    status: 'ACTIVE',
    created_at: '2026-05-15T08:00:00Z',
    updated_at: '2026-05-15T08:00:00Z',
    product: {
      id: 1,
      name: 'Chương trình Đào tạo Kỹ sư AI',
      description: 'Chương trình đào tạo chuyên sâu thực chiến',
      usp: 'Học thực hành trên dàn GPU xịn, cam kết kết nối việc làm',
    },
  },
  {
    id: 2,
    workspace_id: 1,
    product_id: 2,
    owner_id: 2,
    name: 'Quảng bá Nền tảng SaaS MarketFlow',
    objective: 'Gia tăng 200 lượt dùng thử bản Enterprise',
    audience: 'Trưởng phòng Marketing, Giám đốc Agency truyền thông',
    start_date: '2026-07-01',
    end_date: '2026-10-31',
    budget: 80000000,
    status: 'PLANNED',
    created_at: '2026-06-20T09:30:00Z',
    updated_at: '2026-06-20T09:30:00Z',
    product: {
      id: 2,
      name: 'MarketFlow AI SaaS Suite',
      description: 'Bộ công cụ tự động hóa sáng tạo nội dung đa kênh',
      usp: 'Tiết kiệm 80% thời gian tạo nội dung, ROI đo lường chuẩn xác',
    },
  },
  {
    id: 3,
    workspace_id: 2,
    product_id: 3,
    owner_id: 1,
    name: 'VinFast VF7 Launching Event',
    objective: 'Định vị xe điện thông minh phân khúc C',
    audience: 'Khách hàng trẻ trung thành thị, yêu công nghệ xanh',
    start_date: '2026-08-01',
    end_date: '2026-12-31',
    budget: 200000000,
    status: 'ACTIVE',
    created_at: '2026-07-10T10:00:00Z',
    updated_at: '2026-07-10T10:00:00Z',
    product: {
      id: 3,
      name: 'VinFast VF7',
      description: 'SUV điện thông minh đỉnh cao thiết kế',
      usp: 'Thiết kế cá tính, công nghệ hỗ trợ lái ADAS cấp 2 tiên tiến',
    },
  },
];

export const INITIAL_CONTENTS = [
  {
    id: 1,
    campaign_id: 1,
    channel_id: 1,
    title: 'Đột phá sự nghiệp cùng Kỹ sư AI 2026 tại ICTU!',
    body: 'Trí tuệ nhân tạo đang định hình lại toàn bộ nền kinh tế số. Bạn đã sẵn sàng để trở thành người dẫn dắt làn sóng công nghệ tiếp theo? Đăng ký ngay hôm nay để nhận học bổng 50%!',
    cta: 'Đăng ký xét tuyển ngay hôm nay',
    image_url: 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&auto=format&fit=crop&q=80',
    status: 'IN_REVIEW',
    created_at: '2026-08-01T10:00:00Z',
    updated_at: '2026-08-01T10:00:00Z',
    channel: { id: 1, name: 'Facebook' },
  },
  {
    id: 2,
    campaign_id: 1,
    channel_id: 2,
    title: 'Kịch bản TikTok: Sinh viên AI làm gì một ngày trên phòng Lab GPU?',
    body: 'HOOK: 3 giây đầu cảnh sinh viên gõ code và mô hình AI sinh video cực mượt.\n\nVisual: Toàn cảnh phòng thực hành GPU chuẩn quốc tế.\nVoiceover: Khám phá bí mật đằng sau ngành học hot nhất thế kỷ 21 tại ICTU!',
    cta: 'Follow để xem phần tiếp theo',
    image_url: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&auto=format&fit=crop&q=80',
    status: 'DRAFT',
    created_at: '2026-08-02T11:00:00Z',
    updated_at: '2026-08-02T11:00:00Z',
    channel: { id: 2, name: 'TikTok' },
  },
  {
    id: 3,
    campaign_id: 1,
    channel_id: 3,
    title: '[Thư mời] Hội thảo Định hướng Chuyên gia AI & Cơ hội Việc làm Toàn cầu',
    body: 'Kính gửi Quý phụ huynh và các bạn sinh viên, sự kiện hội thảo trực tuyến độc quyền sẽ diễn ra vào Thứ Bảy tuần này.',
    cta: 'Xác nhận tham dự miễn phí',
    image_url: 'https://images.unsplash.com/photo-1531482615713-2afd69097998?w=1200&auto=format&fit=crop&q=80',
    status: 'APPROVED',
    created_at: '2026-08-03T14:00:00Z',
    updated_at: '2026-08-03T16:00:00Z',
    channel: { id: 3, name: 'Email' },
  },
  {
    id: 4,
    campaign_id: 3,
    channel_id: 1,
    title: 'VinFast VF7 - Thiết Kế Vị Lai, Trải Nghiệm Thượng Lưu',
    body: 'Kiến tạo phong cách lái xe điện đẳng cấp cùng VinFast VF7.',
    cta: 'Đặt cọc trải nghiệm tiên phong',
    image_url: 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=1200&auto=format&fit=crop&q=80',
    status: 'IN_REVIEW',
    created_at: '2026-08-04T09:00:00Z',
    updated_at: '2026-08-04T09:00:00Z',
    channel: { id: 1, name: 'Facebook' },
  }
];

export const INITIAL_KPIS = {
  total_views: 452000,
  total_clicks: 28400,
  total_conversions: 1850,
  total_cost: 32000000,
  total_revenue: 96000000,
  overall_ctr: 6.28,
  overall_cpc: 1126,
  overall_cvr: 6.51,
  overall_roas: 3.0,
  overall_roi: 200.0,
  channel_metrics: [
    {
      channel_id: 1,
      channel_name: 'Facebook Ads',
      views: 280000,
      clicks: 18200,
      conversions: 1200,
      cost: 20000000,
      revenue: 62000000,
      ctr: 6.5,
      cpc: 1098,
      cvr: 6.59,
      roas: 3.1,
      roi: 210.0,
    },
    {
      channel_id: 2,
      channel_name: 'TikTok Video',
      views: 140000,
      clicks: 8100,
      conversions: 520,
      cost: 8000000,
      revenue: 24000000,
      ctr: 5.78,
      cpc: 987,
      cvr: 6.42,
      roas: 3.0,
      roi: 200.0,
    },
    {
      channel_id: 3,
      channel_name: 'Email Sequence',
      views: 32000,
      clicks: 2100,
      conversions: 130,
      cost: 4000000,
      revenue: 10000000,
      ctr: 6.56,
      cpc: 1904,
      cvr: 6.19,
      roas: 2.5,
      roi: 150.0,
    },
  ],
};

export const INITIAL_AI_DOCTOR_REPORT = {
  campaign_id: 1,
  campaign_name: 'Chiến dịch Tuyển sinh AI 2026',
  health_score: 84,
  health_status: 'HEALTHY',
  model_used: 'Gemini 2.5 Flash',
  is_fallback: false,
  diagnosis: 'Chiến dịch đang vận hành hiệu quả vượt mức kỳ vọng. Chỉ số ROAS đạt 3.0x và tỷ lệ chuyển đổi CVR đạt 6.51% (vượt tiêu chuẩn ngành 4.2%). Facebook Ads là kênh chuyển đổi mạnh mẽ nhất.',
  strengths: [
    'Chi phí trên mỗi click (CPC 1,126đ) thấp hơn 24% so với trung bình phân khúc giáo dục công nghệ',
    'Tỷ lệ nhấp chuột (CTR 6.28%) rất cao nhờ thông điệp đánh trúng mối quan tâm thực hành GPU',
    'Kênh Facebook mang về 64.5% tổng doanh thu với ROAS 3.1x',
  ],
  weaknesses: [
    'Kênh Email Sequence có CPC cao (1,904đ), cần kiểm tra lại tiêu đề A/B testing',
  ],
  recommendations: [
    {
      action: 'SCALE',
      channel: 'Facebook Ads',
      reason: 'Kênh Facebook Ads đang mang lại ROAS 3.1x, tăng 25% ngân sách sẽ mang lại thêm ~300 chuyển đổi.',
      suggested_budget_delta: 5000000,
    },
    {
      action: 'OPTIMIZE',
      channel: 'Email Sequence',
      reason: 'Tiêu đề email chưa kích hoạt đủ tò mò, mở AI Studio để sinh thêm biến thể Subject Line B.',
      suggested_budget_delta: 0,
    },
  ],
};

/**
 * Tác vụ mẫu cho mock `/tasks/my-tasks` và `/campaigns/{id}/tasks`.
 *
 * Cần đủ nhiều bản ghi để test phân trang có dữ liệu để cắt — một tác vụ thì
 * `total_pages` luôn bằng 1 và mọi nút trang đều bị vô hiệu hóa, tức test phân
 * trang trở nên vô nghĩa.
 */
export const INITIAL_TASKS = [
  { id: 1, campaign_id: 1, workspace_id: 1, title: 'Thiết kế banner 1200x628', description: 'Kích thước chuẩn Meta Ads', task_type: 'DESIGN', status: 'TODO', priority: 'HIGH', due_date: '2026-09-20', assignee_id: 2, creator_id: 2, created_at: '2026-08-01T10:00:00Z', updated_at: '2026-08-01T10:00:00Z' },
  { id: 2, campaign_id: 1, workspace_id: 1, title: 'Viết kịch bản video TikTok 30s', description: 'Hook 3 giây đầu', task_type: 'VIDEO', status: 'IN_PROGRESS', priority: 'MEDIUM', due_date: '2026-09-25', assignee_id: 2, creator_id: 2, created_at: '2026-08-02T10:00:00Z', updated_at: '2026-08-02T10:00:00Z' },
  { id: 3, campaign_id: 1, workspace_id: 1, title: 'Nghiên cứu đối thủ', description: 'Bảng so sánh giá', task_type: 'RESEARCH', status: 'IN_REVIEW', priority: 'LOW', due_date: '2026-09-28', assignee_id: 2, creator_id: 2, created_at: '2026-08-03T10:00:00Z', updated_at: '2026-08-03T10:00:00Z' },
  { id: 4, campaign_id: 1, workspace_id: 1, title: 'Duyệt bài trước khi đăng', description: 'Kiểm tra tuân thủ', task_type: 'CONTENT', status: 'DONE', priority: 'MEDIUM', due_date: '2026-09-10', assignee_id: 2, creator_id: 2, created_at: '2026-08-04T10:00:00Z', updated_at: '2026-08-04T10:00:00Z' },
  { id: 5, campaign_id: 2, workspace_id: 1, title: 'Chụp ảnh sản phẩm', description: 'Studio đơn giản', task_type: 'CONTENT', status: 'TODO', priority: 'URGENT', due_date: '2026-09-15', assignee_id: 2, creator_id: 2, created_at: '2026-08-05T10:00:00Z', updated_at: '2026-08-05T10:00:00Z' },
  { id: 6, campaign_id: 2, workspace_id: 1, title: 'Chạy thử chiến dịch nhỏ', description: 'Ngân sách 500k', task_type: 'ADS', status: 'TODO', priority: 'LOW', due_date: '2026-09-30', assignee_id: 2, creator_id: 2, created_at: '2026-08-06T10:00:00Z', updated_at: '2026-08-06T10:00:00Z' },
];

export const INITIAL_BYOK_KEYS = [
  {
    id: 1,
    provider: 'gemini',
    key_preview: 'AIzaSy...7x9Q',
    model: 'gemini-2.5-flash',
    scope: 'workspace',
    workspace_id: 1,
    is_active: true,
    created_at: '2026-08-10T12:00:00Z',
    updated_at: '2026-08-10T12:00:00Z',
  }
];

/**
 * Kết quả AI dùng chung cho cả hai đường: hàng đợi bất đồng bộ (`POST /ai/jobs`
 * → poll) và endpoint đồng bộ cũ (`POST /ai/ideas` v.v, vẫn được giữ vì backend
 * đánh dấu deprecated nhưng chưa bỏ).
 *
 * Tách ra khỏi handler để hai đường không trôi lệch nội dung với nhau: trước đây
 * payload nằm inline trong từng handler, nên chỉ cần sửa một bên là test chạy được
 * nhưng hành vi thật thì lệch.
 */
export const MOCK_AI_IDEAS = {
  task_type: 'IDEA',
  ideas: [
    {
      id: 1,
      angle: 'Hiệu Năng & Thực Chiến',
      target_emotion: 'Khao khát bứt phá',
      headline: 'Chinh phục kỷ nguyên AI cùng thực hành GPU đỉnh cao',
      concept: 'Nhấn mạnh năng lực thực chiến với cơ sở hạ tầng hiện đại',
      key_benefit: 'Cam kết việc làm và cơ hội nhận học bổng 50%',
    },
    {
      id: 2,
      angle: 'Chuyên Gia Đầu Ngành',
      target_emotion: 'Tin cậy vững chắn',
      headline: 'Học AI từ chuyên gia doanh nghiệp hàng đầu',
      concept: 'Lộ trình đào tạo chuẩn quốc tế gắn liền dự án thật',
      key_benefit: 'Tự tay huấn luyện mô hình LLM từ con số 0',
    },
    {
      id: 3,
      angle: 'Học Bổng Tài Năng',
      target_emotion: 'Hào hứng khám phá',
      headline: 'Học bổng Tài Năng Công nghệ Trí tuệ Nhân tạo 2026',
      concept: 'Đãi ngộ đặc biệt cho tài năng trẻ khao khát đổi mới sáng tạo',
      key_benefit: 'Miễn 100% học phí và tài trợ kinh phí nghiên cứu Lab',
    },
  ],
  warnings: [],
  assumptions: [],
  prompt_version: 'v3',
  is_fallback: false,
  model_used: 'mock-model-v3',
  model_provider: 'mock-ai-provider',
};

export const MOCK_AI_DRAFT = {
  task_type: 'DRAFT',
  title: 'Khởi đầu sự nghiệp Kỹ sư AI cùng chương trình thực hành chuẩn quốc tế 2026',
  body: 'Làn sóng trí tuệ nhân tạo đang mở ra hàng ngàn cơ hội đột phá. Tham gia ngay chương trình đào tạo để cam kết 100% việc làm và trải nghiệm môi trường học tập đẳng cấp, tự tay xây dựng các mô hình Machine Learning thực tế.\n\nThời gian nhận hồ sơ xét tuyển có hạn, hãy nhanh tay nắm bắt tấm vé vàng!',
  cta: 'Đăng ký nhận tư vấn lộ trình và học bổng ngay',
  warnings: [],
  assumptions: [],
  prompt_version: 'v3',
  is_fallback: false,
  model_used: 'mock-model-v3',
  model_provider: 'mock-ai-provider',
};

export const MOCK_AI_OMNICHANNEL = {
  task_type: 'OMNICHANNEL',
  model_used: 'mock-model-v3',
  model_provider: 'mock-ai-provider',
  warnings: [],
  compliance_score: 100,
  is_fallback: false,
  facebook: {
    title: 'Bứt Phá Thu Nhập Cùng Nghề Kỹ Sư AI Thực Chiến',
    headline: 'Bứt Phá Thu Nhập Cùng Nghề Kỹ Sư AI Thực Chiến',
    body: 'Thực hành trực tiếp trên hạ tầng máy chủ GPU công suất lớn. Đăng ký nhận thông tin xét tuyển đợt 1 ngay!',
    primary_text: 'Thực hành trực tiếp trên hạ tầng máy chủ GPU công suất lớn. Đăng ký nhận thông tin xét tuyển đợt 1 ngay!',
    cta: 'Đăng ký ngay',
    hashtags: ['#AI2026', '#KySuAI', '#ICTU', '#CongNgheSo'],
    visual_suggestion: 'Ảnh phòng Lab hiện đại với sinh viên thao tác trên máy trạm.',
  },
  tiktok: {
    hook_3s: 'Bạn có biết sinh viên ngành AI làm gì một ngày trên phòng Lab?',
    scenes: [
      {
        scene: 1,
        scene_number: 1,
        title: 'Mở màn ấn tượng',
        visual_action: 'Cận cảnh màn hình terminal đang chạy mô hình Deep Learning',
        voiceover: 'Một ngày tại phòng Lab AI thực chiến có gì đặc biệt?',
        duration_seconds: 4,
        audio: 'Upbeat tech soundtrack',
      },
      {
        scene: 2,
        scene_number: 2,
        title: 'Thực hành GPU',
        visual_action: 'Sinh viên thảo luận cùng giảng viên bên cụm máy chủ',
        voiceover: 'Được tự tay huấn luyện các mô hình AI tiến bộ nhất hiện nay.',
        duration_seconds: 5,
        audio: 'Lofi study beat',
      }
    ],
    sound_recommendation: 'Trending tech synthwave music',
  },
  email: {
    subject_line_a: '[Thư mời] Trải nghiệm một ngày làm Kỹ sư AI tại ICTU',
    subject_line_b: 'Khám phá bí quyết chinh phục ngành công nghệ hot nhất 2026',
    preheader: 'Cơ hội nhận học bổng 50% dành cho ứng viên đăng ký sớm',
    body_content: 'Chào bạn,\n\nNgành trí tuệ nhân tạo đang khát nhân lực hơn bao giờ hết. Chúng tôi trân trọng mời bạn tham dự ngày hội trải nghiệm công nghệ.',
    cta_button: 'Xác nhận tham gia',
    ps_note: 'Số lượng vé tham dự có hạn cho đợi này.',
  },
};

export interface SetupMockOptions {
  userRole?: 'MARKETER' | 'MANAGER' | 'CLIENT_APPROVER' | 'AGENCY_MANAGER';
  customContents?: any[];
  customCampaigns?: any[];
  customKpis?: any;
  customDoctor?: any;
  customByokKeys?: any[];
}

export async function setupMockApiRoutes(page: Page, options: SetupMockOptions = {}) {
  const currentRole = options.userRole || 'MARKETER';
  const currentUser = Object.values(USERS).find(u => u.role === currentRole) || USERS.marketer;

  let contents = options.customContents ? structuredClone(options.customContents) : structuredClone(INITIAL_CONTENTS);
  let campaigns = options.customCampaigns ? structuredClone(options.customCampaigns) : structuredClone(INITIAL_CAMPAIGNS);
  let byokKeys = options.customByokKeys ? structuredClone(options.customByokKeys) : structuredClone(INITIAL_BYOK_KEYS);

  /**
   * Cắt trang một danh sách và bọc thành envelope `Page` — ĐÚNG hợp đồng của
   * backend (`app/core/pagination.py`).
   *
   * Vì sao mock cũng phải phân trang: nếu mock trả mảng phẳng trong khi backend
   * trả envelope, thì mọi test chạy với mock sẽ KHÔNG phát hiện được lỗi chỉ tồn
   * tại trên backend (thiếu `total`, cắt trang sai, lọc sau khi đã cắt). Mock
   * phải giống backend thì test mới đáng tin.
   *
   * `total` là số bản ghi SAU KHI LỌC — đó là điểm dễ sai nhất của phân trang.
   */
  const paginate = <T,>(list: T[], url: URL): any => {
    const page = Math.max(1, Number(url.searchParams.get('page') || 1));
    const rawSize = Number(url.searchParams.get('page_size') || 20);
    // Trần cứng khớp PAGE_SIZE_MAX; backend trả 422 nếu vượt.
    const pageSize = Math.min(Math.max(1, rawSize), 100);
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
  };

  /** Lọc theo `status` (có thể nhiều giá trị, cách nhau bởi dấu phẩy) + `search`. */
  const applyFilters = <T extends Record<string, any>>(list: T[], url: URL, searchFields: string[]): T[] => {
    const status = url.searchParams.get('status');
    if (status && status !== 'ALL') {
      const wanted = status.split(',').map(s => s.trim().toUpperCase()).filter(s => s && s !== 'ALL');
      if (wanted.length) list = list.filter(row => wanted.includes(String(row.status).toUpperCase()));
    }
    const search = url.searchParams.get('search');
    if (search) {
      const needle = search.toLowerCase();
      list = list.filter(row => searchFields.some(f => String(row[f] ?? '').toLowerCase().includes(needle)));
    }
    return list;
  };

  /** Sắp xếp theo khoá allowlist — sai thì bỏ qua thay vì ném. */
  const applySort = <T extends Record<string, any>>(list: T[], url: URL): T[] => {
    const sort = url.searchParams.get('sort') || 'newest';
    const collator = new Intl.Collator('vi');
    const copy = [...list];
    switch (sort) {
      case 'name_asc': return copy.sort((a, b) => collator.compare(String(a.name ?? ''), String(b.name ?? '')) || a.id - b.id);
      case 'name_desc': return copy.sort((a, b) => collator.compare(String(b.name ?? ''), String(a.name ?? '')) || a.id - b.id);
      case 'budget_asc': return copy.sort((a, b) => (Number(a.budget) || 0) - (Number(b.budget) || 0) || a.id - b.id);
      case 'budget_desc': return copy.sort((a, b) => (Number(b.budget) || 0) - (Number(a.budget) || 0) || a.id - b.id);
      case 'status_asc': return copy.sort((a, b) => collator.compare(String(a.status ?? ''), String(b.status ?? '')) || b.id - a.id);
      case 'oldest': return copy.sort((a, b) => a.id - b.id);
      default: return copy.sort((a, b) => b.id - a.id);
    }
  };

  await page.route('**/api/v1/**', async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    // 1. Auth Endpoints
    if (path.endsWith('/auth/login') && method === 'POST') {
      const body = request.postDataJSON() || {};
      const foundUser = Object.values(USERS).find(u => u.email.toLowerCase() === (body.email || '').toLowerCase());
      if (foundUser) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            access_token: `token-${foundUser.role.toLowerCase()}-${foundUser.id}`,
            user: foundUser,
          }),
        });
      }
      return route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Email hoặc mật khẩu không chính xác' }),
      });
    }

    if (path.endsWith('/auth/me') && method === 'GET') {
      const authHeader = request.headers()['authorization'] || '';
      let userToReturn = currentUser;
      if (authHeader.includes('agency_mgr') || authHeader.includes('agency')) userToReturn = USERS.agency_mgr;
      else if (authHeader.includes('manager')) userToReturn = USERS.manager;
      else if (authHeader.includes('marketer')) userToReturn = USERS.marketer;
      else if (authHeader.includes('approver')) userToReturn = USERS.approver;

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(userToReturn),
      });
    }

    // 2. Workspaces
    if (path.endsWith('/workspaces') && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(paginate(INITIAL_WORKSPACES, url)),
      });
    }

    // 2b. Hạn mức gói miễn phí — cùng hình dạng với GET /workspaces/{id}/quota.
    if (/\/workspaces\/\d+\/quota$/.test(path) && method === 'GET') {
      const wsId = Number(path.match(/\/workspaces\/(\d+)\/quota/)![1]);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          workspace_id: wsId,
          exempt: false,
          limits: [
            { limit_code: 'ai_jobs_per_day', label: 'AI job mỗi 24 giờ', used: 3, limit: 50, remaining: 47, exceeded: false, scope: 'workspace', window: '24h', resets_at: new Date(Date.now() + 3600_000).toISOString() },
            { limit_code: 'campaigns', label: 'chiến dịch', used: campaigns.filter(c => c.workspace_id === wsId).length, limit: 25, remaining: 25, exceeded: false, scope: 'workspace', window: null, resets_at: null },
            { limit_code: 'contents', label: 'bài nội dung', used: contents.filter(c => c.workspace_id === wsId).length, limit: 500, remaining: 500, exceeded: false, scope: 'workspace', window: null, resets_at: null },
            { limit_code: 'workspace_members', label: 'thành viên', used: 2, limit: 10, remaining: 8, exceeded: false, scope: 'workspace', window: null, resets_at: null },
            { limit_code: 'schedules', label: 'lịch đăng', used: 0, limit: 200, remaining: 200, exceeded: false, scope: 'workspace', window: null, resets_at: null },
            { limit_code: 'workspaces_per_user', label: 'không gian làm việc', used: 1, limit: 5, remaining: 4, exceeded: false, scope: 'user', window: null, resets_at: null },
          ],
        }),
      });
    }

    if ((path.endsWith('/brand-kit') || path.match(/\/workspaces\/\d+\/brand-kit/)) && method === 'GET') {
      const wsIdParam = url.searchParams.get('workspace_id');
      const wsIdMatch = path.match(/\/workspaces\/(\d+)\/brand-kit/);
      const wsId = wsIdParam ? Number(wsIdParam) : (wsIdMatch ? Number(wsIdMatch[1]) : 1);
      const kit = INITIAL_BRAND_KITS[wsId] || INITIAL_BRAND_KITS[1];
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(kit),
      });
    }

    // 3. Campaigns
    if (path.endsWith('/campaigns') && method === 'GET') {
      const wsId = url.searchParams.get('workspace_id');
      let filtered = wsId ? campaigns.filter(c => c.workspace_id === Number(wsId)) : campaigns;
      filtered = applyFilters(filtered, url, ['name', 'objective', 'audience']);
      filtered = applySort(filtered, url);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(paginate(filtered, url)),
      });
    }

    if (path.endsWith('/products') && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 1,
            workspace_id: 1,
            name: 'Khóa đào tạo Kỹ sư Trí tuệ Nhân tạo Thực chiến ICTU',
            description: 'Chương trình đào tạo AI thực chiến chuẩn quốc tế',
            price: 15000000,
            status: 'ACTIVE',
          },
          {
            id: 2,
            workspace_id: 1,
            name: 'Hệ thống Quản lý Bán hàng & Marketing Omnichannel',
            description: 'Giải pháp SaaS điều phối tiếp thị đa kênh',
            price: 25000000,
            status: 'ACTIVE',
          }
        ]),
      });
    }

    if (path.endsWith('/campaigns') && method === 'POST') {
      const body = request.postDataJSON() || {};
      const newCampaign = {
        id: campaigns.length + 1,
        workspace_id: body.workspace_id || 1,
        product_id: body.product_id || 1,
        owner_id: currentUser.id,
        name: body.name,
        objective: body.objective || '',
        audience: body.audience || '',
        start_date: body.start_date || '2026-09-01',
        end_date: body.end_date || '2026-12-31',
        budget: body.budget || 10000000,
        status: 'DRAFT',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      campaigns.push(newCampaign);
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(newCampaign),
      });
    }

    if (path.match(/\/campaigns\/\d+$/) && (method === 'PUT' || method === 'PATCH')) {
      const match = path.match(/\/campaigns\/(\d+)$/);
      const campId = match ? Number(match[1]) : 0;
      const body = request.postDataJSON() || {};
      const idx = campaigns.findIndex(c => c.id === campId);
      if (idx !== -1) {
        campaigns[idx] = { ...campaigns[idx], ...body, updated_at: new Date().toISOString() };
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(campaigns[idx]),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: campId, ...body }),
      });
    }

    if (path.match(/\/campaigns\/\d+\/kpi/) && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(options.customKpis || INITIAL_KPIS),
      });
    }

    if (path.match(/\/campaigns\/\d+\/ai-doctor/) && (method === 'POST' || method === 'GET')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(options.customDoctor || INITIAL_AI_DOCTOR_REPORT),
      });
    }

    // 4. Contents
    if (path.endsWith('/contents') && method === 'GET') {
      const wsId = url.searchParams.get('workspace_id');
      const campaignIdParam = url.searchParams.get('campaign_id');
      let result = contents;
      if (wsId) {
        const matchingCampaignIds = campaigns.filter(c => c.workspace_id === Number(wsId)).map(c => c.id);
        result = contents.filter(ct => matchingCampaignIds.includes(ct.campaign_id));
      }
      if (campaignIdParam) {
        result = result.filter(ct => ct.campaign_id === Number(campaignIdParam));
      }
      result = applyFilters(result, url, ['title', 'body']);
      result = applySort(result, url);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(paginate(result, url)),
      });
    }

    // 4b. Nội dung của một chiến dịch — cũng dùng envelope `Page`.
    if (/\/campaigns\/\d+\/contents$/.test(path) && method === 'GET') {
      const campaignId = Number(path.match(/\/campaigns\/(\d+)\/contents/)![1]);
      let result = contents.filter(ct => ct.campaign_id === campaignId);
      result = applyFilters(result, url, ['title', 'body']);
      result = applySort(result, url);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(paginate(result, url)),
      });
    }

    if (path.endsWith('/contents') && method === 'POST') {
      const body = request.postDataJSON() || {};
      const newContent = {
        id: contents.length + 1,
        campaign_id: body.campaign_id || 1,
        channel_id: body.channel_id || 1,
        title: body.title,
        body: body.body,
        cta: body.cta || '',
        image_url: body.image_url || 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1200&auto=format&fit=crop&q=80',
        status: body.status || 'AI_DRAFT',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        channel: { id: body.channel_id || 1, name: body.channel_id === 2 ? 'TikTok' : body.channel_id === 3 ? 'Email' : 'Facebook' },
      };
      contents.push(newContent);
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(newContent),
      });
    }

    if (path.match(/\/contents\/\d+$/) && method === 'PUT') {
      const idMatch = path.match(/\/contents\/(\d+)$/);
      const id = idMatch ? Number(idMatch[1]) : 0;
      const body = request.postDataJSON() || {};
      const item = contents.find(c => c.id === id);
      if (item) {
        Object.assign(item, body);
        item.updated_at = new Date().toISOString();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(item),
        });
      }
      return route.fulfill({ status: 404, body: JSON.stringify({ detail: 'Nội dung không tồn tại' }) });
    }

    if (path.match(/\/contents\/\d+\/schedule/) && method === 'POST') {
      const idMatch = path.match(/\/contents\/(\d+)\/schedule/);
      const contentId = idMatch ? Number(idMatch[1]) : 0;
      const body = request.postDataJSON() || {};
      const targetContent = contents.find(c => c.id === contentId);
      const newSchedule = {
        id: Date.now(),
        content_id: contentId,
        scheduled_time: body.scheduled_at || new Date().toISOString(),
        channel_id: targetContent?.channel_id || 1,
        status: 'SCHEDULED',
        campaign_id: targetContent?.campaign_id || 1,
        title: targetContent?.title || 'Bài viết đã lập lịch'
      };
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(newSchedule),
      });
    }

    if (path.endsWith('/schedules') && method === 'POST') {
      const body = request.postDataJSON() || {};
      const contentId = body.content_id || 1;
      const targetContent = contents.find(c => c.id === contentId);
      const newSchedule = {
        id: Date.now(),
        content_id: contentId,
        scheduled_time: body.scheduled_at || body.scheduled_time || new Date().toISOString(),
        channel_id: targetContent?.channel_id || 1,
        status: 'SCHEDULED',
        campaign_id: targetContent?.campaign_id || 1,
        title: targetContent?.title || 'Bài viết đã lập lịch'
      };
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(newSchedule),
      });
    }

    if (path.endsWith('/schedules') && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(paginate([
          {
            id: 1,
            content_id: 3,
            scheduled_time: '2026-09-30T10:00:00Z',
            channel_id: 1,
            status: 'SCHEDULED',
            campaign_id: 1,
            title: '[Thư mời] Hội thảo Định hướng Chuyên gia AI & Cơ hội Việc làm Toàn cầu'
          }
        ], url)),
      });
    }

    // 4c. Tác vụ — danh sách dùng envelope `Page` như mọi endpoint khác.
    if (/\/tasks\/my-tasks\/summary$/.test(path) && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ overdue: 1, today: 1, in_progress: 1, done: 2, total: 5 }),
      });
    }

    if (path.endsWith('/tasks/my-tasks') && method === 'GET') {
      let result = INITIAL_TASKS as any[];
      result = applyFilters(result, url, ['title', 'description']);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(paginate(result, url)),
      });
    }

    if (/\/campaigns\/\d+\/tasks$/.test(path) && method === 'GET') {
      const campaignId = Number(path.match(/\/campaigns\/(\d+)\/tasks/)![1]);
      let result = INITIAL_TASKS.filter(t => t.campaign_id === campaignId) as any[];
      result = applyFilters(result, url, ['title', 'description']);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(paginate(result, url)),
      });
    }

    // Submit for review
    if (path.match(/\/contents\/\d+\/submit/) && method === 'POST') {
      const idMatch = path.match(/\/contents\/(\d+)\/submit/);
      const id = idMatch ? Number(idMatch[1]) : 0;
      const item = contents.find(c => c.id === id);
      if (item) {
        item.status = 'IN_REVIEW';
        item.updated_at = new Date().toISOString();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(item),
        });
      }
      return route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Nội dung không tồn tại' }),
      });
    }

    // Approve
    if (path.match(/\/contents\/\d+\/approve/) && method === 'POST') {
      const idMatch = path.match(/\/contents\/(\d+)\/approve/);
      const id = idMatch ? Number(idMatch[1]) : 0;
      const item = contents.find(c => c.id === id);
      if (!item) {
        return route.fulfill({ status: 404, body: JSON.stringify({ detail: 'Nội dung không tồn tại' }) });
      }

      // Check RBAC permission for approve
      const isApproverRole = ['MANAGER', 'AGENCY_MANAGER', 'CLIENT_APPROVER'].includes(currentUser.role);
      if (!isApproverRole) {
        return route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Chỉ Quản lý (Manager, Agency Manager, Client Approver) mới có quyền duyệt nội dung!' }),
        });
      }

      // Check workspace boundary for Client Approver
      const campaign = campaigns.find(c => c.id === item.campaign_id);
      if (currentUser.role === 'CLIENT_APPROVER' && campaign && campaign.workspace_id !== 1) {
        return route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Bạn không có quyền thao tác trên tài nguyên thuộc không gian làm việc này (403 Forbidden)' }),
        });
      }

      item.status = 'APPROVED';
      item.updated_at = new Date().toISOString();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(item),
      });
    }

    // Reject
    if (path.match(/\/contents\/\d+\/reject/) && method === 'POST') {
      const idMatch = path.match(/\/contents\/(\d+)\/reject/);
      const id = idMatch ? Number(idMatch[1]) : 0;
      const body = request.postDataJSON() || {};
      const item = contents.find(c => c.id === id);
      if (!item) {
        return route.fulfill({ status: 404, body: JSON.stringify({ detail: 'Nội dung không tồn tại' }) });
      }

      const isApproverRole = ['MANAGER', 'AGENCY_MANAGER', 'CLIENT_APPROVER'].includes(currentUser.role);
      if (!isApproverRole) {
        return route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Chỉ Quản lý mới có quyền từ chối bài viết!' }),
        });
      }

      item.status = 'REJECTED';
      const reasonText = body.reason || body.rejection_feedback || 'Cần điều chỉnh nội dung';
      (item as any).rejection_reason = reasonText;
      (item as any).rejection_feedback = reasonText;
      item.updated_at = new Date().toISOString();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(item),
      });
    }

    // Compliance Check
    if (path.endsWith('/contents/compliance-check') && method === 'POST') {
      const body = request.postDataJSON() || {};
      const textToScan = `${body.title || ''} ${body.body || ''} ${body.cta || ''}`.toLowerCase();
      const banned = ['cam kết 100%', 'chữa dứt điểm', 'làm giàu nhanh', 'đa cấp', 'hoàn tiền không lý do'];
      const foundViolations: any[] = [];

      for (const word of banned) {
        if (textToScan.includes(word)) {
          foundViolations.push({
            word: word,
            keyword: word,
            category: 'BRAND_BANNED',
            severity: 'HIGH',
            reason: `Cụm từ "${word}" vi phạm chính sách quảng cáo cam kết tuyệt đối.`,
            suggestion: `thay bằng "định hướng việc làm vững chắc"`,
          });
        }
      }

      if (foundViolations.length > 0) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            status: 'VIOLATION',
            score: 45,
            violations: foundViolations,
            can_submit: false,
          }),
        });
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'PASSED',
          score: 100,
          violations: [],
          can_submit: true,
        }),
      });
    }

    // ---------------------------------------------------------------------
    // 5a. HÀNG ĐỢI AI BẤT ĐỒNG BỘ (POST /ai/jobs -> poll GET /ai/jobs/{id})
    //
    // Mock bám đúng hợp đồng backend thật (app/api/v1/ai_jobs.py): 202 với
    // {job_id,status}, poll trả queued -> running -> succeeded, huỷ chỉ được
    // khi đang queued. Job đi qua `queued` và `running` trước khi xong để các
    // test chạm đúng đường poll thật thay vì đường "thành công ngay lập tức".
    // ---------------------------------------------------------------------
    if (path.endsWith('/ai/jobs') && method === 'POST') {
      const body = request.postDataJSON() || {};
      const jobId = (setupMockApiRoutes._nextJobId = (setupMockApiRoutes._nextJobId || 9000) + 1);

      // Nhớ `kind` + số lần poll để `GET /ai/jobs/{id}` trả đúng kết quả.
      setupMockApiRoutes._jobs[jobId] = { kind: body.kind, polls: 0 };

      return route.fulfill({
        status: 202,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: jobId,
          status: 'queued',
          kind: body.kind,
          deduplicated: false,
          poll_url: `/api/v1/ai/jobs/${jobId}`,
        }),
      });
    }

    if (path.endsWith('/ai/jobs') && method === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 20, has_next: false }),
      });
    }

    const cancelMatch = path.match(/\/ai\/jobs\/(\d+)\/cancel$/);
    if (cancelMatch && method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: Number(cancelMatch[1]),
          status: 'cancelled',
          kind: 'omnichannel',
          deduplicated: false,
          poll_url: `/api/v1/ai/jobs/${cancelMatch[1]}`,
        }),
      });
    }

    const jobMatch = path.match(/\/ai\/jobs\/(\d+)$/);
    if (jobMatch && method === 'GET') {
      const jobId = Number(jobMatch[1]);
      const job = (setupMockApiRoutes._jobs[jobId] ||= { kind: 'omnichannel', polls: 0 });
      job.polls += 1;
      const kind = job.kind;

      // 2 vòng đầu chỉ trả trạng thái, vòng thứ 3 mới trả kết quả. Đủ để test
      // phải thật sự thăm dò, nhưng vẫn nhanh (mỗi vòng 1.5 giây backoff).
      if (job.polls < 2) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            job_id: jobId,
            kind,
            status: job.polls === 1 ? 'queued' : 'running',
            attempts: 1,
            max_attempts: 3,
            error: null,
            result: null,
          }),
        });
      }

      const results: Record<string, any> = {
        ideas: MOCK_AI_IDEAS,
        draft: MOCK_AI_DRAFT,
        omnichannel: MOCK_AI_OMNICHANNEL,
      };

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: jobId,
          kind,
          status: 'succeeded',
          attempts: 1,
          max_attempts: 3,
          error: null,
          result: results[kind] || MOCK_AI_OMNICHANNEL,
        }),
      });
    }

    // 5. AI Endpoints ĐỒNG BỘ (backend đánh dấu deprecated nhưng vẫn còn, giữ mock
    // để không vỡ nếu còn mã gọi tới). Nội dung dùng chung với hàng đợi ở trên.
    if (path.endsWith('/ai/ideas') && method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_AI_IDEAS),
      });
    }

    if (path.endsWith('/ai/draft') && method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_AI_DRAFT),
      });
    }

    if (path.endsWith('/ai/omnichannel') && method === 'POST') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_AI_OMNICHANNEL),
      });
    }
    // 6. Analytics
    if (path.endsWith('/analytics/dashboard') && method === 'GET') {
      // `campaigns_summary.active_budget` là TỔNG ngân sách chiến dịch đang chạy
      // của tenant. Thẻ "Ngân sách đang chạy" ở màn hình Quản lý Chiến dịch đọc
      // trường này thay vì tự cộng trên danh sách đã phân trang — nếu thiếu, thẻ
      // sẽ hiện số sai mà test không bắt được.
      const activeBudget = campaigns
        .filter(c => c.status === 'ACTIVE')
        .reduce((sum, c) => sum + (Number(c.budget) || 0), 0);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          kpi: options.customKpis || INITIAL_KPIS,
          campaigns_summary: {
            total: campaigns.length,
            active: campaigns.filter(c => c.status === 'ACTIVE').length,
            active_budget: activeBudget,
          },
        }),
      });
    }

    // 7. BYOK Settings
    // `/settings/ai-keys/list` là endpoint DANH SÁCH nên trả envelope `Page`;
    // hai đường kia trả về đối tượng đơn. Gộp chung handler sẽ khiến mock trả
    // sai hình dạng cho một trong hai và test chỉ đúng khi chạy mock.
    if (path.endsWith('/settings/ai-keys/list') && method === 'GET') {
      const wsId = url.searchParams.get('workspace_id');
      const filtered = wsId ? byokKeys.filter(k => k.workspace_id === Number(wsId) || !k.workspace_id) : byokKeys;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(paginate(filtered, url)),
      });
    }

    if ((path.endsWith('/settings/byok/keys') || path.endsWith('/settings/ai-keys')) && method === 'GET') {
      const wsId = url.searchParams.get('workspace_id');
      const filtered = wsId ? byokKeys.filter(k => k.workspace_id === Number(wsId) || !k.workspace_id) : byokKeys;
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(filtered[0] ?? null),
      });
    }

    if ((path.endsWith('/settings/byok/test') || path.endsWith('/settings/ai-keys/test') || path.endsWith('/settings/test-ai-connection')) && method === 'POST') {
      const body = request.postDataJSON() || {};
      const key = body.api_key || '';
      if (!key || key.trim().length < 8 || key.includes('invalid')) {
        return route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            latency_ms: 0,
            message: 'API Key không hợp lệ hoặc không có quyền truy cập Gemini API.',
            error: 'INVALID_API_KEY',
          }),
        });
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          latency_ms: 124,
          message: 'Kết nối API Key Google Gemini 2.5 Flash thành công!',
        }),
      });
    }

    if (path.match(/\/settings\/ai-keys\/\d+\/toggle/) && method === 'PATCH') {
      const idMatch = path.match(/\/settings\/ai-keys\/(\d+)\/toggle/);
      const id = idMatch ? Number(idMatch[1]) : 0;
      const keyObj = byokKeys.find(k => k.id === id);
      if (keyObj) {
        keyObj.is_active = !keyObj.is_active;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(keyObj),
        });
      }
      return route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Key not found' }) });
    }

    if ((path.endsWith('/settings/byok/save') || path.endsWith('/settings/ai-keys')) && method === 'POST') {
      const body = request.postDataJSON() || {};
      const newKey = {
        id: byokKeys.length + 1,
        provider: body.provider || 'gemini',
        masked_key: `${(body.api_key || 'AIzaSy').slice(0, 6)}...${(body.api_key || '1234').slice(-4)}`,
        key_preview: `${(body.api_key || 'AIzaSy').slice(0, 6)}...${(body.api_key || '1234').slice(-4)}`,
        model: body.model || 'gemini-2.5-flash',
        scope: body.scope || 'workspace',
        workspace_id: body.workspace_id || 1,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      byokKeys = [newKey, ...byokKeys];
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Khóa API đã được mã hóa Fernet AES-128 và lưu trữ thành công!',
          key: newKey,
          ...newKey
        }),
      });
    }

    if ((path.match(/\/settings\/byok\/keys\/\d+/) || path.match(/\/settings\/ai-keys\/\d+/)) && method === 'DELETE') {
      const idMatch = path.match(/\/settings\/(?:byok\/keys|ai-keys)\/(\d+)/);
      const id = idMatch ? Number(idMatch[1]) : 0;
      byokKeys = byokKeys.filter(k => k.id !== id);
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Đã xóa cấu hình khóa AI thành công!' }),
      });
    }

    if (path.endsWith('/settings/ai-keys') && method === 'DELETE') {
      const wsId = url.searchParams.get('workspace_id');
      byokKeys = wsId ? byokKeys.filter(k => k.workspace_id !== Number(wsId)) : [];
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'DEACTIVATED', message: 'Đã xóa cấu hình khóa AI thành công!' }),
      });
    }

    // -------------------------------------------------------------------------
    // HAI endpoint chua duoc handler o tren - giu them o day de mock mode HERMETIC
    // (khong bao gio cham toi mang that).
    // -------------------------------------------------------------------------
    if (path.endsWith('/notifications') && (method === 'GET' || method === 'HEAD')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(paginate([], url)),
      });
    }

    if (/\/campaigns\/\d+\/metrics$/.test(path) && (method === 'GET' || method === 'HEAD')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    }

    // -------------------------------------------------------------------------
    // Default fallback: BAY KHUONG cua toan bo API.
    //
    // Truoc day la `route.continue()` - nghia la bat ky endpoint nao chua duoc
    // handler se GOC toi mang that. O E2E_MODE=mock khong co backend that, nen
    // app nhan AxiosError, render trang loi/empty, va cac test a11y/E2E fail
    // vi ly do hoan toan khong lien quan den UI can sua. Hon nua, no lam che
    // mau: test "xanh" vi data rong chu khong phai vi dung.
    //
    // Bay gio tra 200 voi shape rong dung theo method, va CANH BAO mot lan cho
    // moi path de kho gap cua mock la bat quang ngay trong log thay vi im lang.
    // -------------------------------------------------------------------------
    const warnOnce = (p: string) => {
      const cache = setupMockApiRoutes._warned || (setupMockApiRoutes._warned = new Set<string>());
      if (!cache.has(p)) {
        cache.add(p);
        console.warn(`[mock-api] CHUA CO HANDLER cho ${method} ${p} -> tra 200 shape rong. ` +
          `Neu test fail do thieu du lieu, hay bo sung handler o mock-api.ts.`);
      }
    };
    warnOnce(path);

    // Mặc định cho GET trả envelope `Page` rỗng thay vì `[]`: hầu hết endpoint GET
    // còn lại là endpoint DANH SÁCH, và `toPage()` của frontend chấp nhận cả hai
    // hình nên app vẫn chạy được — nhưng nếu trả mảng thì `total` luôn bằng số
    // dòng của trang, đúng cái sai mà test phân trang cần phát hiện.
    const emptyBody = method === 'GET' || method === 'HEAD'
      ? JSON.stringify(paginate([], url))
      : JSON.stringify({ detail: 'Mock response (chua co handler)' });
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: emptyBody,
    });
  });
}

setupMockApiRoutes._warned = new Set<string>();
/** Bộ nhớ job của hàng đợi AI giả lập: `{ kind, polls }` cho từng `job_id`. */
setupMockApiRoutes._jobs = {} as Record<number, { kind: string; polls: number }>;
/** `job_id` kế tiếp; bắt đầu từ 9000 để không đụng id của nội dung/chiến dịch mẫu. */
setupMockApiRoutes._nextJobId = 9000;
