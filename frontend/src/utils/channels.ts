import type { LucideIcon } from 'lucide-react';
import {
  ThumbsUp,
  Mail,
  Globe,
  ExternalLink,
  Video,
  Sparkles,
} from 'lucide-react';

export interface MarketingChannel {
  id: number;
  code: string;
  name: string;
  format_rules?: string | null;
  status: string;
}

export const CHANNEL_CODES = ['facebook', 'email', 'blog', 'google_ads', 'tiktok'] as const;
export type ChannelCode = (typeof CHANNEL_CODES)[number];

const UNKNOWN_CHANNEL_CODE = 'unknown';

export interface ChannelPresentation {
  label: string;
  chip: string;
  dot: string;
  icon: LucideIcon;
}

/**
 * Toàn bộ nhãn/màu/icon được khoá theo `code` chứ không theo `id`.
 * `id` là số thứ tự sinh ra bởi database và thay đổi giữa các môi trường;
 * khoá theo id là nguyên nhân gốc của các bảng map mâu thuẫn (id 2 từng
 * được gọi đồng thời là "TikTok" và là "Email").
 */
const PRESENTATION: Record<string, ChannelPresentation> = {
  facebook: {
    label: 'Facebook Ads / Post',
    chip: 'bg-blue-50 text-blue-700 border-blue-200',
    dot: 'bg-blue-500',
    icon: ThumbsUp,
  },
  email: {
    label: 'Email Newsletter',
    chip: 'bg-purple-50 text-purple-700 border-purple-200',
    dot: 'bg-purple-500',
    icon: Mail,
  },
  blog: {
    label: 'Blog SEO',
    chip: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    dot: 'bg-emerald-500',
    icon: Globe,
  },
  google_ads: {
    label: 'Google Search Ads',
    chip: 'bg-amber-50 text-amber-700 border-amber-200',
    dot: 'bg-amber-500',
    icon: ExternalLink,
  },
  tiktok: {
    label: 'TikTok Short Video',
    chip: 'bg-slate-900 text-white border-slate-900',
    dot: 'bg-slate-900',
    icon: Video,
  },
  [UNKNOWN_CHANNEL_CODE]: {
    label: 'Kênh khác',
    chip: 'bg-slate-50 text-slate-700 border-slate-200',
    dot: 'bg-slate-500',
    icon: Sparkles,
  },
};

const UNKNOWN_PRESENTATION = PRESENTATION[UNKNOWN_CHANNEL_CODE];

/**
 * Thứ tự kênh mặc định của `backend/seed/seed_data.py`. Chỉ dùng làm fallback
 * cho chế độ demo offline (không có backend để hỏi); khi có backend,
 * `setChannelRegistry()` được gọi từ `App.tsx` và ghi đè hoàn toàn giá trị này.
 */
const FALLBACK_REGISTRY: MarketingChannel[] = CHANNEL_CODES.map((code, index) => ({
  id: index + 1,
  code,
  name:
    code === 'facebook'
      ? 'Facebook Ads & Fanpage'
      : code === 'email'
        ? 'Email Marketing Newsletter'
        : code === 'blog'
          ? 'Blog SEO & Website'
          : code === 'google_ads'
            ? 'Google Search Ads'
            : 'TikTok Short Video & Reels',
  status: 'ACTIVE',
}));

let registry: MarketingChannel[] = FALLBACK_REGISTRY;

export function setChannelRegistry(channels: MarketingChannel[]): void {
  if (channels.length === 0) return;
  registry = channels;
}

export function getChannelRegistry(): MarketingChannel[] {
  return registry;
}

export function channelCodeById(channelId: number): string {
  return registry.find((c) => c.id === channelId)?.code ?? UNKNOWN_CHANNEL_CODE;
}

export function channelNameById(channelId: number): string {
  const found = registry.find((c) => c.id === channelId);
  if (found) return found.name;
  return PRESENTATION[channelCodeById(channelId)].label;
}

export function channelIdByCode(code: string): number | null {
  return registry.find((c) => c.code === code)?.id ?? null;
}

export function isKnownChannelCode(code: string): boolean {
  return (CHANNEL_CODES as readonly string[]).includes(code);
}

export function channelPresentation(codeOrId: string | number): ChannelPresentation {
  const code = typeof codeOrId === 'number' ? channelCodeById(codeOrId) : codeOrId;
  return PRESENTATION[code] ?? UNKNOWN_PRESENTATION;
}