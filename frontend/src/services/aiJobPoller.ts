/**
 * Lớp polling cho hàng đợi AI bất đồng bộ (backend `app/api/v1/ai_jobs.py`).
 *
 * VÌ SAO CÓ FILE NÀY
 * -----------------
 * Endpoint AI đồng bộ cũ giữ một thread của worker suốt thời gian chờ LLM:
 * `/ai/omnichannel` đo được 237 giây trên Render free, còn Cloudflare Worker
 * phía trước cắt ở ~100 giây và trả `error code: 524`. Hàng đợi mới sửa đúng
 * chỗ đó: `POST /ai/jobs` trả 202 ngay, `GET /ai/jobs/{id}` thăm dò kết quả.
 * File này bọc hai endpoint đó thành một lời gọi duy nhất "enqueue rồi chờ".
 *
 * NGUYÊN TẮC THIẾT KẾ (những điều này là lý do tồn tại của helper)
 * --------------------------------------------------------------
 * 1. SAI LẦM VỀ TRẠNG THÁI LÀ THẢM HỌA. Ba trạng thái kết thúc (`succeeded`,
 *    `failed`, `cancelled`) phải dừng vòng lặp. `cancelled` KHÔNG phải lỗi
 *    mạng và không được báo như lỗi.
 * 2. HẠN CHẾT. `deadlineMs` là mốc chặn cuối ở phía client: quá hạn thì dừng
 *    chờ và báo đúng là HẾT THỜI GIAN CHỜ, khác hẳn với job backend báo `failed`
 *    với lý do `TIMEOUT`. Hai sự thật khác nhau, không được trộn.
 * 3. BACKOFF. Job thật mất hàng phút. Thăm dò 1 giây/lần là spam không mục
 *    đích; lịch thăm dò tăng dần và có trần.
 * 4. DỌN TIMER. `dispose()` phải xoá đúng timer đang chờ. Điều hướng đi mất thì
 *    timer còn treo sẽ giữ closure (và cả `AIJobTask`) trong bộ nhớ, đồng thời
 *    gọi tiếp `setState` trên component đã bị tháo.
 * 5. MỘT LƯỢT, MỘT JOB. `run()` khi đang chạy trả lại ĐÚNG promise đang chờ,
 *    không enqueue lần hai. Đây là lớp phòng thủ phía client cho double-click;
 *    `idempotency_key` của backend là lớp phòng thủ thứ hai.
 *
 * FILE NÀY CỐ TÌNH KHÔNG IMPORT GÌ
 * -------------------------------
 * Không import axios, không import `api.ts`, không đụng `import.meta`. Nhờ vậy
 * test Playwright import trực tiếp module này trong Node và điều khiển đồng
 * hồ bằng lịch bơm vào — không bao giờ gọi mạng thật, không bao giờ gọi AI thật.
 */

export type AIJobKind = 'ideas' | 'draft' | 'summary' | 'omnichannel';

export type AIJobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';

/** Trạng thái mà tầng UI dùng. `enqueuing` là trạng thái phía client, backend không có. */
export type AIJobPhase =
  | 'idle'
  | 'enqueuing'
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled';

export type AIJobFailureKind =
  | 'timeout'
  | 'rate_limit'
  | 'provider_outage'
  | 'quota'
  | 'validation'
  | 'cancelled'
  | 'conflict'
  | 'unauthorized'
  | 'network'
  | 'unknown';

/** Thân `POST /ai/jobs`. Field nào không gửi thì backend bỏ qua (mặc định đồng bộ vẫn có hiệu lực). */
export interface AIJobCreateRequest {
  kind: AIJobKind;
  idempotency_key?: string;
  // ideas
  custom_topic?: string;
  custom_product?: string;
  custom_usp?: string;
  channel_code?: string;
  tone?: string;
  // draft
  selected_idea?: string;
  // summary
  // omnichannel
  brief?: string;
  target_audience?: string;
  channels?: string[];
  brand_kit_id?: number;
  product_name?: string;
  product_usp?: string;
  // chung
  campaign_id?: number;
  prompt_version?: string;
}

