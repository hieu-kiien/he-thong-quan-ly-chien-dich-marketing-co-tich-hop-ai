import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
  title?: string;
  duration?: number;
}

interface ToastContextType {
  showToast: (type: ToastType, message: string, title?: string, duration?: number) => void;
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
  warning: (message: string, title?: string) => void;
  info: (message: string, title?: string) => void;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback(
    (type: ToastType, message: string, title?: string, duration = 4000) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const newToast: ToastItem = { id, type, message, title, duration };

      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    [removeToast]
  );

  const success = useCallback(
    (message: string, title?: string) => showToast('success', message, title),
    [showToast]
  );

  const error = useCallback(
    (message: string, title?: string) => showToast('error', message, title || 'Có lỗi xảy ra'),
    [showToast]
  );

  const warning = useCallback(
    (message: string, title?: string) => showToast('warning', message, title || 'Cảnh báo'),
    [showToast]
  );

  const info = useCallback(
    (message: string, title?: string) => showToast('info', message, title || 'Thông báo'),
    [showToast]
  );

  return (
    <ToastContext.Provider value={{ showToast, success, error, warning, info, removeToast }}>
      {children}
      {/* Toast Notification Floating Container */}
      <div className="fixed top-5 right-5 z-[9999] flex flex-col gap-2.5 max-w-sm w-full pointer-events-none px-4 sm:px-0">
        {toasts.map((toast) => {
          let bgClass = 'bg-white border-slate-200 text-slate-900';
          let icon = <Info className="w-4 h-4 text-blue-500 shrink-0" />;

          switch (toast.type) {
            case 'success':
              bgClass = 'bg-emerald-50 border-emerald-200 text-emerald-900';
              icon = <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />;
              break;
            case 'error':
              bgClass = 'bg-rose-50 border-rose-200 text-rose-900';
              icon = <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />;
              break;
            case 'warning':
              bgClass = 'bg-amber-50 border-amber-200 text-amber-900';
              icon = <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />;
              break;
            case 'info':
              bgClass = 'bg-indigo-50 border-indigo-200 text-indigo-900';
              icon = <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />;
              break;
          }

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto border rounded-xl p-3.5 shadow-lg flex items-start gap-3 transition-all duration-200 ${bgClass}`}
            >
              {icon}
              <div className="flex-1 min-w-0">
                {toast.title && (
                  <h5 className="text-xs font-bold leading-tight mb-0.5">
                    {toast.title}
                  </h5>
                )}
                <p className="text-xs leading-relaxed break-words font-medium opacity-90">
                  {toast.message}
                </p>
              </div>
              <button
                onClick={() => removeToast(toast.id)}
                className="p-1 rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 transition-colors shrink-0"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};
