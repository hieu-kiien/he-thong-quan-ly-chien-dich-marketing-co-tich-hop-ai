import { Campaign, MarketingContent, KPISummary, Product, MarketingSchedule, User, Workspace, BrandKit, ChannelAttribution, AIDoctorReport, CustomApiKey } from '../types';

export const MOCK_USER_MANAGER: User = {
  id: 1,
  email: 'manager@ictu.edu.vn',
  full_name: 'Quản Lý Chiến Dịch',
  role: 'MANAGER',
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z'
};

export const MOCK_USER_MARKETER: User = {
  id: 2,
  email: 'marketer@ictu.edu.vn',
  full_name: 'Chuyên Viên Tiếp Thị',
  role: 'MARKETER',
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z'
};

export const MOCK_USER_CLIENT_APPROVER: User = {
  id: 3,
  email: 'approver@ictu.edu.vn',
  full_name: 'Đại Diện Khách Hàng (Approver)',
  role: 'CLIENT_APPROVER',
  status: 'ACTIVE',
  created_at: '2026-01-01T00:00:00Z'
};

export const MOCK_WORKSPACES: Workspace[] = [
  {
    id: 1,
    name: 'Default Agency Workspace',
    slug: 'default-agency',
    description: 'Không gian làm việc điều phối chiến dịch tiếp thị tổng lực đa kênh',
    owner_id: 1,
    status: 'ACTIVE',
    created_at: '2026-01-01T00:00:00Z'
  },
  {
    id: 2,
    name: 'VinFast Auto - Brand Campaign',
    slug: 'vinfast-auto',
    description: 'Không gian cách ly chuyên biệt cho thương hiệu VinFast',
    owner_id: 1,
    status: 'ACTIVE',
    created_at: '2026-01-15T00:00:00Z'
  }
];

export const MOCK_BRAND_KITS: Record<number, BrandKit> = {
  1: {
    id: 1,
    workspace_id: 1,
    brand_name: 'MarketFlow AI',
    usp: 'Nền tảng Quản trị & Sáng tạo Tiếp thị Đa kênh Thông minh Chuẩn Doanh nghiệp',
    tone_of_voice: 'Chuyên nghiệp, Đáng tin cậy, Tràn đầy năng lượng chuyển đổi',
    banned_keywords: ['cam kết 100%', 'chữa dứt điểm', 'làm giàu nhanh', 'đa cấp', 'hoàn tiền không lý do']
  },
  2: {
    id: 2,
    workspace_id: 2,
    brand_name: 'VinFast Auto',
    usp: 'Mãnh liệt tinh thần Việt Nam - Xe điện thông minh toàn cầu',
    tone_of_voice: 'Đẳng cấp, Hiện đại, Tiên phong công nghệ xanh',
    banned_keywords: ['rẻ tiền', 'xe tàu', 'không an toàn', 'lỗi pin']
  }
};


export const MOCK_PRODUCTS: Product[] = [
  {
    id: 1,
    name: 'Khóa học AI Marketing Masterclass 2026',
    description: 'Chương trình đào tạo chuyên sâu ứng dụng Generative AI và tự động hóa marketing dành cho doanh nghiệp',
    usp: 'Thực chiến 100% trên các công cụ AI thế hệ mới',
    category_id: 1,
    status: 'ACTIVE'
  },
  {
    id: 2,
    name: 'Nền tảng Tự động hóa Nội dung MarketFlow AI',
    description: 'Giải pháp phần mềm SaaS quản lý vòng đời chiến dịch, phân bổ ngân sách và kiểm duyệt nội dung tiếp thị',
    usp: 'Bảo vệ thương hiệu với bộ lọc tuân thủ chính sách quảng cáo tích hợp AI',
    category_id: 1,
    status: 'ACTIVE'
  }
];

