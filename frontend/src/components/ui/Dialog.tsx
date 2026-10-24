import { useId, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { cn } from '@/lib/cn';
import { IconButton } from './Button';
import { useFocusTrap } from './useFocusTrap';

interface OverlayBaseProps {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  /** Vùng nút hành động ở chân. */
  footer?: ReactNode;
  /** Không cho đóng bằng Esc/click nền (vd đang gửi). */
  dismissable?: boolean;
}

export interface DialogProps extends OverlayBaseProps {
  size?: 'sm' | 'md' | 'lg';
}

const dialogSizes = { sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-3xl' };

/** Hộp thoại modal: role=dialog, focus trap, Esc để đóng. */
export function Dialog({ open, onClose, title, description, children, footer, size = 'md', dismissable = true }: DialogProps) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descId = useId();
  useFocusTrap(ref, open, dismissable ? onClose : undefined);
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:items-center">
      <div
        className="fixed inset-0 animate-fade-in bg-stone-950/40"
        aria-hidden
        onClick={dismissable ? onClose : undefined}
      />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        tabIndex={-1}
        className={cn(
          'relative my-8 w-full animate-scale-in rounded-lg border border-border bg-surface shadow-overlay',
          dialogSizes[size],
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div className="min-w-0">
            <h2 id={titleId} className="text-base font-semibold text-fg">
              {title}
            </h2>
            {description && (
              <p id={descId} className="mt-1 text-sm text-fg-muted">
                {description}
              </p>
            )}
          </div>
          {dismissable && (
            <IconButton label="Đóng" size="sm" onClick={onClose} className="-mr-1.5 -mt-1">
              <X className="h-4 w-4" />
            </IconButton>
          )}
        </div>
        {children && <div className="px-5 py-4">{children}</div>}
        {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-border px-5 py-3">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}

export interface DrawerProps extends OverlayBaseProps {
  width?: 'md' | 'lg' | 'xl';
}

const drawerWidths = { md: 'max-w-md', lg: 'max-w-2xl', xl: 'max-w-4xl' };

/** Ngăn kéo bên phải cho form dài (tạo/sửa). */
export function Drawer({ open, onClose, title, description, children, footer, width = 'lg', dismissable = true }: DrawerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useFocusTrap(ref, open, dismissable ? onClose : undefined);
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="fixed inset-0 animate-fade-in bg-stone-950/40"
        aria-hidden
        onClick={dismissable ? onClose : undefined}
      />
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          'relative flex h-full w-full animate-slide-in-right flex-col border-l border-border bg-surface shadow-overlay',
          drawerWidths[width],
        )}
      >
        <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-4">
          <div className="min-w-0">
            <h2 id={titleId} className="text-base font-semibold text-fg">
              {title}
            </h2>
            {description && <p className="mt-1 text-sm text-fg-muted">{description}</p>}
          </div>
          {dismissable && (
            <IconButton label="Đóng" size="sm" onClick={onClose} className="-mr-1.5 -mt-1">
              <X className="h-4 w-4" />
            </IconButton>
          )}
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-border px-6 py-3">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}
