import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';
import {
  AI_ACTION_STATUS_LABEL,
  AI_ACTION_STATUS_TONE,
  CAMPAIGN_STATUS_LABEL,
  CAMPAIGN_STATUS_TONE,
  CONTENT_STATUS_LABEL,
  CONTENT_STATUS_TONE,
  METRIC_SOURCE_LABEL,
  METRIC_SOURCE_TONE,
  SCHEDULE_STATUS_LABEL,
  SCHEDULE_STATUS_TONE,
  type Tone,
} from '@/lib/labels';
import type { AiActionStatus, CampaignStatus, ContentStatus, MetricSource, ScheduleStatus } from '@/lib/types';

const tones: Record<Tone, string> = {
  neutral: 'bg-subtle text-fg-muted border-border',
  accent: 'bg-accent-soft text-accent-soft-fg border-accent/20',
  success: 'bg-success-soft text-success-soft-fg border-success/20',
  warning: 'bg-warning-soft text-warning-soft-fg border-warning/25',
  danger: 'bg-danger-soft text-danger-soft-fg border-danger/20',
  info: 'bg-info-soft text-info-soft-fg border-info/20',
};

export interface BadgeProps {
  tone?: Tone;
  children: ReactNode;
  className?: string;
  /** Chấm màu trước nhãn. */
  dot?: boolean;
}

export function Badge({ tone = 'neutral', children, className, dot }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded border px-1.5 py-0.5 text-xs font-medium leading-4',
        tones[tone],
        className,
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
      {children}
    </span>
  );
}

type StatusBadgeProps =
  | { kind: 'campaign'; status: CampaignStatus }
  | { kind: 'content'; status: ContentStatus }
  | { kind: 'schedule'; status: ScheduleStatus }
  | { kind: 'metricSource'; status: MetricSource }
  | { kind: 'aiAction'; status: AiActionStatus };

/** Nhãn trạng thái thống nhất cho mọi thực thể. */
export function StatusBadge(props: StatusBadgeProps & { className?: string }) {
  let label: string;
  let tone: Tone;
  switch (props.kind) {
    case 'campaign':
      label = CAMPAIGN_STATUS_LABEL[props.status];
      tone = CAMPAIGN_STATUS_TONE[props.status];
      break;
    case 'content':
      label = CONTENT_STATUS_LABEL[props.status];
      tone = CONTENT_STATUS_TONE[props.status];
      break;
    case 'schedule':
      label = SCHEDULE_STATUS_LABEL[props.status];
      tone = SCHEDULE_STATUS_TONE[props.status];
      break;
    case 'metricSource':
      label = METRIC_SOURCE_LABEL[props.status];
      tone = METRIC_SOURCE_TONE[props.status];
      break;
    case 'aiAction':
      label = AI_ACTION_STATUS_LABEL[props.status];
      tone = AI_ACTION_STATUS_TONE[props.status];
      break;
  }
  return (
    <Badge tone={tone} dot className={props.className}>
      {label ?? props.status}
    </Badge>
  );
}

/** Nhãn "Dữ liệu mẫu" bắt buộc khi có số liệu source=SEED (CONTRACT §0). */
export function SeedDataBadge({ className }: { className?: string }) {
  return (
    <Badge tone="warning" className={className}>
      Dữ liệu mẫu
    </Badge>
  );
}