export const MOCK_CAMPAIGNS: Campaign[] = [
  {
    id: 1,
    product_id: 1,
    owner_id: 1,
    name: 'Chiến dịch Tết 2026 - Bứt phá Doanh số Đa kênh',
    objective: 'Gia tăng nhận diện thương hiệu và tạo 1.500 khách hàng tiềm năng qua Facebook, TikTok và Email Marketing',
    audience: 'Chủ doanh nghiệp SME, Trưởng phòng Marketing, Chuyên viên Content Creator 22-40 tuổi',
    budget: 50000000,
    start_date: '2026-01-10',
    end_date: '2026-02-28',
    status: 'ACTIVE',
    created_at: '2026-01-10T00:00:00Z',
    updated_at: '2026-01-10T00:00:00Z',
    product: MOCK_PRODUCTS[0]
  },
  {
    id: 2,
    product_id: 1,
    owner_id: 1,
    name: 'Tuyển sinh Đại học & Đào tạo AI Thực chiến ICTU',
    objective: 'Thu hút 2.000 hồ sơ đăng ký tham gia hội thảo định hướng nghề nghiệp Kỹ sư AI & Marketing số',
    audience: 'Học sinh THPT, sinh viên năm cuối, người đi làm chuyển ngành công nghệ',
    budget: 35000000,
    start_date: '2026-03-01',
    end_date: '2026-04-30',
    status: 'ACTIVE',
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
    product: MOCK_PRODUCTS[0]
  },
  {
    id: 3,
    product_id: 2,
    owner_id: 1,
    name: 'Ra mắt Nền tảng Quản trị Vận hành Tiếp thị MarketFlow AI',
    objective: 'Tiếp cận 100.000 lượt xem và đạt 500 lượt dùng thử bản Enterprise trong quý 1',
    audience: 'Giám đốc Marketing (CMO), Agency Lead, Digital Marketing Managers tại Việt Nam',
    budget: 80000000,
    start_date: '2026-02-01',
    end_date: '2026-03-31',
    status: 'ACTIVE',
    created_at: '2026-02-01T00:00:00Z',
    updated_at: '2026-02-01T00:00:00Z',
    product: MOCK_PRODUCTS[1]
  }
];

