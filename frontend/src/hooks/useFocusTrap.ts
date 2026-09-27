import { useEffect, useRef, useCallback } from 'react';

export interface UseFocusTrapOptions {
  isActive: boolean;
  onEscape?: () => void;
  restoreFocus?: boolean;
  autoFocus?: boolean;
}

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

/**
 * Hook to manage WCAG 2.1 / 2.2 AA compliant focus trap inside modals/dialogs.
 * - Traps Tab & Shift+Tab within the container element.
 * - Triggers onEscape when Escape key is pressed.
 * - Restores focus to the triggering element when closed.
 */
export function useFocusTrap<T extends HTMLElement = HTMLDivElement>({
  isActive,
  onEscape,
  restoreFocus = true,
  autoFocus = true,
}: UseFocusTrapOptions) {
  const containerRef = useRef<T | null>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  // Capture triggering element when trap activates, restore on deactivate
  useEffect(() => {
    if (isActive) {
      previousActiveElementRef.current = document.activeElement as HTMLElement | null;
    } else if (restoreFocus && previousActiveElementRef.current && typeof previousActiveElementRef.current.focus === 'function') {
      const el = previousActiveElementRef.current;
      setTimeout(() => {
        el.focus();
      }, 10);
    }
  }, [isActive, restoreFocus]);

  // Focus the first focusable element upon activation
  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    if (autoFocus) {
      const focusableElements = containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      const autoFocusTarget = containerRef.current.querySelector<HTMLElement>('[autofocus], [data-autofocus]');
      const target = autoFocusTarget || focusableElements[0];
      if (target) {
        // Use timeout to ensure DOM is rendered and accessible
        const timer = setTimeout(() => {
          target.focus();
        }, 30);
        return () => clearTimeout(timer);
      } else {
        containerRef.current.focus();
      }
    }
  }, [isActive, autoFocus]);

  // Restore focus on unmount
  useEffect(() => {
    return () => {
      if (restoreFocus && previousActiveElementRef.current && typeof previousActiveElementRef.current.focus === 'function') {
        previousActiveElementRef.current.focus();
      }
    };
  }, [restoreFocus]);

  // Handle Tab trapping and Escape
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isActive || !containerRef.current) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        if (restoreFocus && previousActiveElementRef.current && typeof previousActiveElementRef.current.focus === 'function') {
          previousActiveElementRef.current.focus();
        }
        if (onEscape) {
          onEscape();
        }
        return;
      }

      if (e.key === 'Tab') {
        const focusable = Array.from(
          containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
        ).filter(el => el.offsetParent !== null); // only visible elements

        if (focusable.length === 0) {
          e.preventDefault();
          return;
        }

        const firstElement = focusable[0];
        const lastElement = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement || !containerRef.current.contains(document.activeElement)) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement || !containerRef.current.contains(document.activeElement)) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    },
    [isActive, onEscape]
  );

  useEffect(() => {
    if (!isActive) {
      if (restoreFocus && previousActiveElementRef.current && typeof previousActiveElementRef.current.focus === 'function') {
        previousActiveElementRef.current.focus();
        previousActiveElementRef.current = null;
      }
      return;
    }

    document.addEventListener('keydown', handleKeyDown, true);
    return () => {
      document.removeEventListener('keydown', handleKeyDown, true);
    };
  }, [isActive, handleKeyDown, restoreFocus]);

  return containerRef;
}

export default useFocusTrap;
