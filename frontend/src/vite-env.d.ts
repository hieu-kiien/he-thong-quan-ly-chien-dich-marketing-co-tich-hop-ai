/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  /** Chỉ hiển thị khi chạy dev (`import.meta.env.DEV`). */
  readonly VITE_DEV_LOGIN_HINT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