export const MOCK_CONTENTS: MarketingContent[] = [
  {
    id: 1,
    campaign_id: 1,
    channel_id: 1,
    created_by: 2,
    title: 'Bí quyết x3 Doanh số Mùa Tết 2026 Nhờ Tự Động Hóa AI',
    body: 'Bạn đang đau đầu vì chi phí quảng cáo tăng cao mà đơn hàng không bù đắp được chi phí? Khám phá ngay quy trình tích hợp AI vào quản lý chiến dịch marketing giúp tối ưu hóa chi phí đến 40% và nhân đôi hiệu suất đội ngũ sáng tạo nội dung.',
    cta: 'Khám phá giải pháp ngay',
    image_url: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=1200&auto=format&fit=crop&q=80',
    status: 'APPROVED',
    version_no: 1,
    source_ids_json: '[]',
    warnings_json: '[]',
    created_at: '2026-09-24T08:00:00Z',
    updated_at: '2026-09-24T08:00:00Z',
    creator: MOCK_USER_MARKETER,
    channel: { id: 1, code: 'FACEBOOK', name: 'Facebook Ads & Post' }
  },
  {
    id: 2,
    campaign_id: 1,
    channel_id: 4,
    created_by: 2,
    title: 'Kịch bản Video ngắn: 1 Ngày Của Marketer Khi Có AI Trợ Lý',
    body: 'Góc nhìn thực tế từ bàn làm việc: Lên 10 concept bài viết chỉ trong 3 phút, quét sạch từ ngữ nhạy cảm vi phạm chính sách Meta trước khi bấm duyệt. Tiết kiệm 4 tiếng làm việc mỗi ngày!',
    cta: 'Xem chi tiết tại link bio',
    image_url: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop&q=80',
    status: 'IN_REVIEW',
    version_no: 1,
    source_ids_json: '[]',
    warnings_json: '[]',
    created_at: '2026-09-24T08:30:00Z',
    updated_at: '2026-09-24T08:30:00Z',
    creator: MOCK_USER_MARKETER,
    channel: { id: 4, code: 'TIKTOK', name: 'TikTok Short Video' }
  },
  {
    id: 3,
    campaign_id: 1,
    channel_id: 2,
    created_by: 2,
    title: 'Thư mời độc quyền: Trải nghiệm Nền tảng MarketFlow AI Vòng Alpha',
    body: 'Kính gửi Quý đối tác, Chúng tôi trân trọng kính mời Anh/Chị tham gia chương trình trải nghiệm giải pháp điều phối chiến dịch tiếp thị đa kênh tiên phong kết hợp AI Human-in-the-loop.',
    cta: 'Xác nhận tham gia',
    image_url: 'https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1200&auto=format&fit=crop&q=80',
    status: 'IN_REVIEW',
    version_no: 1,
    source_ids_json: '[]',
    warnings_json: '[]',
    created_at: '2026-09-24T09:00:00Z',
    updated_at: '2026-09-24T09:00:00Z',
    creator: MOCK_USER_MARKETER,
    channel: { id: 2, code: 'EMAIL', name: 'Email Marketing' }
  },
  {
    id: 4,
    campaign_id: 1,
    channel_id: 3,
    created_by: 2,
    title: 'Google Search Ads: Tối Ưu Chi Phí Quảng Cáo Với AI',
    body: 'Tìm kiếm giải pháp cắt giảm chi phí CPA và tăng tỷ lệ chuyển đổi? MarketFlow AI giúp theo dõi ROI và điều chuyển ngân sách thông minh tự động.',
    cta: 'Đăng ký dùng thử miễn phí',
    image_url: 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&auto=format&fit=crop&q=80',
    status: 'APPROVED',
    version_no: 1,
    source_ids_json: '[]',
    warnings_json: '[]',
    created_at: '2026-09-24T09:15:00Z',
    updated_at: '2026-09-24T09:15:00Z',
    creator: MOCK_USER_MARKETER,
    channel: { id: 3, code: 'GOOGLE_ADS', name: 'Google Search Ads' }
  },
  {
    id: 5,
    campaign_id: 1,
    channel_id: 1,
    created_by: 2,
    title: 'Cam kết tăng 300% doanh thu trong 3 ngày làm giàu nhanh',
    body: 'Phương pháp bí truyền kiếm tiền dễ dàng chắc chắn 100% thành công không cần làm gì.',
    cta: 'Click ngay',
    status: 'REJECTED',
    version_no: 2,
    source_ids_json: '[]',
    warnings_json: '["Lý do từ chối của Quản lý: Vi phạm chính sách cam kết tuyệt đối và ngôn từ giật gân làm giàu nhanh. Yêu cầu sửa đổi bằng AI Copilot."]',
    created_at: '2026-09-24T09:30:00Z',
    updated_at: '2026-09-24T09:45:00Z',
    creator: MOCK_USER_MARKETER,
    channel: { id: 1, code: 'FACEBOOK', name: 'Facebook Ads & Post' }
  },
  {
    id: 6,
    campaign_id: 2,
    channel_id: 1,
    created_by: 2,
    title: 'Học bổng Ươm mầm Tài năng AI & Data Science 2026',
    body: 'Khoa Công nghệ Thông tin ICTU công bố 50 suất học bổng toàn phần dành cho tân sinh viên xuất sắc đam mê lĩnh vực Trí tuệ Nhân tạo và Tiếp thị số.',
    cta: 'Nộp hồ sơ xét học bổng',
    status: 'APPROVED',
    version_no: 1,
    source_ids_json: '[]',
    warnings_json: '[]',
    created_at: '2026-09-24T10:00:00Z',
    updated_at: '2026-09-24T10:00:00Z',
    creator: MOCK_USER_MARKETER,
    channel: { id: 1, code: 'FACEBOOK', name: 'Facebook Ads & Post' }
  }
];

