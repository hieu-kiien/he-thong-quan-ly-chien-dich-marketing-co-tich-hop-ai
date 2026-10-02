import { useEffect, useRef, useCallback } from 'react';

export interface UseFocusTrapOptions {
  isActive: boolean;
  onEscape?: () => void;
  restoreFocus?: boolean;
  autoFocus?: boolean;
  /** Khoá cuộn trang nền khi hộp thoại mở. Mặc định true. */
  lockScroll?: boolean;
  /** Đánh dấu `inert` lên các anh chị em của hộp thoại để trình đọc màn hình
   *  không còn bò tới nội dung phía sau. Mặc định true. */
  inertSiblings?: boolean;
}

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

const isFocusable = (el: HTMLElement | null): el is HTMLElement =>
  !!el && typeof el.focus === 'function';

/**
 * Vùng luôn phải "sống" kể cả khi hộp thoại đang mở. Không đánh dấu inert lên
 * chúng, nếu không toast thông báo sẽ không được trình đọc màn hình đọc tới
 * đúng lúc người dùng vừa thao tác trong modal.
 */
const ALWAYS_LIVE_SELECTOR =
  '[aria-live], [role="status"], [role="alert"], [role="log"], [data-focus-trap-exempt]';

const isAlwaysLive = (el: HTMLElement): boolean => el.matches(ALWAYS_LIVE_SELECTOR);

/**
 * Hook quản lý focus trap cho modal/dialog theo WCAG 2.1/2.2 AA.
 *
 * Ba lỗi đã sửa so với bản cũ:
 * 1. Khôi phục focus chạy tới 3 lần (mỗi effect một lần) và `setTimeout` không
 *    được huỷ → gọi `.focus()` sau khi component đã unmount.
 * 2. `useCallback` đọc `restoreFocus` bên trong nhưng không khai báo trong deps →
 *    stale closure.
 * 3. Không khoá scroll nền và không đánh dấu `inert`, nên trang phía sau vẫn
 *    cuộn được và trình đọc màn hình vẫn đọc tới.
 */
export function useFocusTrap<T extends HTMLElement = HTMLDivElement>({
  isActive,
  onEscape,
  restoreFocus = true,
  autoFocus = true,
  lockScroll = true,
  inertSiblings = true,
}: UseFocusTrapOptions) {
  const containerRef = useRef<T | null>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);
  const onEscapeRef = useRef<((() => void) | undefined)>(onEscape);
  onEscapeRef.current = onEscape;

  // Gom toàn bộ vòng đời (mở -> focus vào -> đóng -> trả focus) vào MỘT effect.
  useEffect(() => {
    if (!isActive) {
      return;
    }

    previousActiveElementRef.current = document.activeElement as HTMLElement | null;

    const container = containerRef.current;
    if (container && !container.hasAttribute('tabindex')) {
      // Không có phần tử nào focus được thì container.focus() là no-op; gán
      // tabindex=-1 để focus rơi vào chính hộp thoại thay vì để trả về body.
      container.setAttribute('tabindex', '-1');
    }

    let rafId: number | null = null;
    const focusTimer = window.setTimeout(() => {
      if (!containerRef.current) return;
      const preferred =
        containerRef.current.querySelector<HTMLElement>('[autofocus], [data-autofocus]') ??
        containerRef.current.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      (preferred ?? containerRef.current).focus();
    }, 30);

    // Khoá cuộn trang nền, giữ nguyên vị trí thanh cuộn.
    let previousOverflow: string | null = null;
    if (lockScroll) {
      previousOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      rafId = window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
        window.scrollTo(0, window.scrollY);
      }));
    }

    // `inert` cho mọi anh chị em của hộp thoại ở cấp <body>.
    const inerted: HTMLElement[] = [];
    if (inertSiblings && container) {
      let node: HTMLElement | null = container;
      while (node?.parentElement) {
        const parent: HTMLElement = node.parentElement;
        for (const child of Array.from(parent.children) as HTMLElement[]) {
          if (child === node || child.contains(container)) continue;
          if (child.hasAttribute('inert')) continue;
          if (isAlwaysLive(child)) continue;
          child.setAttribute('inert', '');
          inerted.push(child);
        }
        node = parent;
        if (parent === document.body) break;
      }
    }

    return () => {
      window.clearTimeout(focusTimer);
      if (rafId !== null) window.cancelAnimationFrame(rafId);
      if (lockScroll) {
        document.body.style.overflow = previousOverflow ?? '';
      }
      inerted.forEach((el) => el.removeAttribute('inert'));

      const el = previousActiveElementRef.current;
      previousActiveElementRef.current = null;
      if (restoreFocus && isFocusable(el) && document.body.contains(el)) {
        el.focus();
      }
    };
  }, [isActive, restoreFocus, autoFocus, lockScroll, inertSiblings]);

  // Tab / Shift+Tab chỉ bị chặn khi hộp thoại đang mở.
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isActive || !containerRef.current) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onEscapeRef.current?.();
        return;
      }

      if (e.key !== 'Tab') return;

      const focusable = Array.from(
        containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      ).filter((el) => el.offsetParent !== null);

      if (focusable.length === 0) {
        e.preventDefault();
        containerRef.current.focus();
        return;
      }

      const firstElement = focusable[0];
      const lastElement = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === firstElement || !containerRef.current.contains(document.activeElement)) {
          e.preventDefault();
          lastElement.focus();
        }
      } else if (document.activeElement === lastElement || !containerRef.current.contains(document.activeElement)) {
        e.preventDefault();
        firstElement.focus();
      }
    },
    [isActive]
  );

  useEffect(() => {
    if (!isActive) return;
    document.addEventListener('keydown', handleKeyDown, true);
    return () => {
      document.removeEventListener('keydown', handleKeyDown, true);
    };
  }, [isActive, handleKeyDown]);

  return containerRef;
}

export default useFocusTrap;
