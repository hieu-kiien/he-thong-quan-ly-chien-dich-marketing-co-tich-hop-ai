import { API_BASE, authHeaders, errorFromResponse } from '@/lib/api/client';
import type {
  AssistantPhase,
  ToolCallStatus,
} from '@/lib/types';
import { getSelectedAiModel } from './components/ModelSelector';
import type { AssistantStreamEventCallback } from './types';

/**
 * Xử lý chuỗi SSE thô từ một frame hoàn chỉnh (ngăn cách bởi \n\n).
 * Hỗ trợ các trường `event:`, `data:` (nhiều dòng data ghép lại bằng \n).
 */
function parseSseFrame(rawFrame: string): { event: string; data: string } | null {
  const lines = rawFrame.split(/\r?\n/);
  let event = 'message';
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith(':')) {
      // Dòng chú thích / ping của SSE, bỏ qua
      continue;
    }
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    event,
    data: dataLines.join('\n'),
  };
}

/**
 * Điều phối sự kiện đã parse tới các callback tương ứng.
 */
function dispatchSseEvent(
  event: string,
  rawJson: string,
  callbacks: AssistantStreamEventCallback,
  lifecycle?: { onStart: () => void; onTerminal: () => void },
): void {
  try {
    const parsedData = JSON.parse(rawJson);

    switch (event) {
      case 'message_start':
        lifecycle?.onStart();
        callbacks.onMessageStart?.(parsedData);
        break;
      case 'status':
        callbacks.onStatus?.(parsedData as { phase: AssistantPhase; queue_position?: number });
        break;
      case 'text':
        callbacks.onText?.(parsedData as { content: string });
        break;
      case 'tool_call':
        callbacks.onToolCall?.(
          parsedData as {
            id: string;
            name: string;
            args: Record<string, unknown>;
            status: ToolCallStatus;
            summary?: string | null;
          },
        );
        break;
      case 'action':
        callbacks.onAction?.(parsedData);
        break;
      case 'message_end':
        lifecycle?.onTerminal();
        callbacks.onMessageEnd?.(parsedData);
        break;
      case 'error':
        lifecycle?.onTerminal();
        callbacks.onError?.(parsedData as { code: string; message: string });
        break;
      default:
        // Sự kiện tuỳ biến hoặc không xác định
        break;
    }
  } catch (err) {
    // Nếu frame data không phải JSON hợp lệ, ghi log khi dev
    if (import.meta.env.DEV) {
      console.warn('[SSE] Không thể phân tích JSON từ data frame:', rawJson, err);
    }
  }
}

/**
 * Gọi POST endpoint trả về text/event-stream và đọc luồng bằng ReadableStream.
 */
export async function streamPost(
  path: string,
  body: Record<string, unknown>,
  callbacks: AssistantStreamEventCallback,
  signal?: AbortSignal,
): Promise<void> {
  const url = `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...authHeaders(),
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const apiError = await errorFromResponse(response);
    throw apiError;
  }

  const bodyStream = response.body;
  if (!bodyStream) {
    const err = { code: 'AI_EMPTY_RESPONSE', message: 'Phản hồi từ máy chủ không chứa luồng dữ liệu.' };
    throw err;
  }

  const reader = bodyStream.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let started = false;
  let terminalReceived = false;

  const lifecycle = {
    onStart: () => {
      started = true;
    },
    onTerminal: () => {
      terminalReceived = true;
    },
  };

  try {
    let streamActive = true;
    while (streamActive) {
      const { done, value } = await reader.read();
      if (done) {
        streamActive = false;
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Cắt từng frame SSE ngăn cách bởi 2 ký tự xuống dòng liên tiếp
      let boundaryIndex = buffer.indexOf('\n\n');
      while (boundaryIndex !== -1) {
        const rawFrame = buffer.slice(0, boundaryIndex).trim();
        buffer = buffer.slice(boundaryIndex + 2);

        if (rawFrame) {
          const parsed = parseSseFrame(rawFrame);
          if (parsed) {
            dispatchSseEvent(parsed.event, parsed.data, callbacks, lifecycle);
          }
        }
        boundaryIndex = buffer.indexOf('\n\n');
      }
    }

    // Nếu còn buffer chưa đóng \n\n ở cuối luồng
    const remaining = buffer.trim();
    if (remaining) {
      const parsed = parseSseFrame(remaining);
      if (parsed) {
        dispatchSseEvent(parsed.event, parsed.data, callbacks, lifecycle);
      }
    }

    // Nếu luồng kết thúc đột ngột khi đã bắt đầu nhưng chưa nhận message_end / error (vd: đổi tab làm ngắt kết nối)
    if (started && !terminalReceived && !signal?.aborted) {
      throw {
        code: 'STREAM_INTERRUPTED',
        message: 'Luồng kết nối tạm gián đoạn, đang đồng bộ kết quả từ máy chủ...',
        interruptedAfterStart: true,
      };
    }
  } catch (err: unknown) {
    if (signal?.aborted) {
      // Người dùng chủ động huỷ (Stop)
      return;
    }
    if (started && !terminalReceived) {
      throw {
        code: 'STREAM_INTERRUPTED',
        message: 'Luồng kết nối tạm gián đoạn, đang đồng bộ kết quả từ máy chủ...',
        interruptedAfterStart: true,
      };
    }
    const message = err instanceof Error ? err.message : 'Mất kết nối với luồng truyền dữ liệu AI.';
    throw {
      code: 'NETWORK_ERROR',
      message,
      interruptedAfterStart: false,
    };
  } finally {
    reader.releaseLock();
  }
}

/**
 * Gửi tin nhắn mới vào phiên và mở luồng SSE (POST /assistant/threads/{id}/messages).
 */
export async function streamSendMessage(
  threadId: number,
  content: string,
  callbacks: AssistantStreamEventCallback,
  signal?: AbortSignal,
): Promise<void> {
  const model = getSelectedAiModel();
  const payload: Record<string, unknown> = { content };
  if (model) {
    payload.model = model;
  }
  return streamPost(`/assistant/threads/${threadId}/messages`, payload, callbacks, signal);
}

/**
 * Tạo lại phản hồi cuối cùng qua SSE (POST /assistant/messages/{id}/regenerate).
 */
export async function streamRegenerateMessage(
  messageId: number,
  callbacks: AssistantStreamEventCallback,
  signal?: AbortSignal,
): Promise<void> {
  return streamPost(`/assistant/messages/${messageId}/regenerate`, {}, callbacks, signal);
}