export const MOCK_SCHEDULES: MarketingSchedule[] = [
  {
    id: 1,
    content_id: 1,
    scheduled_at: '2026-09-25T09:00:00+07:00',
    timezone: 'Asia/Ho_Chi_Minh',
    status: 'PLANNED',
    created_by: 1,
    created_at: '2026-09-24T08:00:00Z',
    content: MOCK_CONTENTS[0]
  },
  {
    id: 2,
    content_id: 4,
    scheduled_at: '2026-09-26T14:30:00+07:00',
    timezone: 'Asia/Ho_Chi_Minh',
    status: 'PLANNED',
    created_by: 1,
    created_at: '2026-09-24T09:15:00Z',
    content: MOCK_CONTENTS[3]
  }
];

export const MOCK_DASHBOARD_KPI: KPISummary = {
  total_views: 185420,
  total_clicks: 9680,
  total_conversions: 842,
  total_cost: 21500000,
  total_revenue: 68900000,
  ctr_percent: 5.22,
  cpc_avg: 2221.07,
  cvr_percent: 8.7,
  roi_percent: 220.47,
  roas: 3.20
};

export const MOCK_CHANNEL_ATTRIBUTIONS: ChannelAttribution[] = [
  {
    channel_id: 1,
    channel_name: 'Facebook Feed & Ads',
    channel_slug: 'facebook',
    channel_code: 'FACEBOOK',
    views: 98500,
    clicks: 5120,
    conversions: 380,
    cost: 9500000,
    revenue: 29450000,
    ctr_percent: 5.20,
    cpc_avg: 1855,
    cvr_percent: 7.42,
    roas: 3.10,
    roi_percent: 210.0,
    share_of_cost: 44.2,
    share_of_revenue: 42.7
  },
  {
    channel_id: 4,
    channel_name: 'TikTok Short Video',
    channel_slug: 'tiktok',
    channel_code: 'TIKTOK',
    views: 72000,
    clicks: 3860,
    conversions: 395,
    cost: 8800000,
    revenue: 35200000,
    ctr_percent: 5.36,
    cpc_avg: 2280,
    cvr_percent: 10.23,
    roas: 4.00,
    roi_percent: 300.0,
    share_of_cost: 40.9,
    share_of_revenue: 51.1
  },
  {
    channel_id: 2,
    channel_name: 'Email Marketing',
    channel_slug: 'email',
    channel_code: 'EMAIL',
    views: 14920,
    clicks: 700,
    conversions: 67,
    cost: 3200000,
    revenue: 4250000,
    ctr_percent: 4.69,
    cpc_avg: 4571,
    cvr_percent: 9.57,
    roas: 1.33,
    roi_percent: 32.8,
    share_of_cost: 14.9,
    share_of_revenue: 6.2
  }
];

