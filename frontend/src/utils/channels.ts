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
  shortLabel: string;
  chip: string;
  dot: string;
  icon: LucideIcon;
}

const PRESENTATION: Record<string, ChannelPresentation> = {
  facebook: {
    label: 'Facebook Ads / Post',
    shortLabel: 'Facebook',
    chip: 'bg-[#EFF6FF] text-[#1D4ED8] border-[#BFDBFE]',
    dot: 'bg-[#1D4ED8]',
    icon: ThumbsUp,
  },
  email: {
    label: 'Email Newsletter',
    shortLabel: 'Email',
    chip: 'bg-[#F6F5F0] text-[#121316] border-[#D0CEC7]',
    dot: 'bg-[#5A5E66]',
    icon: Mail,
  },
  blog: {
    label: 'Blog SEO',
    shortLabel: 'Website / SEO',
    chip: 'bg-[#F0FDF4] text-[#15803D] border-[#BBF7D0]',
    dot: 'bg-[#15803D]',
    icon: Globe,
  },
  google_ads: {
    label: 'Google Search Ads',
    shortLabel: 'Google Ads',
    chip: 'bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]',
    dot: 'bg-[#B45309]',
    icon: ExternalLink,
  },
  tiktok: {
    label: 'TikTok Short Video',
    shortLabel: 'TikTok',
    chip: 'bg-[#121316] text-white border-[#121316]',
    dot: 'bg-[#121316]',
    icon: Video,
  },
  [UNKNOWN_CHANNEL_CODE]: {
    label: 'Kênh khác',
    shortLabel: 'Kênh khác',
    chip: 'bg-[#F6F5F0] text-[#121316] border-[#E4E2DD]',
    dot: 'bg-[#5A5E66]',
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