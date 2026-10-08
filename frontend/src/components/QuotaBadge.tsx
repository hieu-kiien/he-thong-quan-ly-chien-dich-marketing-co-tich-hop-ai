import React, { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Gauge, RefreshCw } from 'lucide-react';
import type { QuotaErrorDetail, QuotaLimitItem, QuotaSnapshot } from '../types';
import { describeQuotaReset, getQuotaError, quotaApi } from '../services/api';

/**
 * Hiển thị hạn mức gói miễn phí: thanh tiến trình đã dùng / trần, và đồng hồ đếm
 * ngược tới lúc hết hạn.
 *
 * VÌ SAO CẦN THẤY TRƯỚC
 * ---------------------
Một hạn mứng chỉ báo lỗi khi đã vượt thì người dùng chỉ biết sau khi thao tác
đã thất bại — đúng trải nghiệm tệ nhất. Ở đây người dùng thấy "còn 8/50 AI job"
trước khi bấm, nên biết mình sắp chạm trần. Đây là lớp HIỂN THỊ; hạn mứng thật
vẫn thực thi ở server (xem `app/services/quota.py`).
 */
export interface QuotaBadgeProps {
  workspaceId: number | null | undefined;
  /** Chỉ hiện các hạn mức này. Rỗng = mặc định `ai_jobs_per_day` + `campaigns`. */
  limitCodes?: string[];
  /** Làm mới mỗi N giây. `0` = không tự làm mới. */
  refreshSeconds?: number;
  className?: string;
}

const DEFAULT_CODES = ['ai_jobs_per_day', 'campaigns'];

/** Ngưỡng coi là "sắp chạm trần" để đổi màu cảnh báo. */
const NEAR_LIMIT_RATIO = 0.8;

const resolveLimit = (snapshot: QuotaSnapshot | null, code: string): QuotaLimitItem | null =>
  snapshot?.limits?.find((item) => item.limit_code === code) || null;

const ratio = (item: QuotaLimitItem): number => {
  if (item.limit <= 0) return 1;
  return Math.min(1, item.used / item.limit);
};

const barColor = (item: QuotaLimitItem): string => {
  if (item.exceeded) return 'bg-red-600';
  if (ratio(item) >= NEAR_LIMIT_RATIO) return 'bg-amber-500';
  return 'bg-indigo-600';
};

export const QuotaBadge: React.FC<QuotaBadgeProps> = ({
  workspaceId,
  limitCodes = DEFAULT_CODES,
  refreshSeconds = 60,
  className = '',
}) => {
  const [snapshot, setSnapshot] = useState<QuotaSnapshot | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!workspaceId) {
      setSnapshot(null);
      return;
    }
    setLoading(true);
    try {
      setSnapshot(await quotaApi.get(workspaceId));
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void load();
    if (!refreshSeconds || !workspaceId) return undefined;
    const timer = window.setInterval(() => void load(), refreshSeconds * 1000);
    return () => window.clearInterval(timer);
  }, [load, refreshSeconds, workspaceId]);

  const items = (snapshot?.limits || [])
    .filter((item) => limitCodes.includes(item.limit_code))
    .map((item) => resolveLimit(snapshot!, item.limit_code))
    .filter((item): item is QuotaLimitItem => item !== null);

  // Không có workspace hoặc endpoint lỗi thì không render gì: màn hình vẫn dùng
  // được bình thường, chỉ mất phần báo trước.
  if (!workspaceId || items.length === 0) return null;

  return (
    <section
      data-testid="quota-badge"
      aria-label="Hạn mức gói miễn phí"
      className={`rounded-xl border border-slate-200 bg-white p-3 ${className}`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
          <Gauge className="h-3.5 w-3.5" aria-hidden="true" />
          Hạn mức gói miễn phí
        </h3>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          aria-label="Làm mới hạn mức"
          className="rounded p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
        </button>
      </div>

      <ul className="space-y-2.5">
        {items.map((item) => (
          <li key={item.limit_code} data-testid={`quota-row-${item.limit_code}`}>
            <div className="mb-1 flex items-baseline justify-between gap-2 text-xs">
              <span className="font-medium text-slate-700">
                {item.label}
                {item.window ? ` / ${item.window}` : ''}
              </span>
              <span
                className={`tabular-nums font-semibold ${
                  item.exceeded ? 'text-red-700' : ratio(item) >= NEAR_LIMIT_RATIO ? 'text-amber-700' : 'text-slate-600'
                }`}
              >
                {item.used}/{item.limit}
              </span>
            </div>
            <div
              className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200"
              role="progressbar"
              aria-valuenow={item.used}
              aria-valuemin={0}
              aria-valuemax={item.limit}
              aria-label={`${item.label}: ${item.used}/${item.limit}`}
            >
              <div className={`h-full rounded-full ${barColor(item)}`} style={{ width: `${ratio(item) * 100}%` }} />
            </div>
            <p className="mt-1 text-[11px] text-slate-500" data-testid={`quota-reset-${item.limit_code}`}>
              {item.exceeded
                ? 'Đã hết hạn mức'
                : item.resets_at
                  ? `Đặt lại ${describeQuotaReset(item.resets_at)}`
                  : 'Không tự đặt lại'}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
};

/**
 * Thẻ lỗi hạn mứng để nhúng cạnh nút bấm.
 *
 * Nói rõ vì sao bị chặn, đã dùng bao nhiêu, còn bao nhiêu, và bao giờ hết hạn —
 * thay vì để `getApiErrorMessage` rơi về `JSON.stringify` của cả object.
 */
export const QuotaErrorCard: React.FC<{ detail: QuotaErrorDetail }> = ({ detail }) => (
  <div
    role="alert"
    data-testid="quota-error"
    className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
  >
    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
    <div>
      <p className="font-medium">{detail.message}</p>
      <p className="mt-1 text-xs">
        Đã dùng {detail.used}/{detail.limit} — còn {detail.remaining} lượt.
        {detail.resets_at ? ` Hết hạn lúc ${new Date(detail.resets_at).toLocaleString('vi-VN')}.` : ' Hạn mức này không tự đặt lại.'}
      </p>
    </div>
  </div>
);

/** Hook tiện ích: bắt lỗi 429 hạn mứng từ bất kỳ lời gọi API nào. */
export const useQuotaError = (error: unknown): QuotaErrorDetail | null =>
  getQuotaError(error);

export default QuotaBadge;