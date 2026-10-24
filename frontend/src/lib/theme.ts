import { useCallback, useEffect, useState } from 'react';

export type ThemeMode = 'light' | 'dark';
const KEY = 'mf-theme';

function currentMode(): ThemeMode {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

/** Chế độ sáng/tối; trạng thái ban đầu do public/theme-init.js đặt trước khi render. */
export function useTheme(): { mode: ThemeMode; toggle: () => void } {
  const [mode, setMode] = useState<ThemeMode>(currentMode);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', mode === 'dark');
  }, [mode]);

  const toggle = useCallback(() => {
    setMode((m) => {
      const next = m === 'dark' ? 'light' : 'dark';
      try {
        localStorage.setItem(KEY, next);
      } catch {
        /* bỏ qua */
      }
      return next;
    });
  }, []);

  return { mode, toggle };
}