/** Phản hồi 202 của `POST /ai/jobs` (và của `POST /ai/jobs/{id}/cancel`). */
export interface AIJobAccepted {
  job_id: number;
  status: string;
  kind: string;
  deduplicated: boolean;
  poll_url: string;
}

/** Phản hồi của `GET /ai/jobs/{id}`. `result` chỉ có mặt khi job đã xong. */
export interface AIJobSnapshot {
  job_id: number;
  kind: string;
  status: AIJobStatus;
  attempts: number;
  max_attempts: number;
  campaign_id?: number | null;
  queued_at?: string | null;
  available_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  cancelled_at?: string | null;
  error?: string | null;
  result?: Record<string, unknown> | null;
}

export interface AIJobListResponse {
  items: Omit<AIJobSnapshot, 'result'>[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

/** Hợp đồng tối thiểu cần cho việc chờ. `api.ts` cài transport thật, test cài transport giả. */
export interface AIJobTransport {
  enqueue(request: AIJobCreateRequest): Promise<AIJobAccepted>;
  getJob(jobId: number): Promise<AIJobSnapshot>;
  cancelJob(jobId: number): Promise<AIJobAccepted>;
}

/** Đồng hồ và hẹn giờ bơm vào được — lý do test chạy tức thì thay vì chờ thật. */
export interface AIJobScheduler {
  now(): number;
  setTimeout(fn: () => void, ms: number): unknown;
  clearTimeout(handle: unknown): void;
}

export const systemScheduler: AIJobScheduler = {
  now: () => Date.now(),
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  clearTimeout: (handle) => clearTimeout(handle as ReturnType<typeof setTimeout>),
};

export interface AIJobErrorInit {
  kind: AIJobFailureKind;
  jobId?: number | null;
  backendReason?: string | null;
  httpStatus?: number | null;
  /** Task bị `dispose()` (component bị tháo) — UI không nên báo lỗi cho người dùng. */
  disposed?: boolean;
  cause?: unknown;
}

export class AIJobError extends Error {
  readonly kind: AIJobFailureKind;
  readonly jobId: number | null;
  readonly backendReason: string | null;
  readonly httpStatus: number | null;
  readonly disposed: boolean;
  /** Lỗi gốc (thường là `AxiosError`) giữ lại để log, không dùng để hiển thị. */
  readonly originalError: unknown;

  constructor(message: string, init: AIJobErrorInit) {
    super(message);
    this.name = 'AIJobError';
    this.kind = init.kind;
    this.jobId = init.jobId ?? null;
    this.backendReason = init.backendReason ?? null;
    this.httpStatus = init.httpStatus ?? null;
    this.disposed = init.disposed ?? false;
    this.originalError = init.cause;
  }
}

const FAILED_KINDS: ReadonlySet<AIJobStatus> = new Set<AIJobStatus>(['failed', 'cancelled']);
const TERMINAL_KINDS: ReadonlySet<AIJobStatus> = new Set<AIJobStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);

export const isTerminalAIJobStatus = (status: string): boolean =>
  TERMINAL_KINDS.has(status as AIJobStatus);

/**
 * Phân loại lỗi. Đây là phần dễ làm ẩu nhất của cả hệ thống: người dùng chỉ
 * quan tâm "làm gì tiếp theo", mà "lỗi 500" không trả lời được câu đó.
 *
 * Phân biệt quan trọng nhất: 429 lúc ENQUEUE là hạn mứng của hệ thống ta
 * (`enforce_quota`), còn 429 nằm trong `error` của job là provider AI từ chối.
 * Hai việc cần làm hoàn toàn khác nhau, nên phải ra hai loại lỗi khác nhau.
 */
export function classifyAIJobFailure(input: {
  phase: 'enqueue' | 'execute';
  httpStatus?: number | null;
  backendError?: string | null;
}): AIJobFailureKind {
  const { phase, httpStatus, backendError } = input;

  if (phase === 'enqueue') {
    if (httpStatus === 429) return 'quota';
    if (httpStatus === 409) return 'conflict';
    if (httpStatus === 422 || httpStatus === 400) return 'validation';
    if (httpStatus === 401 || httpStatus === 403) return 'unauthorized';
    if (httpStatus && httpStatus >= 500) return 'provider_outage';
    if (!httpStatus) return 'network';
    return 'unknown';
  }

  const raw = (backendError || '').trim();
  if (!raw) return 'unknown';

  // `sweep_expired_jobs` ghi tiền tố `TIMEOUT:` (hằng `queue.FAILURE_TIMEOUT`).
  if (/^TIMEOUT\b/i.test(raw)) return 'timeout';

  if (/HTTP\s*429|too many requests|rate[\s_-]?limit/i.test(raw)) return 'rate_limit';

  if (
    /HTTP\s*(500|502|503|504|408)|overloaded|service unavailable|bad gateway|gateway timeout|connection (error|refused|reset|aborted)|connecterror|readtimeout|timed out|httpx\./i.test(
      raw,
    )
  ) {
    return 'provider_outage';
  }

  if (/HTTP\s*(401|403|404)|not authorized|không có quyền|không tồn tại/i.test(raw)) {
    return 'unauthorized';
  }

  if (/HTTP\s*409|conflict/i.test(raw)) return 'conflict';

  if (/HTTP\s*422|payload không hợp lệ|validationerror|field required/i.test(raw)) {
    return 'validation';
  }

  return 'unknown';
}

export interface AIJobFailureDescription {
  title: string;
  hint: string;
  /** Người dùng có nên thử lại ngay không. */
  retryable: boolean;
}

/**
 * Câu chữ cho từng loại lỗi.
 *
 * KHÔNG trộn nguyên văn lý do của backend vào đây: thông báo này là lời giải
 * thích và hành động đề xuất, còn nguyên văn thì hiển thị riêng (xem
 * `AIJobError.backendReason`) để người dùng tự đối chiếu với log máy chủ.
 */
export function describeAIJobFailure(kind: AIJobFailureKind): AIJobFailureDescription {
  switch (kind) {
    case 'timeout':
      return {
        title: 'Hết thời gian chờ',
        hint: 'Tác vụ chạy quá lâu nên hệ thống ngừng chờ. Tác vụ có thể vẫn đang chạy trên máy chủ — thử lại sau, hoặc rút ngắn nội dung yêu cầu.',
        retryable: true,
      };
    case 'rate_limit':
      return {
        title: 'Nhà cung cấp AI đang giới hạn tốc độ',
        hint: 'Máy chủ AI từ chối vì quá nhiều yêu cầu. Đây là tình trạng tạm thời ở phía nhà cung cấp, thử lại sau ít phút.',
        retryable: true,
      };
    case 'provider_outage':
      return {
        title: 'Nhà cung cấp AI không phản hồi',
        hint: 'Kết nối tới nhà cung cấp AI bị lỗi hoặc máy chủ họ đang quá tải. Không phải lỗi dữ liệu của bạn — thử lại sau.',
        retryable: true,
      };
    case 'quota':
      return {
        title: 'Đã vượt hạn mức gọi AI',
        hint: 'Bạn đã dùng hết số lượt gọi AI trong chu kỳ hiện tại. Hạn mức sẽ được mở lại sau, hoặc hãy chờ tới chu kỳ kế tiếp.',
        retryable: false,
      };
    case 'validation':
      return {
        title: 'Dữ liệu đầu vào không hợp lệ',
        hint: 'Yêu cầu bị từ chối trước khi gọi AI vì thiếu hoặc sai trường dữ liệu. Kiểm tra lại các ô đã nhập rồi thử lại.',
        retryable: false,
      };
    case 'conflict':
      return {
        title: 'Yêu cầu trùng với một lần gửi khác',
        hint: 'Một khoá chống gọi trùng đã được dùng cho nội dung khác. Hãy thử lại với nội dung hiện tại.',
        retryable: true,
      };
    case 'unauthorized':
      return {
        title: 'Không có quyền thực hiện',
        hint: 'Phiên đăng nhập hoặc quyền trên không gian làm việc không cho phép tác vụ này. Đăng nhập lại hoặc chọn đúng không gian làm việc.',
        retryable: false,
      };
    case 'network':
      return {
        title: 'Không kết nối được máy chủ',
        hint: 'Máy chủ backend không phản hồi (có thể đang khởi động lại). Thử lại sau 30–50 giây.',
        retryable: true,
      };
    case 'cancelled':
      return {
        title: 'Đã huỷ',
        hint: 'Tác vụ đã bị huỷ trước khi có kết quả.',
        retryable: true,
      };
    default:
      return {
        title: 'Tác vụ AI thất bại',
        hint: 'Không xác định được nguyên nhân. Bạn có thể thử lại; nếu lặp lại, hãy báo lại kèm thông báo gốc bên dưới.',
        retryable: true,
      };
  }
}

export interface AIJobTaskUpdate {
  phase: AIJobPhase;
  jobId: number | null;
  status: AIJobStatus | null;
  elapsedMs: number;
  attempts: number;
  maxAttempts: number;
  /** Số lần backend đã thử (đã retry) — hiện ra để người dùng biết đang thử lại. */
  retries: number;
  error: AIJobError | null;
  /** Job `failed` tạm thời rồi được đẩy lại hàng đợi (status vẫn `queued`). */
  requeued: boolean;
  /** Backend có nói lý do không (hiển thị nguyên văn, không diễn giải). */
  backendReason: string | null;
  /** Huỷ bị từ chối vì job đã chạy (HTTP 409) — polling vẫn tiếp tục để lấy kết quả. */
  cancelRejectedReason: string | null;
}

/**
 * Nguồn gốc thật của một kết quả AI.
 *
 * Backend trả `is_fallback=true` + `model_provider="template-fallback-engine"`
 * khi không gọi được nhà cung cấp và dựng nội dung bằng bộ template dự phòng.
 * Kết quả đó vẫn hữu ích, nhưng KHÔNG được trình bày như sản phẩm của mô hình
 * ngôn ngữ — nếu không người dùng tin là AI đã viết khi thực tế máy chủ dùng
 * khuôn mẫu có sẵn.
 */
export interface AIResultOrigin {
  isFallback: boolean;
  /** Chuỗi `provider/model` để hiển thị, đã gắn nhãn dự phòng khi cần. */
  label: string;
}

export const describeAIResultOrigin = (result: {
  is_fallback?: boolean | null;
  model_used?: string | null;
  model_provider?: string | null;
}): AIResultOrigin => {
  const provider = result.model_provider || 'AI';
  const model = result.model_used || 'không rõ';
  const isFallback = result.is_fallback === true;
  return {
    isFallback,
    label: isFallback
      ? `nội dung dự phòng (${provider}/${model}) — KHÔNG phải do mô hình ngôn ngữ viết`
      : `${provider}/${model}`,
  };
};

export interface AIJobTaskOptions {
  deadlineMs?: number;
  initialBackoffMs?: number;
  maxBackoffMs?: number;
  backoffFactor?: number;
  scheduler?: AIJobScheduler;
  onUpdate?: (update: AIJobTaskUpdate) => void;
}

/** Hạn chờ mặc định 8 phút. Rộng hơn `AI_JOB_TIMEOUT_SECONDS=300` của backend để server kịp báo lỗi có kiểm soát. */
export const DEFAULT_AI_JOB_DEADLINE_MS = 480_000;
const DEFAULT_INITIAL_BACKOFF_MS = 1_500;
const DEFAULT_MAX_BACKOFF_MS = 15_000;
const DEFAULT_BACKOFF_FACTOR = 1.6;
/** Số lần lỗi mạng liên tiếp chịu được trước khi bỏ cuộc. Render free có lúc cold start. */
const MAX_TRANSPORT_RETRIES = 3;

export interface AIJobTask<T = Record<string, unknown>> {
  run(request: AIJobCreateRequest): Promise<T>;
  cancel(): void;
  dispose(): void;
  readonly active: boolean;
  readonly jobId: number | null;
}

const stripNullish = <V extends Record<string, unknown>>(input: V): Partial<V> => {
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(input)) {
    if (value !== undefined && value !== null) out[key] = value;
  }
  return out as Partial<V>;
};

