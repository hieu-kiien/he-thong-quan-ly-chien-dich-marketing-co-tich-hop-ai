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
 * Các handler phím đang hoạt động, theo thứ tự mở. Handler của hộp thoại mở
 * sau nằm cuối mảng và là hộp thoại "trên cùng" — chỉ nó được quyền xử lý
 * Escape/Tab khi nhiều hộp thoại lồng nhau.
 */
const trapStack: Array<(e: KeyboardEvent) => void> = [];

/** Lớp phủ nền của hộp thoại: `aria-hidden` + `position: fixed` phủ viewport. */
const isInteractiveOverlay = (el: HTMLElement): boolean => {
  if (!el.hasAttribute('aria-hidden')) return false;
  const cs = window.getComputedStyle(el);
  return cs.position === 'fixed' || cs.position === 'absolute';
};

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
    //
    // Ranh giới phải là CHÍNH hộp thoại (`role="dialog"` / `role="alertdialog"`
    // / `aria-modal`), không phải `container`. Nhiều màn hình đặt ref lên panel
    // trong khi thuộc tính role đặt trên lớp bọc ngoài một cấp; nếu leo từ
    // `container` thì vòng lặp đánh dấu `inert` luôn cả backdrop của hộp thoại
    // (nó là anh em của `container` dưới lớp bọc đó). `inert` khiến phần tử mất
    // khả năng hit-test lẫn bàn phím — click ra vùng ngoài và click backdrop
    // im lặng không làm gì, đúng triệu chứng đã gặp.
    const boundary: HTMLElement | null =
      container?.closest<HTMLElement>('[role="dialog"], [role="alertdialog"], [aria-modal="true"]') ??
      container;

    const inerted: HTMLElement[] = [];
    if (inertSiblings && boundary) {
      let node: HTMLElement | null = boundary;
      while (node?.parentElement) {
        const parent: HTMLElement = node.parentElement;
        for (const child of Array.from(parent.children) as HTMLElement[]) {
          if (child === node || child.contains(boundary)) continue;
          if (child.hasAttribute('inert')) continue;
          if (isAlwaysLive(child)) continue;
          // Lớp phủ nền tương tác được (backdrop) KHÔNG được inert. Cách nhận diện
          // theo đúng định nghĩa, không phụ thuộc vị trí cây DOM: nó là phần tử
          // `aria-hidden` + `position: fixed` phủ toàn viewport. Cần điều này vì
          // hai hộp thoại kiểm tra này đặt `role` khác nhau — Campaigns đặt
          // `role="dialog"` trên lớp bọc (backdrop nằm trong đó, được miễn khi
          // leo từ `role`), còn ReviewQueue đặt `role="alertdialog"` trên chính
          // panel nên backdrop lại nằm NGOÀI `role`. Inert làm mất hit-test, tức
          // là click ra ngoài im lặng không đóng hộp thoại.
          if (isInteractiveOverlay(child)) continue;
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

      // Chỉ hộp thoại trên cùng mới xử lý phím. Các handler đều đăng ký ở
      // `document` nên với hộp thoại lồng nhau (vd: modal sửa bài chứa hộp thoại
      // xác nhận Brand Safety) một lần Escape sẽ chạy mọi handler cùng lúc và
      // đóng cả hai, khiến người dùng mất luôn nội dung đang sửa. Đồng thời Tab
      // cũng bị hai hộp thoại cùng giành nhau và người dùng có thể tab ra
      // khỏi hộp thoại đang mở.
      if (trapStack[trapStack.length - 1] !== handleKeyDown) return;

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
    trapStack.push(handleKeyDown);
    document.addEventListener('keydown', handleKeyDown, true);
    return () => {
      const i = trapStack.indexOf(handleKeyDown);
      if (i !== -1) trapStack.splice(i, 1);
      document.removeEventListener('keydown', handleKeyDown, true);
    };
  }, [isActive, handleKeyDown]);

  return containerRef;
}

export default useFocusTrap;
