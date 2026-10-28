import type { HTMLAttributes, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { cn } from '@/lib/cn';

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('rounded-xl border border-border bg-surface shadow-sm', className)}
      {...rest}
    />
  );
}

export function CardHeader({
  title,
  description,
  actions,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-start justify-between gap-3 rounded-t-xl border-b border-border/80 bg-subtle/45 px-5 py-3.5',
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-sm font-semibold text-fg">{title}</h2>
        {description && <div className="mt-0.5 text-[0.8125rem] text-fg-muted">{description}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function CardBody({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('p-5', className)} {...rest} />;
}

export interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  /** Liên kết quay lại (vd về danh sách). */
  back?: { to: string; label: string };
  meta?: ReactNode;
}

export function PageHeader({ title, description, actions, back, meta }: PageHeaderProps) {
  return (
    <div className="mb-5 border-b border-border/70 pb-4">
      {back && (
        <Link
          to={back.to}
          className="mb-2 inline-flex items-center gap-1 rounded text-[0.8125rem] font-medium text-fg-muted hover:text-accent"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden />
          {back.label}
        </Link>
      )}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <span className="h-5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
            <h1 className="text-xl font-bold tracking-tight text-fg">{title}</h1>
          </div>
          {description && <div className="mt-1 pl-4 text-sm text-fg-muted">{description}</div>}
          {meta && <div className="mt-2 flex flex-wrap items-center gap-2 pl-4">{meta}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}

/** Danh sách mô tả 2 cột (nhãn – giá trị) cho trang chi tiết. */
export function DescriptionList({ items, className }: { items: { label: string; value: ReactNode }[]; className?: string }) {
  return (
    <dl className={cn('grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2', className)}>
      {items.map((it) => (
        <div key={it.label} className="min-w-0">
          <dt className="text-xs font-medium text-fg-subtle">{it.label}</dt>
          <dd className="mt-1 whitespace-pre-line break-words text-sm text-fg">{it.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Thông báo inline (cảnh báo/thông tin) trong trang. */
export function Callout({
  tone = 'info',
  title,
  children,
  className,
  icon,
}: {
  tone?: 'info' | 'warning' | 'danger' | 'success';
  title?: ReactNode;
  children?: ReactNode;
  className?: string;
  icon?: ReactNode;
}) {
  const tones = {
    info: 'border-info/25 bg-info-soft text-info-soft-fg',
    warning: 'border-warning/30 bg-warning-soft text-warning-soft-fg',
    danger: 'border-danger/25 bg-danger-soft text-danger-soft-fg',
    success: 'border-success/25 bg-success-soft text-success-soft-fg',
  };
  return (
    <div
      className={cn('flex gap-3 rounded-lg border px-3.5 py-3 text-[0.8125rem]', tones[tone], className)}
      role={tone === 'danger' || tone === 'warning' ? 'alert' : 'status'}
    >
      {icon && <span className="mt-0.5 shrink-0 [&>svg]:h-4 [&>svg]:w-4">{icon}</span>}
      <div className="min-w-0">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={cn(title && 'mt-0.5')}>{children}</div>}
      </div>
    </div>
  );
}