/** Khoá chống gọi trùng. Ưu tiên `crypto.randomUUID`, có fallback cho ngữ cảnh không có. */
export const newAIJobIdempotencyKey = (): string => {
  const cryptoRef = (globalThis as { crypto?: Crypto }).crypto;
  if (cryptoRef && typeof cryptoRef.randomUUID === 'function') {
    return cryptoRef.randomUUID();
  }
  return `aijob-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
};

export function createAIJobTask<T = Record<string, unknown>>(
  transport: AIJobTransport,
  options: AIJobTaskOptions = {},
): AIJobTask<T> {
  const sched = options.scheduler ?? systemScheduler;
  const deadlineMs = options.deadlineMs ?? DEFAULT_AI_JOB_DEADLINE_MS;
  const initialBackoff = options.initialBackoffMs ?? DEFAULT_INITIAL_BACKOFF_MS;
  const maxBackoff = options.maxBackoffMs ?? DEFAULT_MAX_BACKOFF_MS;
  const factor = options.backoffFactor ?? DEFAULT_BACKOFF_FACTOR;
  const notify = options.onUpdate;

  const IDLE_TASK_UPDATE: AIJobTaskUpdate = {
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

  let activePromise: Promise<T> | null = null;
  let activeJobId: number | null = null;
  let disposed = false;
  let cancelRequested = false;
  /** Timer đang chờ. Giữ tham chiếu để `dispose()` xoá được đúng cái. */
  let pendingSleep: { handle: unknown; wake: () => void } | null = null;
  /**
   * Kết cục của lệnh huỷ đang bay: `'cancelled'` = server đã huỷ, `'continue'` =
   * server từ chối vì job đã `running` nên phải chờ tiếp lấy kết quả.
   *
   * Vòng poll PHẢI chờ promise này trước khi quyết định dừng. Nếu ném lỗi
   * `cancelled` ngay khi người dùng bấm huỷ rồi mới xử lý phản hồi 409 sau, thì
   * client báo "đã huỷ" trong khi máy chủ vẫn đang chạy job — đúng dạng nói dối
   * mà nguyên tắc 1 của file này cấm.
   */
  let cancelOutcome: Promise<'cancelled' | 'continue'> | null = null;
  /**
   * Lý do backend từ chối huỷ (HTTP 409 khi job đã `running`).
   *
   * Sống lâu hơn một lần `emit` vì nó phải hiện nguyên trạng suốt các vòng poll
   * tiếp theo: nếu chỉ gửi kèm một lần rồi mất, người dùng thấy cảnh báo biến
   * mất trong khi thực tế vẫn chưa huỷ được.
   */
  let cancelRejectedReason: string | null = null;

  /** Cập nhật gần nhất, dùng làm nền cho `emit` kế tiếp. */
  let lastUpdate: AIJobTaskUpdate = { ...IDLE_TASK_UPDATE };

  const emit = (patch: Partial<AIJobTaskUpdate>): void => {
    lastUpdate = { ...lastUpdate, ...patch };
    if (!notify) return;
    notify({ ...lastUpdate });
  };

  const sleep = (ms: number): Promise<void> =>
    new Promise<void>((resolve) => {
      const handle = sched.setTimeout(() => {
        pendingSleep = null;
        resolve();
      }, Math.max(0, ms));
      pendingSleep = {
        handle,
        wake: () => {
          sched.clearTimeout(handle);
          pendingSleep = null;
          resolve();
        },
      };
    });

  const wake = (): void => {
    if (pendingSleep) pendingSleep.wake();
  };

  const fail = (
    kind: AIJobFailureKind,
    message: string,
    extra: Partial<AIJobErrorInit> = {},
  ): AIJobError => {
    const error = new AIJobError(message, {
      kind,
      jobId: activeJobId,
      disposed,
      ...extra,
    });
    emit({
      phase: disposed ? 'idle' : kind === 'cancelled' ? 'cancelled' : 'failed',
      error,
      status: error.kind === 'cancelled' ? 'cancelled' : 'failed',
      backendReason: error.backendReason,
    });
    return error;
  };

  const execute = async (request: AIJobCreateRequest): Promise<T> => {
    const startedAt = sched.now();
    const deadlineAt = startedAt + deadlineMs;
    let attempts = 0;
    let maxAttempts = 0;
    let transportFailures = 0;

    const elapsed = (): number => sched.now() - startedAt;

    // --- 1. Enqueue -------------------------------------------------------------
    let accepted: AIJobAccepted;
    try {
      accepted = await transport.enqueue(
        stripNullish({
          ...request,
          idempotency_key: request.idempotency_key ?? newAIJobIdempotencyKey(),
        }) as AIJobCreateRequest,
      );
    } catch (error) {
      const httpStatus = (error as { response?: { status?: number } })?.response?.status ?? null;
      const detail =
        (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail ??
        null;
      const kind = classifyAIJobFailure({ phase: 'enqueue', httpStatus });
      const reason = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : null;
      throw fail(kind, `Không tạo được tác vụ AI: ${reason ?? 'lỗi không xác định'}`, {
        httpStatus,
        backendReason: reason,
        cause: error,
      });
    }

    if (disposed) throw fail('cancelled', 'Tác vụ đã bị huỷ do rời khỏi trang.');
    if (cancelRequested) throw fail('cancelled', 'Tác vụ đã bị huỷ trước khi bắt đầu.');

    activeJobId = accepted.job_id;
    emit({
      phase: accepted.status === 'running' ? 'running' : 'queued',
      status: (accepted.status as AIJobStatus) ?? 'queued',
      elapsedMs: elapsed(),
    });

    // --- 2. Poll ----------------------------------------------------------------
    let backoff = initialBackoff;
    let requeued = false;
    let backendReason: string | null = null;

    for (;;) {
      if (disposed) throw fail('cancelled', 'Tác vụ đã bị huỷ do rời khỏi trang.');

      if (cancelRequested) {
        // Chờ lệnh huỷ có kết cục rồi mới quyết định. Xem `cancelOutcome`.
        const outcome = cancelOutcome ? await cancelOutcome : 'cancelled';
        if (outcome === 'cancelled') throw fail('cancelled', 'Bạn đã huỷ tác vụ này.');
        // HTTP 409: job đang chạy, máy chủ không huỷ được. Người dùng đã chờ
        // vài phút và LLM vẫn đang tốn tiền, nên tiếp tục chờ lấy kết quả thay
        // vì báo "huỷ xong" rồi bỏ mặc.
        cancelRequested = false;
      }

      const remaining = deadlineAt - sched.now();
      if (remaining <= 0) {
        throw fail(
          'timeout',
          `Đã chờ hết ${Math.round(deadlineMs / 1000)} giây mà tác vụ vẫn chưa xong.`,
          { backendReason },
        );
      }

      let snapshot: AIJobSnapshot;
      try {
        snapshot = await transport.getJob(activeJobId);
        transportFailures = 0;
      } catch (error) {
        transportFailures += 1;
        const httpStatus =
          (error as { response?: { status?: number } })?.response?.status ?? null;
        if (httpStatus === 404) {
          throw fail('unknown', 'Không tìm thấy tác vụ trên máy chủ.', {
            httpStatus,
            cause: error,
          });
        }
        if (httpStatus === 401 || httpStatus === 403) {
          throw fail('unauthorized', 'Phiên đăng nhập không còn hợp lệ.', {
            httpStatus,
            cause: error,
          });
        }
        if (transportFailures >= MAX_TRANSPORT_RETRIES) {
          const kind = classifyAIJobFailure({ phase: 'execute', httpStatus });
          throw fail(kind, 'Không liên lạc được với máy chủ để kiểm tra tiến độ tác vụ.', {
            httpStatus,
            cause: error,
          });
        }
        // Lỗi mạng tạm thời: thử lại, job vẫn chạy trên máy chủ.
        await sleep(Math.min(backoff, remaining));
        backoff = Math.min(backoff * factor, maxBackoff);
        continue;
      }

      attempts = snapshot.attempts ?? 0;
      maxAttempts = snapshot.max_attempts ?? 0;
      requeued = snapshot.status === 'queued' && attempts > 0;
      backendReason = snapshot.error ?? null;

      emit({
        phase:
          snapshot.status === 'running'
            ? 'running'
            : snapshot.status === 'queued'
              ? 'queued'
              : snapshot.status,
        status: snapshot.status,
        elapsedMs: elapsed(),
        attempts,
        maxAttempts,
        retries: Math.max(attempts - 1, 0),
        requeued,
        backendReason,
        cancelRejectedReason,
      });

      if (TERMINAL_KINDS.has(snapshot.status)) {
        activeJobId = null;
        if (snapshot.status === 'succeeded') {
          if (snapshot.result === null || snapshot.result === undefined) {
            throw fail('unknown', 'Tác vụ báo thành công nhưng không có kết quả trả về.', {
              backendReason: snapshot.error ?? null,
            });
          }
          emit({ phase: 'succeeded', status: 'succeeded', elapsedMs: elapsed() });
          return snapshot.result as T;
        }
        if (snapshot.status === 'cancelled') {
          throw fail('cancelled', 'Tác vụ đã bị huỷ trên máy chủ.', {
            backendReason: snapshot.error ?? null,
          });
        }
        const kind = classifyAIJobFailure({
          phase: 'execute',
          backendError: snapshot.error ?? null,
        });
        const description = describeAIJobFailure(kind);
        throw fail(kind, `Tác vụ AI thất bại: ${description.title}`, {
          backendReason: snapshot.error ?? null,
        });
      }

      if (!FAILED_KINDS.has(snapshot.status) && snapshot.status === 'queued' && !requeued) {
        // Job mới vào hàng: thăm dò nhanh hơn một chút vì thường được nhặt ngay.
        backoff = initialBackoff;
      }

      const sleepMs = Math.min(backoff, Math.max(0, deadlineAt - sched.now()));
      await sleep(sleepMs);
      backoff = Math.min(backoff * factor, maxBackoff);
    }
  };

  const task: AIJobTask<T> = {
    get active(): boolean {
      return activePromise !== null;
    },
    get jobId(): number | null {
      return activeJobId;
    },
    run(request: AIJobCreateRequest): Promise<T> {
      // Double-click: trả lại đúng promise đang chờ, KHÔNG enqueue lần hai.
      if (activePromise) return activePromise;
      if (disposed) {
        return Promise.reject(
          new AIJobError('Tác vụ đã bị huỷ do rời khỏi trang.', { kind: 'cancelled', disposed: true }),
        );
      }
      cancelRequested = false;
      cancelOutcome = null;
      cancelRejectedReason = null;
      lastUpdate = { ...IDLE_TASK_UPDATE };
      activePromise = execute(request).finally(() => {
        activePromise = null;
        activeJobId = null;
        pendingSleep = null;
        cancelOutcome = null;
      });
      return activePromise;
    },
    cancel(): void {
      if (!activePromise) return;
      cancelRequested = true;
      const jobId = activeJobId;
      // Chưa có `job_id` (đang trong lúc enqueue) thì không có gì để huỷ trên
      // máy chủ; vòng poll sẽ thấy `cancelRequested` và dừng ngay.
      cancelOutcome =
        jobId === null
          ? Promise.resolve('cancelled')
          : transport.cancelJob(jobId).then(
              () => 'cancelled' as const,
              (error: unknown) => {
                const httpStatus =
                  (error as { response?: { status?: number } })?.response?.status ?? null;
                const detail =
                  (error as { response?: { data?: { detail?: unknown } } })?.response?.data
                    ?.detail ?? null;
                const reason =
                  typeof detail === 'string'
                    ? detail
                    : detail
                      ? JSON.stringify(detail)
                      : 'không rõ';
                cancelRejectedReason = `Máy chủ từ chối huỷ (HTTP ${httpStatus ?? '?'}): ${reason}`;
                // HTTP 409 = job đang `running`; Python không huỷ được thread đã
                // chạy. Trả `'continue'` để vòng poll tiếp tục lấy kết quả.
                // Mọi lỗi khác coi như đã dừng — lúc đó không còn gì để chờ và
                // giữ màn hình ở trạng thái "đang chờ" là nói dối.
                emit({ cancelRejectedReason });
                return httpStatus === 409 ? ('continue' as const) : ('cancelled' as const);
              },
            );
      wake();
    },
    dispose(): void {
      disposed = true;
      cancelRequested = true;
      // `dispose()` không huỷ job trên máy chủ: người dùng điều hướng đi mất,
      // tác vụ vẫn chạy và kết quả vẫn còn đọc được bằng `GET /ai/jobs/{id}`.
      // Huỷ ở đây sẽ đốt hạn mứng đã trừ một cách vô nghĩa.
      wake();
    },
  };

  return task;
}