import { test, expect } from '@playwright/test';

import {
  AIJobAccepted,
  AIJobCreateRequest,
  AIJobError,
  AIJobScheduler,
  AIJobSnapshot,
  AIJobStatus,
  AIJobTransport,
  classifyAIJobFailure,
  createAIJobTask,
  describeAIJobFailure,
  describeAIResultOrigin,
} from '../../src/services/aiJobPoller';

/**
 * =========================================================================
 * KIỂM THỬ LỚP POLLING HÀNG ĐỜI AI — KHÔNG BAO GIỜ GỌI MẠNG THẬT
 * =========================================================================
 *
 * `createAIJobTask` nhận `transport` và `scheduler` qua tham số, nên toàn bộ
 * suite này chạy trong Node với hai bộ giả:
 *   - transport trả `AIJobSnapshot` dựng sẵn, không gọi `fetch`/axios;
 *   - scheduler là một đồng hồ ảo điều khiển được, thay cho `setTimeout` thật.
 *
 * Hệ quả cần nhấn mạnh: KHÔNG có test nào ở đây gọi provider AI, không tiêu tốn
 * credit, và chạy xong trong vài chục mili giây thay vì vài phút.
 *
 * Các hành vi bị khoá ở đây (mỗi cái là một lỗi đã xảy ra thật hoặc có thể xảy ra):
 *   1. Resolve khi `succeeded` và trả đúng `result` của backend.
 *   2. Reject khi `failed`, với loại lỗi phân loại đúng + nguyên văn lý do.
 *   3. Reject khi `cancelled` — và đây KHÔNG phải lỗi hệ thống.
 *   4. Tôn trọng `deadlineMs`: quá hạn thì dừng và báo `timeout`.
 *   5. `dispose()` xoá timer đang chờ và ngừng thăm dò (không rò rỉ khi rời trang).
 *   6. `cancel()` gọi thật `POST /jobs/{id}/cancel` trên server.
 *   7. `cancel()` bị server từ chối (409, job đã `running`) thì KHÔNG báo đã huỷ.
 *   8. Double-click: `run()` lần hai trong lúc đang chạy không enqueue thêm job.
 *   9. Backoff tăng dần và có trần — không spam thăm dò mỗi giây suốt bốn phút.
 */

interface ScheduledTimer {
  id: number;
  fireAt: number;
  fn: () => void;
}

/**
 * Đồng hồ ảo.
 *
 * `advance()` chạy các callback đã tới hạn theo đúng thứ tự thời gian, nên thứ
 * tự backoff và deadline trong `createAIJobTask` được kiểm chứng chứ không đoán.
 * `pendingCount` là bằng chứng trực tiếp cho yêu cầu "timer phải được dọn".
 */
class FakeScheduler implements AIJobScheduler {
  private current = 0;
  private nextId = 1;
  private timers: ScheduledTimer[] = [];

  now(): number {
    return this.current;
  }

  setTimeout(fn: () => void, ms: number): unknown {
    const id = this.nextId++;
    this.timers.push({ id, fireAt: this.current + Math.max(0, ms), fn });
    return id;
  }

  clearTimeout(handle: unknown): void {
    this.timers = this.timers.filter((t) => t.id !== handle);
  }

  get pendingCount(): number {
    return this.timers.length;
  }

  /** Đẩy đồng hồ đi `ms` và chạy mọi timer tới hạn dọc theo thứ tự. */
  async advance(ms: number): Promise<void> {
    const target = this.current + ms;
    for (;;) {
      const due = this.timers
        .filter((t) => t.fireAt <= target)
        .sort((a, b) => a.fireAt - b.fireAt)[0];
      if (!due) break;
      this.timers = this.timers.filter((t) => t.id !== due.id);
      this.current = due.fireAt;
      due.fn();
      // Để các promise đang chờ được nối chuỗi trước bước tiếp theo.
      await flushMicrotasks();
    }
    this.current = target;
    await flushMicrotasks();
  }
}

/**
 * Drain hết microtask queue.
 *
 * Dùng `setImmediate` (macrotask) chứ không phải vài vòng `Promise.resolve()`:
 * `await` xích trong `createAIJobTask` đi qua nhiều promise, và chỉ một macrotask
 * mới chắc chắn xảy hết. Thiếu bước này thì `advance()` kịp kết thúc trước khi
 * poller kịp đăng ký timer kế tiếp, và test timeout vô lý.
 */
