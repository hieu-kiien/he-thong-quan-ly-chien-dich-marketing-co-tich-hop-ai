export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'MANAGER' | 'MARKETER';
  status: string;
  created_at: string;
}

export interface Campaign {
  id: number;
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
  campaign_id: number;
  channel_id: number;
  created_by: number;
  title: string;
  body: string;
  cta?: string;
  status: 'DRAFT' | 'AI_DRAFT' | 'IN_REVIEW' | 'APPROVED' | 'REJECTED' | 'PUBLISHED';
  version_no: number;
  source_ids_json: string;
  warnings_json: string;
  created_at: string;
  updated_at: string;
  creator?: User;
  channel?: {
    id: number;
    code: string;
    name: string;
  };
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
