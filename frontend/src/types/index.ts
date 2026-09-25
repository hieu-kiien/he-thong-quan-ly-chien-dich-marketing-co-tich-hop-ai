export type UserRole = 'MANAGER' | 'MARKETER' | 'CLIENT_APPROVER' | 'AGENCY_MANAGER';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  status: string;
  created_at: string;
}

export interface Workspace {
  id: number;
  name: string;
  slug?: string;
  description?: string;
  owner_id?: number;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface BrandKit {
  id?: number;
  workspace_id?: number;
  brand_name: string;
  usp: string;
  tone_of_voice: string;
  banned_keywords: string[];
  created_at?: string;
  updated_at?: string;
}

export interface Campaign {
  id: number;
  workspace_id?: number;
  product_id: number;
  owner_id: number;
  name: string;
  objective: string;
  audience: string;
  start_date: string;
  end_date: string;
  budget: number;
  status: 'DRAFT' | 'PLANNED' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'ARCHIVED';
  created_at: string;
  updated_at: string;
  product?: Product;
}

export interface Product {
  id: number;
  category_id?: number;
  name: string;
  description?: string;
  usp?: string;
  status?: string;
}

export interface MarketingContent {
  id: number;
  workspace_id?: number;
  campaign_id: number;
  channel_id: number;
  created_by: number;
  title: string;
  body: string;
  cta?: string;
  image_url?: string;
  status: 'DRAFT' | 'AI_DRAFT' | 'IN_REVIEW' | 'APPROVED' | 'REJECTED' | 'PUBLISHED';
  version_no: number;
  source_ids_json: string;
  warnings_json: string;
  rejection_reason?: string;
  reviews?: ContentReview[];
  created_at: string;
  updated_at: string;
  creator?: User;
  channel?: {
    id: number;
    code: string;
    name: string;
  };
}

export interface ContentCreate {
  campaign_id: number;
  channel_id: number;
  workspace_id?: number;
  title: string;
  body: string;
  cta?: string;
  image_url?: string;
  status?: string;
}

export interface ContentUpdate {
  title?: string;
  body?: string;
  cta?: string;
  image_url?: string;
  status?: string;
}


export interface ChannelAttribution {
  channel_id: number;
  channel_name: string;
  channel_slug?: string;
  channel_code?: string;
  views: number;
  clicks: number;
  conversions: number;
  cost: number;
  revenue: number;
  ctr_percent: number;
  cpc_avg: number;
  cvr_percent: number;
  roas: number;
  roi_percent: number;
  share_of_cost: number;
  share_of_revenue: number;
}

export interface AIDoctorRecommendation {
  action: 'SCALE' | 'REDUCE' | 'OPTIMIZE' | 'PAUSE';
  channel?: string;
  reason: string;
  suggestion?: string;
  title?: string;
  description?: string;
  impact?: string;
}

export interface AIDoctorBottleneck {
  category?: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  channel?: string;
  metric_name?: string;
  current_value?: number;
  benchmark_value?: number;
  description: string;
}

export interface AIDoctorReport {
  campaign_id?: number;
  campaign_name?: string;
  health_status: 'HEALTHY' | 'NEEDS_ATTENTION' | 'CRITICAL';
  health_score: number;
  diagnosis_summary: string;
  key_bottlenecks?: string[];
  bottlenecks?: string[];
  recommendations: AIDoctorRecommendation[];
  metrics_analyzed?: any;
  channel_breakdown?: ChannelAttribution[];
  is_sparse_data?: boolean;
  generated_at?: string;
}

export interface KPISummary {
  total_views: number;
  total_clicks: number;
  total_conversions: number;
  total_cost: number;
  total_revenue: number;
  ctr_percent: number;
  cpc_avg: number;
  cvr_percent: number;
  roi_percent: number;
  roas?: number;
  channel_metrics?: ChannelAttribution[];
}

export interface AIIdeaItem {
  id: number;
  angle: string;
  headline: string;
  concept: string;
  target_emotion: string;
}

export interface AIIdeaResponse {
  task_type: string;
  ideas: AIIdeaItem[];
  warnings: string[];
  assumptions: string[];
  model_used: string;
  prompt_version: string;
}

export interface AIDraftResponse {
  task_type: string;
  title: string;
  body: string;
  cta: string;
  warnings: string[];
  assumptions: string[];
  model_used: string;
  prompt_version: string;
}

export interface AISummaryResponse {
  task_type: string;
  executive_summary: string;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  warnings: string[];
  model_used: string;
  prompt_version: string;
}

// ==========================================
// R2: Deep 3-Channel AI Creative Engine Types
// ==========================================

export interface FacebookCreative {
  title: string;
  body: string;
  cta: string;
  hashtags: string[];
  headline?: string;
  primary_text?: string;
  visual_suggestion?: string;
  image_url?: string;
}

export interface TikTokScene {
  scene?: number;
  scene_number?: number;
  visual: string;
  voiceover: string;
  audio?: string;
  visual_action?: string;
  voiceover_script?: string;
  duration_seconds?: string | number;
  audio_hint?: string;
  scene_name?: string;
  title?: string;
}

export interface TikTokCreative {
  hook_3s: string;
  target_duration?: string;
  scenes: TikTokScene[];
  suggested_audio: string;
  sound_recommendation?: string;
  audio_suggestion?: string;
  caption_with_hashtags?: string;
  cta?: string;
  hashtags?: string[];
  image_url?: string;
}

export interface EmailCreative {
  subject_options: string[];
  subject_line_a?: string;
  subject_line_b?: string;
  subject?: string;
  preheader?: string;
  greeting?: string;
  body: string;
  body_content?: string;
  cta_button: string;
  cta_button_text?: string;
  cta_destination_type?: string;
  cta?: string;
  ps_note?: string;
  ps?: string;
  image_url?: string;
}

export interface OmnichannelRequest {
  campaign_id?: number | null;
  brief: string;
  target_audience?: string;
  channels?: string[];
  tone?: string;
  brand_kit_id?: number;
  product_name?: string;
  product_usp?: string;
  prompt_version?: string;
}

export interface OmnichannelResponse {
  task_type?: string;
  campaign_id?: number | null;
  facebook?: FacebookCreative;
  tiktok?: TikTokCreative;
  email?: EmailCreative;
  is_fallback?: boolean;
  compliance_score?: number;
  warnings?: string[];
  assumptions?: string[];
  model_used?: string;
  prompt_version?: string;
  model_provider?: string;
}

export interface MarketingSchedule {
  id: number;
  content_id: number;
  scheduled_at: string;
  timezone: string;
  status: 'PLANNED' | 'CANCELLED' | 'EXECUTED';
  created_by: number;
  created_at: string;
  content?: MarketingContent;
}

export interface ComplianceViolation {
  category: 'AD_POLICY' | 'BRAND_BANNED' | string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  word: string;
  suggestion: string;
  reason?: string;
}

export interface ComplianceCheckRequest {
  workspace_id?: number;
  channel?: string;
  title?: string;
  body?: string;
  cta?: string;
}

export interface ComplianceCheckResponse {
  status: 'PASSED' | 'WARNING' | 'VIOLATION';
  score: number;
  can_submit: boolean;
  violations: ComplianceViolation[];
  summary?: string;
  flagged_items?: {
    phrase: string;
    risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
    reason: string;
    suggestion: string;
  }[];
}

export interface ContentReview {
  id: number;
  content_id: number;
  reviewer_id: number;
  decision: 'APPROVED' | 'REJECTED' | 'REQUEST_CHANGES';
  reason: string;
  created_at: string;
  reviewer?: User;
}

export interface ContentComplianceCheck {
  score: number;
  status: 'PASSED' | 'WARNING' | 'VIOLATION';
  summary: string;
  flagged_items: {
    phrase: string;
    risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
    reason: string;
    suggestion: string;
  }[];
}

export interface ChannelBudgetItem {
  channel_code: string;
  channel_name: string;
  allocated_budget: number;
  spent_amount: number;
  clicks: number;
  conversions: number;
  revenue: number;
  roi_percent: number;
}

// ==========================================
// R6: Enterprise Settings & BYOK Custom AI API Key Types
// ==========================================

export interface CustomApiKey {
  id?: number;
  provider: string;
  model: string;
  masked_key: string;
  is_active: boolean;
  workspace_id?: number | null;
  user_id?: number | null;
  scope?: 'workspace' | 'personal' | string;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AIKeyTestRequest {
  provider: string;
  api_key: string;
  model?: string;
}

export interface AIKeyTestResponse {
  success: boolean;
  latency_ms: number;
  message: string;
  provider?: string;
  model?: string;
  error?: string | null;
}

export interface AIKeySaveRequest {
  provider?: string;
  api_key: string;
  model?: string;
  workspace_id?: number | null;
  scope?: 'workspace' | 'personal';
  is_active?: boolean;
}

export interface AIKeySaveResponse {
  id?: number;
  provider: string;
  model: string;
  masked_key: string;
  is_active: boolean;
  workspace_id?: number | null;
  user_id?: number | null;
  scope?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