const flushMicrotasks = async (): Promise<void> => {
  await new Promise<void>((resolve) => setImmediate(resolve));
};

/**
 * Cho một tác vụ đã bắt đầu chạy kịp đi qua phần `await` đầu tiên (enqueue)
 * trước khi đồng hồ ảo được đẩy. Thiếu bước này thì `advance()` chạy trước khi
 * poller kịp đăng ký timer đầu tiên.
 */
const settle = async (): Promise<void> => {
  for (let i = 0; i < 5; i += 1) await flushMicrotasks();
};

const snapshot = (patch: Partial<AIJobSnapshot> & { status: AIJobStatus }): AIJobSnapshot => ({
  job_id: 1,
  kind: 'omnichannel',
  attempts: 1,
  max_attempts: 3,
  error: null,
  result: null,
  ...patch,
});

interface ScriptedTransportOptions {
  /** Chuỗi snapshot trả lần lượt cho mỗi lần `getJob`. Hết danh sách thì lặp lại phần tử cuối. */
  polls?: AIJobSnapshot[];
  enqueueError?: { status: number; detail?: string };
  /** Số lần `getJob` được phép thất bại với lỗi mạng trước khi trả kết quả. */
  transientPollFailures?: number;
  cancelError?: { status: number; detail?: string };
}

/** Transport giả: đếm số lần gọi và trả lập trình sẵn, không chạm mạng. */
const scriptedTransport = (options: ScriptedTransportOptions = {}) => {
  const calls = { enqueue: 0, getJob: 0, cancel: 0 };
  const requests: AIJobCreateRequest[] = [];
  const polls = options.polls ?? [];

  const transport: AIJobTransport = {
    async enqueue(request: AIJobCreateRequest): Promise<AIJobAccepted> {
      calls.enqueue += 1;
      requests.push(request);
      if (options.enqueueError) {
        const err = new Error('enqueue failed') as Error & {
          response?: { status: number; data: { detail: string } };
        };
        err.response = {
          status: options.enqueueError.status,
          data: { detail: options.enqueueError.detail ?? 'lỗi' },
        };
        throw err;
      }
      return { job_id: 1, status: 'queued', kind: request.kind, deduplicated: false, poll_url: '/api/v1/ai/jobs/1' };
    },
    async getJob(): Promise<AIJobSnapshot> {
      calls.getJob += 1;
      if (calls.getJob <= (options.transientPollFailures ?? 0)) {
        // Lỗi không có `response` = mất mạng / Render cold start.
        throw new Error('Network Error');
      }
      const index = Math.min(calls.getJob - 1, polls.length - 1);
      return polls[index];
    },
    async cancelJob(jobId: number): Promise<AIJobAccepted> {
      calls.cancel += 1;
      if (options.cancelError) {
        const err = new Error('cancel failed') as Error & {
          response?: { status: number; data: { detail: string } };
        };
        err.response = {
          status: options.cancelError.status,
          data: { detail: options.cancelError.detail ?? 'Không thể huỷ' },
        };
        throw err;
      }
      return { job_id: jobId, status: 'cancelled', kind: 'omnichannel', deduplicated: false, poll_url: '' };
    },
  };

  return { transport, calls, requests };
};

