import React, { useState, useEffect } from 'react';
import { Server, Loader2, CheckCircle2, X, CloudLightning } from 'lucide-react';
import { subscribeServerAwakening, ServerAwakeningStatus } from '../services/api';

export const ServerAwakeningIndicator: React.FC = () => {
  const [status, setStatus] = useState<ServerAwakeningStatus>({
    isWakingUp: false,
    elapsedSeconds: 0,
  });
  const [showSuccess, setShowSuccess] = useState<boolean>(false);
  const [isDismissed, setIsDismissed] = useState<boolean>(false);

  useEffect(() => {
    let successTimer: any = null;

    const unsubscribe = subscribeServerAwakening((newStatus) => {
      setStatus((prev) => {
        // Nếu chuyển từ isWakingUp = true sang false, hiển thị banner thành công trong 2.5s
        if (prev.isWakingUp && !newStatus.isWakingUp) {
          setShowSuccess(true);
          if (successTimer) clearTimeout(successTimer);
          successTimer = setTimeout(() => {
            setShowSuccess(false);
          }, 2500);
        }
        if (newStatus.isWakingUp) {
          setIsDismissed(false); // Reset trạng thái đóng khi có cold start mới
        }
        return newStatus;
      });
    });

    return () => {
      unsubscribe();
      if (successTimer) clearTimeout(successTimer);
    };
  }, []);

  // Không hiển thị nếu không đánh thức và không trong trạng thái hiển thị thành công
  if ((!status.isWakingUp && !showSuccess) || isDismissed) {
    return null;
  }

  const progressPercent = Math.min(95, Math.max(10, Math.round((status.elapsedSeconds / 50) * 100)));

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50 max-w-xl w-[92vw] sm:w-auto animate-in fade-in slide-in-from-top-4 duration-300"
    >
      {showSuccess ? (
        <div className="bg-emerald-950/90 text-emerald-100 border border-emerald-500/40 shadow-2xl backdrop-blur-md rounded-2xl px-5 py-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-emerald-500/20 flex items-center justify-center shrink-0 border border-emerald-500/30">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <div className="text-sm font-bold text-white flex items-center gap-1.5">
              <span>Máy chủ đã sẵn sàng!</span>
            </div>
            <div className="text-xs text-emerald-200/80">
              Kết nối backend (Render) đã được thiết lập thành công.
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900/95 text-slate-100 border border-amber-500/40 shadow-2xl backdrop-blur-md rounded-2xl p-4 sm:px-5 sm:py-3.5 flex flex-col gap-2.5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="relative w-9 h-9 rounded-xl bg-amber-500/20 flex items-center justify-center shrink-0 border border-amber-500/30">
                <Server className="w-4 h-4 text-amber-400" />
                <span className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
                </span>
              </div>
              <div>
                <div className="text-sm font-bold text-white flex items-center gap-2">
                  <span>Máy chủ đang thức dậy...</span>
                  <span className="text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                    <Loader2 className="w-3 h-3 animate-spin text-amber-400" />
                    <span>{status.elapsedSeconds}s / ~50s</span>
                  </span>
                </div>
                <div className="text-xs text-slate-300 flex items-center gap-1 mt-0.5">
                  <CloudLightning className="w-3 h-3 text-amber-400 shrink-0" />
                  <span>Render Cloud đang khởi động container từ chế độ ngủ đông.</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => setIsDismissed(true)}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              aria-label="Thu nhỏ thông báo"
              title="Thu nhỏ thông báo"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-gradient-to-r from-amber-500 to-indigo-500 h-full rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <div className="text-[11px] text-slate-400 text-center sm:text-left">
            Vui lòng không tải lại trang. Hệ thống sẽ tự động cập nhật ngay khi máy chủ trực tuyến.
          </div>
        </div>
      )}
    </div>
  );
};
