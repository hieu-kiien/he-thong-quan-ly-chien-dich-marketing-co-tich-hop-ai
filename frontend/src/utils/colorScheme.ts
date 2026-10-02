import { useCallback, useEffect, useState } from 'react';

export type ColorScheme = 'light' | 'dark';

const STORAGE_KEY = 'mf_color_scheme';
const EVENT = 'mf:color-scheme-changed';

/**
 * Mặc định LUÔN là sáng.
 *
 * Vì sao không bám theo hệ điều hành: ứng dụng được thiết kế cho nền sáng
 * (khung ngoài `bg-[#F8FAFC]`, sidebar tối). Trước đây Tailwind mặc định
 * `prefers-color-scheme` nên trên máy bật chế độ tối, khoảng 6 component dùng
 * tiền tố `dark:` sẽ tự tối hoá (thẻ KPI, biểu đồ, banner) trong khi phần còn
 * lại vẫn sáng — tương phản không đọc được, màu chữ biến mất. Người dùng cũng
 * không có cách nào ép lại sáng.
 *
 * Nay `tailwind.config.js` đặt `darkMode: 'class'` và ứng dụng tự quyết định:
 * sáng mặc định, tối chỉ khi người dùng chủ động chọn (lưu lại để nhớ).
 */
function readScheme(): ColorScheme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'dark' || stored === 'light') return stored;
  } catch {
    // localStorage bị chặn (chế độ riêng tư) -> dùng mặc định bên dưới.
  }
  return 'light';
}

function applyScheme(scheme: ColorScheme): void {
  const root = document.documentElement;
  root.classList.toggle('dark', scheme === 'dark');
  // `color-scheme` khiến các control gốc của trình duyệt (scrollbar, form
  // control) cũng đổi theo, tránh nền trắng lọt vào vùng tối.
  root.style.colorScheme = scheme;
}

export function initializeColorScheme(): void {
  applyScheme(readScheme());
}

export function useColorScheme(): { scheme: ColorScheme; toggle: () => void } {
  const [scheme, setScheme] = useState<ColorScheme>(() =>
    typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
      ? 'dark'
      : readScheme()
  );

  useEffect(() => {
    const onChange = () => {
      setScheme(readScheme());
    };
    window.addEventListener(EVENT, onChange);
    // Đồng bộ nếu một tab khác đổi giao diện.
    window.addEventListener('storage', onChange);
    return () => {
      window.removeEventListener(EVENT, onChange);
      window.removeEventListener('storage', onChange);
    };
  }, []);

  const toggle = useCallback(() => {
    setScheme((prev) => {
      const next: ColorScheme = prev === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {
        // Không lưu được vẫn áp dụng cho phiên hiện tại.
      }
      applyScheme(next);
      window.dispatchEvent(new CustomEvent(EVENT, { detail: next }));
      return next;
    });
  }, []);

  return { scheme, toggle };
}