test.describe('createAIJobTask — hàng đợi AI bất đồng bộ', () => {
  test('resolve với `result` khi job chuyển sang succeeded', async () => {
    const scheduler = new FakeScheduler();
    const result = { task_type: 'OMNICHANNEL', facebook: { headline: 'Tiêu đề' } };
    const { transport, calls } = scriptedTransport({
      polls: [
        snapshot({ status: 'queued' }),
        snapshot({ status: 'running', attempts: 1 }),
        snapshot({ status: 'succeeded', result }),
      ],
    });

    const task = createAIJobTask(transport, { scheduler, initialBackoffMs: 1000, maxBackoffMs: 8000 });
    const promise = task.run({ kind: 'omnichannel', brief: 'brief thử' });

    await settle();
    await settle();    await scheduler.advance(10_000);
    await expect(promise).resolves.toEqual(result);

    // Phải thật sự thăm dò qua hàng đợi, không lấy kết quả bằng đường tắt.
    expect(calls.enqueue).toBe(1);
    expect(calls.getJob).toBe(3);
  });

  test('reject với loại lỗi đúng khi job failed, kèm nguyên văn lý do của backend', async () => {
    const scheduler = new FakeScheduler();
    // `TIMEOUT:` là tiền tố do `queue.sweep_expired_jobs` ghi khi quá hạn cứng.
    const { transport } = scriptedTransport({
      polls: [snapshot({ status: 'running' }), snapshot({ status: 'failed', error: 'TIMEOUT: job vượt thời hạn cứng 300s.' })],
    });

    const task = createAIJobTask(transport, { scheduler, initialBackoffMs: 1000 });
    const promise = task.run({ kind: 'omnichannel', brief: 'b' });
    const assertion = expect(promise).rejects.toMatchObject({
      kind: 'timeout',
      backendReason: 'TIMEOUT: job vượt thời hạn cứng 300s.',
    });

    await settle();
    await scheduler.advance(10_000);
    await assertion;
  });

  test('phân biệt rate limit của provider với lỗi hạn mứng của hệ thống', async () => {
    const scheduler = new FakeScheduler();
    const { transport } = scriptedTransport({
      polls: [snapshot({ status: 'failed', error: 'Endpoint AI trả HTTP 429: AI Provider trả về lỗi HTTP 429: rate limit' })],
    });

    const task = createAIJobTask(transport, { scheduler, initialBackoffMs: 1000 });
    const promise = task.run({ kind: 'omnichannel', brief: 'b' });
    const assertion = expect(promise).rejects.toMatchObject({ kind: 'rate_limit' });
    await settle();    await scheduler.advance(10_000);
    await assertion;

    // 429 lúc ENQUEUE là hạn mứng của ta (`enforce_quota`), khác hẳn 429 của
    // provider nằm trong `error` của job. Trộn hai loại này là dạng lỗi gây hiểu
    // nhầm nhiều nhất.
    expect(classifyAIJobFailure({ phase: 'enqueue', httpStatus: 429 })).toBe('quota');
    expect(
      classifyAIJobFailure({
        phase: 'execute',
        backendError: 'API Provider trả về lỗi HTTP 429: too many requests',
      }),
    ).toBe('rate_limit');
  });

  test('reject là `cancelled` khi job bị huỷ trên máy chủ, không phải lỗi hệ thống', async () => {
    const scheduler = new FakeScheduler();
    const { transport } = scriptedTransport({
      polls: [snapshot({ status: 'queued' }), snapshot({ status: 'cancelled' })],
    });

    const task = createAIJobTask(transport, { scheduler, initialBackoffMs: 1000 });
    const promise = task.run({ kind: 'omnichannel', brief: 'b' });
    const assertion = expect(promise).rejects.toMatchObject({ kind: 'cancelled' });

    await settle();
    await scheduler.advance(10_000);
    await assertion;
  });

  test('tôn trọng deadline: quá hạn thì dừng chờ và báo timeout', async () => {
    const scheduler = new FakeScheduler();
    // Job cứ kẹt ở `running` mãi — đúng tình huống 237 giây của omnichannel.
    const { transport, calls } = scriptedTransport({ polls: [snapshot({ status: 'running' })] });

    const task = createAIJobTask(transport, { scheduler, deadlineMs: 30_000, initialBackoffMs: 1000, maxBackoffMs: 5000 });
    const promise = task.run({ kind: 'omnichannel', brief: 'b' });
    const assertion = expect(promise).rejects.toMatchObject({ kind: 'timeout' });

    // Chỉ cần chạy quá mốc; poller phải tự chặn mà không cần thêm một lần poll nào.
    await settle();    await scheduler.advance(31_000);
    await assertion;
    expect(calls.getJob).toBeGreaterThan(0);
  });

  test('dispose() xoá timer đang chờ và ngừng thăm dò', async () => {
    const scheduler = new FakeScheduler();
    const { transport, calls } = scriptedTransport({ polls: [snapshot({ status: 'running' })] });

    const task = createAIJobTask(transport, { scheduler, initialBackoffMs: 1000, maxBackoffMs: 5000 });
    const promise = task.run({ kind: 'omnichannel', brief: 'b' });
    const assertion = expect(promise).rejects.toMatchObject({ kind: 'cancelled', disposed: true });

    // Chạy tới lúc poller đang nằm chờ giữa hai vòng thăm dò — đúng trạng thái
    // khi người dùng điều hướng rời trang.
    await settle();    await scheduler.advance(1000);
    expect(scheduler.pendingCount).toBeGreaterThan(0);

    task.dispose();

    // KHÔNG còn timer treo: đây là điều kiện để unmount không rò rỉ bộ nhớ.
    expect(scheduler.pendingCount).toBe(0);

    const pollsAtDispose = calls.getJob;
    await settle();    await scheduler.advance(60_000);
    // Và không hề thăm dò thêm sau khi đã dispose.
    expect(calls.getJob).toBe(pollsAtDispose);

    await assertion;
  });

  test('cancel() gọi thật endpoint huỷ trên máy chủ', async () => {
    const scheduler = new FakeScheduler();
    const { transport, calls } = scriptedTransport({ polls: [snapshot({ status: 'queued' })] });

    const task = createAIJobTask(transport, { scheduler, initialBackoffMs: 1000 });
    const promise = task.run({ kind: 'omnichannel', brief: 'b' });
    const assertion = expect(promise).rejects.toMatchObject({ kind: 'cancelled' });

    await settle();
    await scheduler.advance(1000);
    task.cancel();
    await settle();    await scheduler.advance(1000);

    // Không chỉ dừng giao diện: phải có đúng một lệnh huỷ gửi lên server.
    expect(calls.cancel).toBe(1);
    await assertion;
  });

  test('khi server từ chối huỷ (409, job đã running) thì KHÔNG báo đã huỷ', async () => {
    const scheduler = new FakeScheduler();
    const updates: { phase: string; cancelRejectedReason: string | null }[] = [];
    const { transport, calls } = scriptedTransport({
      // Job chuyển sang `running` ngay vòng poll đầu.
      polls: [snapshot({ status: 'running' }), snapshot({ status: 'running' }), snapshot({ status: 'running' })],
      cancelError: { status: 409, detail: "Không thể huỷ job ở trạng thái 'running'. Chỉ huỷ được job đang chờ (queued)." },
    });

    const task = createAIJobTask(transport, {
      scheduler,
      initialBackoffMs: 1000,
      onUpdate: (u) => updates.push({ phase: u.phase, cancelRejectedReason: u.cancelRejectedReason }),
    });
    const promise = task.run({ kind: 'omnichannel', brief: 'b' });

    await settle();
    await scheduler.advance(1000);
    task.cancel();
    await settle();    await scheduler.advance(1000);

    expect(calls.cancel).toBe(1);
    // Lý do từ chối phải xuất hiện để UI hiển thị, thay vì bịa trạng thái "đã huỷ".
    expect(updates.some((u) => (u.cancelRejectedReason ?? '').includes('running'))).toBe(true);

    task.dispose();
    await expect(promise).rejects.toMatchObject({ kind: 'cancelled', disposed: true });
  });

  test('không enqueue lần hai khi bấm lại trong lúc đang chạy (double-click)', async () => {
    const scheduler = new FakeScheduler();
    const { transport, calls, requests } = scriptedTransport({
      polls: [snapshot({ status: 'running' }), snapshot({ status: 'succeeded', result: { task_type: 'IDEA' } })],
    });

    const task = createAIJobTask(transport, { scheduler, initialBackoffMs: 1000 });
    const first = task.run({ kind: 'omnichannel', brief: 'b' });

    // Ba lần bấm nữa trong khi lần đầu còn đang chờ.
    const second = task.run({ kind: 'omnichannel', brief: 'b' });
    const third = task.run({ kind: 'omnichannel', brief: 'b' });

    expect(second).toBe(first);
    expect(third).toBe(first);

    await settle();
    await scheduler.advance(10_000);
    await expect(first).resolves.toMatchObject({ task_type: 'IDEA' });

    // Một lượt gọi AI, một lần trừ hạn mứng.
    expect(calls.enqueue).toBe(1);
    expect(requests).toHaveLength(1);
  });

  test('luôn gửi idempotency_key để backend có lớp chống trùng thứ hai', async () => {
    const scheduler = new FakeScheduler();
    const { transport, requests } = scriptedTransport({
      polls: [snapshot({ status: 'succeeded', result: {} })],
    });

    const task = createAIJobTask(transport, { scheduler, initialBackoffMs: 1000 });
    await task.run({ kind: 'ideas', channel_code: 'facebook' });
    await settle();    await scheduler.advance(1000);

    expect(requests[0].idempotency_key).toBeTruthy();
  });

  test('backoff tăng dần và có trần, không thăm dò dồn dập', async () => {
    const scheduler = new FakeScheduler();
    const { transport, calls } = scriptedTransport({ polls: [snapshot({ status: 'running' })] });

    const task = createAIJobTask(transport, {
      scheduler,
      initialBackoffMs: 1000,
      backoffFactor: 2,
      maxBackoffMs: 4000,
      deadlineMs: 1_000_000,
    });
    const promise = task.run({ kind: 'omnichannel', brief: 'b' });
    promise.catch(() => undefined);

    // Chạy đúng 30 giây. Với nhịp 1s -> 2s -> 4s -> 4s... số lần thăm dò phải
    // nhỏ; nếu thăm dò mỗi giây thì đã là 30 lần.
    await settle();    await scheduler.advance(30_000);
    const pollsIn30s = calls.getJob;
    expect(pollsIn30s).toBeGreaterThan(0);
    expect(pollsIn30s).toBeLessThanOrEqual(10);

    task.dispose();
    await expect(promise).rejects.toMatchObject({ disposed: true });
  });

  test('lỗi mạng tạm thời khi thăm dò thì thử lại, không bỏ cuộc ngay', async () => {
    const scheduler = new FakeScheduler();
    const { transport } = scriptedTransport({
      transientPollFailures: 2,
      polls: [snapshot({ status: 'succeeded', result: { task_type: 'IDEA' } })],
    });

    const task = createAIJobTask(transport, { scheduler, initialBackoffMs: 1000 });
    const promise = task.run({ kind: 'ideas' });

    await settle();
    await scheduler.advance(30_000);
    await expect(promise).resolves.toMatchObject({ task_type: 'IDEA' });
  });

  test('phân loại đủ các nguyên nhân backend có thể trả về', () => {
    expect(classifyAIJobFailure({ phase: 'enqueue', httpStatus: 422 })).toBe('validation');
    expect(classifyAIJobFailure({ phase: 'enqueue', httpStatus: 409 })).toBe('conflict');
    expect(classifyAIJobFailure({ phase: 'enqueue', httpStatus: 403 })).toBe('unauthorized');
    expect(classifyAIJobFailure({ phase: 'enqueue', httpStatus: 503 })).toBe('provider_outage');
    expect(classifyAIJobFailure({ phase: 'enqueue', httpStatus: null })).toBe('network');

    expect(
      classifyAIJobFailure({ phase: 'execute', backendError: 'ConnectError: [Errno 110] Connection refused' }),
    ).toBe('provider_outage');
    expect(classifyAIJobFailure({ phase: 'execute', backendError: "Endpoint AI trả HTTP 422: Payload không hợp lệ" })).toBe(
      'validation',
    );
    expect(classifyAIJobFailure({ phase: 'execute', backendError: 'Endpoint AI trả HTTP 403: Not authorized' })).toBe(
      'unauthorized',
    );
    expect(classifyAIJobFailure({ phase: 'execute', backendError: 'Lỗi không lường trước' })).toBe('unknown');
  });

  test('mỗi loại lỗi có hành động đề xuất riêng, không gộp chung', () => {
    const kinds = ['timeout', 'rate_limit', 'provider_outage', 'quota', 'validation', 'conflict', 'unauthorized', 'network', 'unknown'] as const;
    const titles = new Set<string>();
    for (const kind of kinds) {
      const description = describeAIJobFailure(kind);
      expect(description.title).toBeTruthy();
      expect(description.hint).toBeTruthy();
      titles.add(description.title);
    }
    // Mỗi loại lỗi phải có tiêu đề riêng: gộp về một câu chung là dấu hiệu
    // người dùng không biết phải làm gì.
    expect(titles.size).toBe(kinds.length);

    // Hết hạn mứng thì không nên mời thử lại vì chắc chắn vẫn vượt.
    expect(describeAIJobFailure('quota').retryable).toBe(false);
    expect(describeAIJobFailure('timeout').retryable).toBe(true);
  });

  test('run() sau khi dispose() không enqueue thêm job nào', async () => {
    const scheduler = new FakeScheduler();
    const { transport, calls } = scriptedTransport({ polls: [snapshot({ status: 'succeeded', result: {} })] });

    const task = createAIJobTask(transport, { scheduler });
    task.dispose();

    await expect(task.run({ kind: 'ideas' })).rejects.toMatchObject({ disposed: true });
    expect(calls.enqueue).toBe(0);
  });

  test('lỗi enqueue 429 bị phân loại thành hạn mứng, kèm detail gốc của backend', async () => {
    const scheduler = new FakeScheduler();
    const { transport } = scriptedTransport({
      enqueueError: { status: 429, detail: 'Bạn đã vượt giới hạn số lượt gọi. Vui lòng thử lại sau.' },
    });

    const task = createAIJobTask(transport, { scheduler });
    let caught: AIJobError | null = null;
    try {
      await task.run({ kind: 'ideas' });
    } catch (error) {
      caught = error as AIJobError;
    }

    expect(caught).toBeInstanceOf(AIJobError);
    expect(caught!.kind).toBe('quota');
    expect(caught!.backendReason).toBe('Bạn đã vượt giới hạn số lượt gọi. Vui lòng thử lại sau.');
    expect(caught!.httpStatus).toBe(429);
  });

  test('job báo succeeded nhưng thiếu `result` thì phải ném lỗi, không trả undefined', async () => {
    const scheduler = new FakeScheduler();
    const { transport } = scriptedTransport({ polls: [snapshot({ status: 'succeeded', result: null })] });

    const task = createAIJobTask(transport, { scheduler, initialBackoffMs: 1000 });
    const promise = task.run({ kind: 'omnichannel', brief: 'b' });
    const assertion = expect(promise).rejects.toMatchObject({ kind: 'unknown' });

    await settle();
    await scheduler.advance(10_000);
    await assertion;
  });

  test('thông báo trạng thái đi qua queued rồi running trước khi thành công', async () => {
    const scheduler = new FakeScheduler();
    const phases: string[] = [];
    const { transport } = scriptedTransport({
      polls: [
        snapshot({ status: 'queued' }),
        snapshot({ status: 'running' }),
        snapshot({ status: 'succeeded', result: {} }),
      ],
    });

    const task = createAIJobTask(transport, {
      scheduler,
      initialBackoffMs: 1000,
      onUpdate: (u) => {
        if (phases[phases.length - 1] !== u.phase) phases.push(u.phase);
      },
    });
    const promise = task.run({ kind: 'omnichannel', brief: 'b' });
    await settle();    await scheduler.advance(10_000);
    await promise;

    // UI cần phân biệt "còn nằm hàng" với "đang chạy" để không bắt người dùng
    // ngồi nhìn một vòng quay không có thông tin.
    expect(phases).toEqual(expect.arrayContaining(['queued', 'running', 'succeeded']));
  });

  test('nguồn gốc dự phòng được dán nhãn rõ, không bao giờ hiện như kết quả AI', () => {
    const real = describeAIResultOrigin({
      is_fallback: false,
      model_provider: 'opencode',
      model_used: 'space-bunny-free',
    });
    expect(real.isFallback).toBe(false);
    expect(real.label).toBe('opencode/space-bunny-free');
    expect(real.label).not.toContain('KHÔNG');

    // Kết quả dự phòng vẫn hữu ích, nhưng KHÔNG được gắn tên provider như thể
    // mô hình ngôn ngữ đã viết ra nó.
    const fallback = describeAIResultOrigin({
      is_fallback: true,
      model_provider: 'template-fallback-engine',
      model_used: 'gemini-2.5-flash (Fallback Mock)',
    });
    expect(fallback.isFallback).toBe(true);
    expect(fallback.label).toContain('dự phòng');
    expect(fallback.label).toContain('KHÔNG phải do mô hình ngôn ngữ viết');
  });

  test('job bị backend đẩy lại hàng đợi sau lỗi tạm thời vẫn được chờ tiếp', async () => {
    const scheduler = new FakeScheduler();
    const updates: { status: string | null; retries: number }[] = [];
    // Lần 1 hỏng tạm thời: backend ghi `attempts=1`, status quay lại `queued` và
    // có `error`. Lần 2 mới thành công.
    const { transport } = scriptedTransport({
      polls: [
        snapshot({ status: 'running', attempts: 1 }),
        snapshot({ status: 'queued', attempts: 1, error: 'HTTP 503: provider overloaded' }),
        snapshot({ status: 'succeeded', attempts: 2, result: { task_type: 'IDEA' } }),
      ],
    });

    const task = createAIJobTask(transport, {
      scheduler,
      initialBackoffMs: 1000,
      onUpdate: (u) => updates.push({ status: u.status, retries: u.retries }),
    });
    const promise = task.run({ kind: 'ideas' });

    await settle();
    await scheduler.advance(30_000);
    await expect(promise).resolves.toMatchObject({ task_type: 'IDEA' });

    // Người dùng phải được báo đang thử lại lần 2, không phải treo im.
    expect(updates.some((u) => u.retries === 1)).toBe(true);
  });
});