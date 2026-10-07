import { useCallback, useEffect, useRef, useState } from 'react';

import {
  AIJobError,
  AIJobCreateRequest,
  AIJobPhase,
  AIJobTask,
  AIJobTaskUpdate,
  AIJobTransport,
  createAIJobTask,
  describeAIJobFailure,
} from '../services/aiJobPoller';
import { aiJobTransport } from '../services/api';

/**
 * Hook bọc `createAIJobTask` thành state cho React.
 *
 * BA VIỆC MÀ HOOK NÀY LO, ĐỀU LÀ BẮT BUỘC VỚI MỘT LẦN CHỜ DÀI:
 *
 * 1. **Đồng hồ đếm ngược.** Job thật mất vài phút. Người dùng cần thấy thời
 *    gian đã trôi qua và còn bao lâu nữa thì hết hạn; một vòng quay tròn trống
 *    trong bốn phút đọc như phần mềm vừa treo.
 * 2. **Dọn timer khi rời trang.** `useEffect` cleanup gọi `dispose()`. Không có
 *    nó thì timer của `createAIJobTask` còn sống, giữ closure trong bộ nhớ và
 *    đồng thời `setState` vào component đã bị React tháo.
 * 3. **Không nuốt lỗi.** `run()` luôn trả `AIJobError` có `kind` phân loại và
 *    `backendReason` nguyên văn từ server. Không có đường nào biến lỗi thành
 *    kết quả rỗng, và kết quả rỗng cũng không được trình bày như nội dung AI.
 */
export interface UseAIJobResult {
  phase: AIJobPhase;
  /** Đang chờ kết quả (kể cả lúc huỷ đang bay về server). */
  busy: boolean;
  jobId: number | null;
  status: string | null;
  elapsedMs: number;
  /** Còn bao lâu thì hết hạn chờ. `null` khi không chờ. */
  remainingMs: number | null;
  attempts: number;
  maxAttempts: number;
  retries: number;
  requeued: boolean;
  backendReason: string | null;
  cancelRejectedReason: string | null;
  error: AIJobError | null;
  errorTitle: string | null;
  errorHint: string | null;
  /** Có nên gợi ý thử lại không (lỗi tạm thời thì có, hết hạn mức thì không). */
  errorRetryable: boolean;
  /**
   * Chạy một tác vụ AI và trả kết quả, hoặc ném `AIJobError` đã phân loại.
   *
   * Kiểu trả về KHÔNG phải `T | null`: một kết quả rỗng/null từ hàng đợi là
   * tình huống bất thường đã được poller tự ném lỗi. Cho phép `null` lọt qua
   * chính là đường để lỗi biến thành nội dung rỗng bị trình bày như kết quả thật.
   */
  run: <T = Record<string, unknown>>(request: AIJobCreateRequest) => Promise<T>;
  cancel: () => void;
  reset: () => void;
}

const IDLE_UPDATE: AIJobTaskUpdate = {
  phase: 'idle',
  jobId: null,
  status: null,
  elapsedMs: 0,
  attempts: 0,
  maxAttempts: 0,
  retries: 0,
  error: null,
  requeued: false,
  backendReason: null,
  cancelRejectedReason: null,
};

/** Lịch bơm thời gian cho phần đồng hồ, tách khỏi scheduler của poller. */
const startTicker = (onTick: () => void): (() => void) => {
  const handle = setInterval(onTick, 250);
  return () => clearInterval(handle);
};

export const useAIJob = (
  transport: AIJobTransport = aiJobTransport,
  deadlineMs?: number,
): UseAIJobResult => {
  const [update, setUpdate] = useState<AIJobTaskUpdate>(IDLE_UPDATE);
  const taskRef = useRef<AIJobTask | null>(null);
  const disposedRef = useRef(false);

  if (!taskRef.current) {
    taskRef.current = createAIJobTask(transport, {
      ...(deadlineMs !== undefined ? { deadlineMs } : {}),
      onUpdate: (next) => {
        // `dispose()` có thể chạy trước khi React tháo effect; bỏ qua để không
        // setState vào cây component đã ngừng.
        if (disposedRef.current) return;
        setUpdate(next);
      },
    });
  }

  useEffect(() => {
    disposedRef.current = false;
    return () => {
      disposedRef.current = true;
      taskRef.current?.dispose();
    };
  }, []);

  const busy = update.phase === 'enqueuing' || update.phase === 'queued' || update.phase === 'running';

  // Đồng hồ đếm ngược: chỉ chạy khi đang chờ, và luôn được dọn khi hết việc.
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!busy) return undefined;
    return startTicker(() => setTick((n) => n + 1));
  }, [busy]);

  const run = useCallback(
    async <T,>(request: AIJobCreateRequest): Promise<T> => {
      const task = taskRef.current;
      if (!task) {
        throw new AIJobError('Tác vụ chưa sẵn sàng.', { kind: 'unknown' });
      }
      // Lỗi từ `createAIJobTask` đã là `AIJobError` có `kind` + `backendReason`;
      // ném nguyên vẹn lên để tầng gọi hiển thị đúng loại, không bọc lại thành
      // thông báo chung chung.
      return (await task.run(request)) as T;
    },
    [],
  );

  const cancel = useCallback(() => taskRef.current?.cancel(), []);
  const reset = useCallback(() => setUpdate(IDLE_UPDATE), []);

  const description = update.error ? describeAIJobFailure(update.error.kind) : null;

  return {
    phase: update.phase,
    busy,
    jobId: update.jobId,
    status: update.status,
    elapsedMs: update.elapsedMs,
    remainingMs: busy && deadlineMs ? Math.max(0, deadlineMs - update.elapsedMs) : null,
    attempts: update.attempts,
    maxAttempts: update.maxAttempts,
    retries: update.retries,
    requeued: update.requeued,
    backendReason: update.backendReason,
    cancelRejectedReason: update.cancelRejectedReason,
    error: update.error,
    errorTitle: description?.title ?? null,
    errorHint: description?.hint ?? null,
    errorRetryable: description?.retryable ?? false,
    run,
    cancel,
    reset,
  };
};

/** Định dạng thời gian chờ dạng `m:ss` — ngắn gọn để đọc trong khi chờ. */
export const formatElapsed = (ms: number): string => {
  const total = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
};