export const MOCK_AI_DOCTOR_REPORT: AIDoctorReport = {
  campaign_id: 1,
  campaign_name: 'Chiến Dịch Ra Mắt Khóa Học AI K25',
  health_status: 'HEALTHY',
  health_score: 86,
  diagnosis_summary: 'Chiến dịch duy trì chỉ số sinh lời tích cực với ROAS tổng đạt 3.20x và ROI +220.5%. Kênh TikTok là động lực doanh thu mạnh nhất (ROAS 4.00x), trong khi kênh Email có ROAS 1.33x đang làm giảm tốc độ hoàn vốn chung.',
  key_bottlenecks: [
    'Kênh Email có ROAS 1.33x (dưới ngưỡng hòa vốn khuyến nghị 1.5x) và chi phí mỗi click CPC cao (4.571 VNĐ), cần cá nhân hóa tiêu đề.',
    'Kênh Facebook có tỷ lệ nhấp tốt (CTR 5.20%) nhưng tỷ lệ chuyển đổi tại giỏ hàng giảm 18% vào cuối tuần.',
    'Kênh TikTok có dư địa tăng trưởng ngân sách lớn nhưng hiện chỉ nhận 40.9% tổng chi phí.'
  ],
  bottlenecks: [
    'Kênh Email có ROAS 1.33x (dưới ngưỡng hòa vốn khuyến nghị 1.5x) và chi phí mỗi click CPC cao (4.571 VNĐ), cần cá nhân hóa tiêu đề.',
    'Kênh Facebook có tỷ lệ nhấp tốt (CTR 5.20%) nhưng tỷ lệ chuyển đổi tại giỏ hàng giảm 18% vào cuối tuần.',
    'Kênh TikTok có dư địa tăng trưởng ngân sách lớn nhưng hiện chỉ nhận 40.9% tổng chi phí.'
  ],
  recommendations: [
    {
      action: 'SCALE',
      channel: 'tiktok',
      title: 'Tăng 30% ngân sách cho Kịch bản TikTok',
      description: 'TikTok đạt ROAS 4.00x vượt kỳ vọng. Tái phân bổ thêm 3.000.000 VNĐ vào các video phân cảnh ngắn giữ chân khách hàng 3 giây đầu.',
      reason: 'TikTok đạt ROAS 4.00x cao nhất toàn chiến dịch và CVR vượt 10%.',
      suggestion: 'Tăng 20-30% ngân sách cho video kịch bản 9:16 có hook ấn tượng.',
      impact: '+22.4% Doanh thu dự kiến'
    },
    {
      action: 'OPTIMIZE',
      channel: 'facebook',
      title: 'A/B Testing tiêu đề & Tối ưu hóa Landing Page Facebook',
      description: 'Điều chỉnh thông điệp Facebook Post Card và gắn ảnh banner thực tế để tăng CVR thanh toán từ 7.4% lên >10%.',
      reason: 'CTR Facebook đạt 5.20% nhưng CVR bị rơi rụng tại trang thanh toán.',
      suggestion: 'Thử nghiệm tiêu đề A/B và tối ưu tốc độ tải trang thanh toán.',
      impact: 'Giảm 12% CPC, tăng CVR thanh toán'
    },
    {
      action: 'PAUSE',
      channel: 'email',
      title: 'Tạm hoãn chuỗi Email Generic & Tối ưu hóa tiêu đề',
      description: 'Tạm dừng các email bản tin chung chung để cắt giảm chi phí lãng phí, chuyển sang chuỗi nuôi dưỡng tự động.',
      reason: 'ROAS kênh Email chỉ đạt 1.33x, làm giảm tỷ suất hoàn vốn tổng.',
      suggestion: 'Tạm hoãn gửi chuỗi email đại trà, tập trung ưu đãi đặc quyền cho khách hàng VIP.',
      impact: 'Tiết kiệm 1.500.000 VNĐ chi phí lãng phí'
    }
  ],
  channel_breakdown: MOCK_CHANNEL_ATTRIBUTIONS,
  is_sparse_data: false,
  generated_at: new Date().toISOString()
};

export const MOCK_CUSTOM_API_KEYS: CustomApiKey[] = [
  {
    id: 1,
    provider: 'gemini',
    model: 'gemini-2.5-flash',
    masked_key: 'AIzaSy...4xQ9',
    is_active: true,
    workspace_id: 1,
    user_id: 1,
    scope: 'workspace',
    status: 'ACTIVE',
    created_at: '2026-02-01T10:00:00Z',
    updated_at: '2026-02-15T14:30:00Z'
  },
  {
    id: 2,
    provider: 'gemini',
    model: 'gemini-2.5-pro',
    masked_key: 'AIzaSy...8kP2',
    is_active: false,
    workspace_id: null,
    user_id: 1,
    scope: 'personal',
    status: 'INACTIVE',
    created_at: '2026-02-10T08:15:00Z',
    updated_at: '2026-02-20T11:00:00Z'
  }
];

