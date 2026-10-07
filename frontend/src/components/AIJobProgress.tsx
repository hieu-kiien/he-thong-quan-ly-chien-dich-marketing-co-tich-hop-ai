import React from 'react';
import { Clock, Loader2, ListOrdered, Ban, RotateCcw, AlertTriangle } from 'lucide-react';

import { formatElapsed } from '../hooks/useAIJob';
import type { UseAIJobResult } from '../hooks/useAIJob';

/**
 * Bảng trạng thái cho một lần chờ job AI.
 *
 * VÌ SAO CẦN CẢ MỘT BẢNG RIÊNG
 * -----------------------------
 * `/ai/omnichannel` đo mất 237 giây. Một vòng quay tròn trống suốt bốn phút đọc
 * như phần mềm vừa treo, và người dùng không có cách nào biết hệ thống còn làm
 * việc hay đã chết. Bảng này trả lời bốn câu hỏi liên tục trong lúc chờ:
 *   1. Việc này còn được chờ không?        -> phase
 *   2. Nó đang ở hàng hay đang chạy?      -> badge "Đang xếp hàng" / "Đang chạy"
 *   3. Đã chờ bao lâu, còn bao lâu nữa?   -> đồng hồ đã trôi + còn hạn
 *   4. Tôi có huỷ được không?              -> nút huỷ, kèm lý do khi không huỷ được
 *
 * Nút "Huỷ" KHÔNG chỉ dừng giao diện: nó gọi `POST /ai/jobs/{id}/cancel`. Khi
 * backend từ chối (HTTP 409 vì job đã `running` — Python không huỷ được thread
 * đang chạy), bảng hiện đúng lý do từ server thay vì báo đã huỷ.
 */
export interface AIJobProgressProps {
  job: UseAIJobResult;
  /** Nhãn việc đang làm, ví dụ "3 kênh đa kênh". */
  label: string;
  onRetry?: () => void;
  className?: string;
}

export const AIJobProgress: React.FC<AIJobProgressProps> = ({ job, label, onRetry, className = '' }) => {
  const { busy, phase } = job;

  if (!busy && phase !== 'failed' && phase !== 'cancelled') return null;

  if (busy) {
    const queued = phase === 'queued' || phase === 'enqueuing';
    return (
      <div
        role="status"
        aria-live="polite"
        data-testid="ai-job-progress"
        className={`rounded-xl border border-indigo-200 bg-indigo-50/70 p-4 space-y-3 ${className}`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            {queued ? (
              <ListOrdered className="w-4 h-4 text-indigo-600 shrink-0" />
            ) : (
              <Loader2 className="w-4 h-4 text-indigo-600 animate-spin shrink-0" />
            )}
            <div className="min-w-0">
              <p className="text-xs font-bold text-indigo-900 truncate">
                {queued ? `Đang xếp hàng: ${label}` : `AI đang tạo: ${label}`}
              </p>
              <p className="text-[11px] text-indigo-700 mt-0.5">
                {queued
                  ? 'Tác vụ đã vào hàng đợi. Hàng đợi chạy tối đa 2 tác vụ AI cùng lúc để không làm cạn máy chủ.'
                  : 'Máy chủ đang gọi nhà cung cấp AI. Việc này có thể mất vài phút — bạn có thể để ngang màn hình này, tác vụ vẫn chạy.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <div className="text-right">
              <p className="text-[11px] font-mono font-bold text-indigo-900" data-testid="ai-job-elapsed">
                {formatElapsed(job.elapsedMs)}
              </p>
              {job.remainingMs !== null && (
                <p className="text-[10px] font-mono text-indigo-600">
                  còn {formatElapsed(job.remainingMs)}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={job.cancel}
              className="text-[11px] font-bold text-slate-600 hover:text-rose-700 hover:bg-rose-50 border border-slate-300 hover:border-rose-300 px-2.5 py-1.5 rounded-lg flex items-center gap-1 transition-colors cursor-pointer"
            >
              <Ban className="w-3.5 h-3.5" />
              <span>Huỷ</span>
            </button>
          </div>
        </div>

        {job.retries > 0 && (
          <p className="text-[11px] text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5">
            Tác vụ gặp lỗi tạm thời và đang thử lại lần {job.attempts}/{job.maxAttempts}.
            {job.backendReason ? ` Lý do: ${job.backendReason}` : ''}
          </p>
        )}

        {job.cancelRejectedReason && (
          <p
            role="alert"
            data-testid="ai-job-cancel-rejected"
            className="text-[11px] text-amber-900 bg-amber-50 border border-amber-300 rounded-lg px-2.5 py-1.5"
          >
            Không huỷ được trên máy chủ: {job.cancelRejectedReason} Hệ thống vẫn chờ lấy kết quả để bạn không mất công đã chờ.
          </p>
        )}

        {/* Thanh tiến trình không có phần trăm thật — dùng thanh nhấp nháy để không
            bịa ra con số tiến độ mà backend không cung cấp. */}
        <div className="h-1.5 w-full bg-indigo-100 rounded-full overflow-hidden">
          <div className="h-full w-1/3 bg-indigo-500 rounded-full animate-pulse" />
        </div>
      </div>
    );
  }

  // phase === 'failed' hoặc 'cancelled'
  const cancelled = phase === 'cancelled';
  return (
    <div
      role="alert"
      data-testid="ai-job-error"
      className={`rounded-xl border p-4 space-y-2 ${
        cancelled ? 'border-slate-300 bg-slate-50' : 'border-rose-300 bg-rose-50'
      } ${className}`}
    >
      <div className="flex items-start gap-2">
        <AlertTriangle
          className={`w-4 h-4 shrink-0 mt-0.5 ${cancelled ? 'text-slate-500' : 'text-rose-600'}`}
        />
        <div className="min-w-0 flex-1">
          <p className={`text-xs font-bold ${cancelled ? 'text-slate-700' : 'text-rose-900'}`}>
            {cancelled ? 'Đã huỷ tác vụ' : (job.errorTitle ?? 'Tác vụ AI thất bại')}
          </p>
          {!cancelled && job.errorHint && (
            <p className="text-[11px] text-rose-800 mt-0.5">{job.errorHint}</p>
          )}
          {cancelled && (
            <p className="text-[11px] text-slate-600 mt-0.5">
              Tác vụ đã bị huỷ trước khi có kết quả. Không có nội dung nào được tạo ra.
            </p>
          )}
          {job.backendReason && (
            <p className="text-[11px] text-slate-600 mt-1.5 break-words">
              <span className="font-semibold">Thông báo từ máy chủ: </span>
              {job.backendReason}
            </p>
          )}
          {!cancelled && onRetry && job.errorRetryable && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 text-[11px] font-bold text-rose-700 hover:text-rose-900 bg-white border border-rose-300 hover:border-rose-400 px-2.5 py-1.5 rounded-lg flex items-center gap-1 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Thử lại</span>
            </button>
          )}
        </div>
      </div>
      {!cancelled && (
        <p className="text-[10px] text-rose-700 flex items-center gap-1">
          <Clock className="w-3 h-3" />
          <span>Đã chờ {formatElapsed(job.elapsedMs)} trước khi thất bại.</span>
        </p>
      )}
    </div>
  );
};