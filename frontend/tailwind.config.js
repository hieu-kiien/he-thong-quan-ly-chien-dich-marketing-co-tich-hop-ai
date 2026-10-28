/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  // Dark mode do ứng dụng quyết định (nút chuyển ở Topbar, lưu localStorage).
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'Be Vietnam Pro'", "'Plus Jakarta Sans'", 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        body: ["'Plus Jakarta Sans'", "'Be Vietnam Pro'", 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ["'JetBrains Mono'", 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      colors: {
        // Màu ngữ nghĩa theo Design System "Soft Daylight", giá trị nằm trong src/index.css (sáng/tối).
        canvas: token('canvas'),
        surface: token('surface'),
        'ai-panel': token('ai-panel'),
        subtle: token('subtle'),
        muted: token('muted'),
        border: token('border'),
        'border-strong': token('border-strong'),
        fg: token('fg'),
        'fg-muted': token('fg-muted'),
        'fg-subtle': token('fg-subtle'),
        accent: {
          DEFAULT: token('accent'),
          hover: token('accent-hover'),
          fg: token('accent-fg'),
          soft: token('accent-soft'),
          'soft-fg': token('accent-soft-fg'),
        },
        ai: {
          DEFAULT: token('ai'),
          hover: token('ai-hover'),
          fg: token('ai-fg'),
          soft: token('ai-soft'),
          'soft-fg': token('ai-soft-fg'),
        },
        danger: { DEFAULT: token('danger'), soft: token('danger-soft'), 'soft-fg': token('danger-soft-fg') },
        warning: { DEFAULT: token('warning'), soft: token('warning-soft'), 'soft-fg': token('warning-soft-fg') },
        success: { DEFAULT: token('success'), soft: token('success-soft'), 'soft-fg': token('success-soft-fg') },
        info: { DEFAULT: token('info'), soft: token('info-soft'), 'soft-fg': token('info-soft-fg') },
      },
      borderRadius: {
        DEFAULT: '0.375rem',
      },
      boxShadow: {
        overlay: '0 10px 30px -10px rgb(28 25 23 / 0.25), 0 2px 6px -2px rgb(28 25 23 / 0.12)',
      },
      keyframes: {
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        'slide-in-right': { from: { transform: 'translateX(16px)', opacity: '0' }, to: { transform: 'none', opacity: '1' } },
        'scale-in': { from: { transform: 'scale(0.98)', opacity: '0' }, to: { transform: 'none', opacity: '1' } },
      },
      animation: {
        'fade-in': 'fade-in 150ms ease-out',
        'slide-in-right': 'slide-in-right 180ms ease-out',
        'scale-in': 'scale-in 150ms ease-out',
      },
    },
  },
  plugins: [],
};
