import { useLayoutEffect, useState, type HTMLAttributes, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
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
  const [slot, setSlot] = useState<HTMLElement | null>(() =>
    typeof document !== 'undefined' ? document.getElementById('mf-topbar-slot') : null,
  );

  useLayoutEffect(() => {
    if (typeof document !== 'undefined') {
      setSlot(document.getElementById('mf-topbar-slot'));
    }
  }, []);

  if (slot && !back) {
    return (
      <>
        {createPortal(
          <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-base font-bold tracking-tight text-fg sm:text-[1.0625rem]">
                  {title}
                </h1>
                {meta && <div className="flex shrink-0 flex-wrap items-center gap-1.5">{meta}</div>}
              </div>
              {description && (
                <div className="mt-0.5 truncate text-xs text-fg-muted">{description}</div>
              )}
            </div>
            {actions && (
              <div className="hidden shrink-0 items-center gap-2 xl:flex">{actions}</div>
            )}
          </div>,
          slot,
        )}
        {actions && (
          <div className="mb-4 flex flex-wrap items-center justify-end gap-2 xl:hidden">
            {actions}
          </div>
        )}
      </>
    );
  }

  return (
    <>
      {slot && back &&
        createPortal(
          <div className="flex min-w-0 flex-1 items-center gap-2.5">
            <Link
              to={back.to}
              className="inline-flex h-8 shrink-0 items-center gap-1 rounded-lg border border-border bg-subtle/70 px-2.5 text-xs font-medium text-fg-muted transition-colors hover:border-border-strong hover:bg-subtle hover:text-fg"
              title={`Quay lại ${back.label}`}
            >
              <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
              <span>{back.label}</span>
            </Link>
            <span className="text-fg-subtle" aria-hidden>
              /
            </span>
            <span className="truncate text-xs font-medium text-fg-muted">Chi tiết</span>
          </div>,
          slot,
        )}
      <div className="mb-5 rounded-xl border border-border/80 bg-surface px-5 py-4 shadow-2xs">
        {!slot && back && (
          <Link
            to={back.to}
            className="mb-2 inline-flex items-center gap-1 rounded text-[0.8125rem] font-medium text-fg-muted hover:text-accent"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden />
            {back.label}
          </Link>
        )}
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-lg font-bold tracking-tight text-fg sm:text-xl leading-snug">
                {title}
              </h1>
              {meta && <div className="flex flex-wrap items-center gap-2">{meta}</div>}
            </div>
            {description && <div className="mt-2 text-xs text-fg-muted sm:text-sm">{description}</div>}
          </div>
          {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
        </div>
      </div>
    </>
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
