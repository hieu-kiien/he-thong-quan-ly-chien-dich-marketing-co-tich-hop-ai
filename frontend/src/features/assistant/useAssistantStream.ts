import { useCallback, useEffect, useState } from 'react';
import { type QueryClient, useQueryClient } from '@tanstack/react-query';
import { assistantApi } from '@/lib/api/endpoints';
import type {
  AiAction,
  AiMessage,
  AiToolCallPart,
  AssistantPhase,
  ToolCallStatus,
} from '@/lib/types';
import { streamRegenerateMessage, streamSendMessage } from './sseClient';
import { isSimulatorActive, simulateAssistantStream } from './simulator';
import type { StreamingState } from './types';

const INITIAL_STREAMING_STATE: StreamingState = {
  isStreaming: false,
  phase: null,
  queuePosition: undefined,
  userMessageId: undefined,
  assistantMessageId: undefined,
  accumulatedText: '',
  toolCalls: [],
  proposedActions: [],
  error: null,
};

/** id tạm của tin nhắn lạc quan = Date.now() (> 1e11); id thật trong DB nhỏ hơn rất nhiều. */
const OPTIMISTIC_ID_MIN = 1e11;

/**
 * Kho lưu trạng thái stream ở cấp module theo từng threadId.
 * Giúp luồng SSE tiếp tục chạy ngầm khi người dùng chuyển trang trong ứng dụng (Tổng quan, Chiến dịch...)
 * hoặc đổi tab trình duyệt mà không bị huỷ kết nối hay rơi vào trạng thái lỗi giả.
 */
const streamStateByThread = new Map<number, StreamingState>();
const controllersByThread = new Map<number, AbortController>();
const pollingTimersByThread = new Map<number, ReturnType<typeof setInterval>>();
const stateListeners = new Set<() => void>();

function notifyListeners() {
  stateListeners.forEach((fn) => fn());
}

function getThreadStreamState(threadId?: number): StreamingState {
  if (!threadId) return INITIAL_STREAMING_STATE;
  return streamStateByThread.get(threadId) ?? INITIAL_STREAMING_STATE;
}

function updateThreadStreamState(
  threadId: number,
  updater: StreamingState | ((prev: StreamingState) => StreamingState),
) {
  const prev = getThreadStreamState(threadId);
  const next = typeof updater === 'function' ? updater(prev) : updater;
  streamStateByThread.set(threadId, next);
  notifyListeners();
}

function stopPollingForThread(threadId: number) {
  const timer = pollingTimersByThread.get(threadId);
  if (timer) {
    clearInterval(timer);
    pollingTimersByThread.delete(threadId);
  }
}

/**
 * Khi luồng SSE bị ngắt tạm thời do đổi tab trình duyệt / mạng chập chờn hoặc khi quay lại phiên đang STREAMING,
 * tự động hỏi thăm (poll) CSDL mỗi 1.5s cho tới khi lượt xử lý nền hoàn tất (COMPLETE / ERROR / STOPPED).
 */
function startPollingRecovery(threadId: number, queryClient: QueryClient) {
  if (pollingTimersByThread.has(threadId)) return;

  updateThreadStreamState(threadId, (prev) => ({
    ...prev,
    isStreaming: true,
    phase: prev.phase ?? 'writing',
    error: null,
  }));

  let attempts = 0;
  const maxAttempts = 120; // Tối đa ~3 phút (bằng timeout của lượt AI)

  const pollOnce = async () => {
    attempts += 1;
    try {
      const [messages, actions] = await Promise.all([
        assistantApi.messages(threadId),
        assistantApi.listActions({ thread_id: threadId }),
      ]);

      queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', threadId], messages);
      queryClient.setQueryData<AiAction[]>(['assistant', 'actions', threadId], actions);

      const lastAssistant = [...messages].reverse().find((m) => m.role === 'ASSISTANT');
      if (!lastAssistant) {
        if (attempts >= 5) {
          stopPollingForThread(threadId);
          updateThreadStreamState(threadId, INITIAL_STREAMING_STATE);
        }
        return;
      }

      if (lastAssistant.status === 'STREAMING') {
        updateThreadStreamState(threadId, (prev) => ({
          ...prev,
          isStreaming: true,
          assistantMessageId: lastAssistant.id,
          phase: lastAssistant.content ? 'writing' : prev.phase ?? 'thinking',
          accumulatedText: lastAssistant.content || prev.accumulatedText,
        }));
        if (attempts >= maxAttempts) {
          stopPollingForThread(threadId);
          updateThreadStreamState(threadId, (prev) => ({
            ...prev,
            isStreaming: false,
            phase: null,
          }));
        }
      } else {
        // Đã hoàn tất (COMPLETE / ERROR / STOPPED)
        stopPollingForThread(threadId);
        updateThreadStreamState(threadId, (prev) => ({
          ...prev,
          isStreaming: false,
          phase: null,
          assistantMessageId: lastAssistant.id,
          accumulatedText: lastAssistant.content,
          error:
            lastAssistant.status === 'ERROR'
              ? {
                  code: lastAssistant.error_code || 'AI_INTERNAL',
                  message: 'Lượt xử lý gặp sự cố. Bạn có thể bấm Tạo lại.',
                }
              : null,
        }));
        queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
      }
    } catch {
      if (attempts >= maxAttempts) {
        stopPollingForThread(threadId);
        updateThreadStreamState(threadId, (prev) => ({
          ...prev,
          isStreaming: false,
          phase: null,
        }));
      }
    }
  };

  void pollOnce();
  const timer = setInterval(() => {
    void pollOnce();
  }, 1500);
  pollingTimersByThread.set(threadId, timer);
}

export function useAssistantStream(threadId?: number) {
  const queryClient = useQueryClient();
  const [, setTick] = useState(0);

  useEffect(() => {
    const listener = () => setTick((t) => t + 1);
    stateListeners.add(listener);
    return () => {
      stateListeners.delete(listener);
    };
  }, []);

  const streamingState = getThreadStreamState(threadId);

  // Tự động khôi phục / đồng bộ khi người dùng quay lại tab hoặc mở một phiên đang STREAMING trên máy chủ
  useEffect(() => {
    if (!threadId) return;

    const checkAndSyncThread = async () => {
      // Nếu vẫn đang có kết nối SSE sống trên đúng thread này thì không cần can thiệp
      if (controllersByThread.has(threadId)) return;

      try {
        const messages = await assistantApi.messages(threadId);
        queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', threadId], messages);
        const lastMsg = messages[messages.length - 1];
        if (lastMsg && lastMsg.role === 'ASSISTANT' && lastMsg.status === 'STREAMING') {
          startPollingRecovery(threadId, queryClient);
        } else if (getThreadStreamState(threadId).isStreaming && !pollingTimersByThread.has(threadId)) {
          updateThreadStreamState(threadId, (prev) => ({
            ...prev,
            isStreaming: false,
            phase: null,
          }));
        }
      } catch {
        // Bỏ qua lỗi mạng tạm thời khi đồng bộ nền
      }
    };

    void checkAndSyncThread();

    const handleVisibilityOrFocus = () => {
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') return;
      void checkAndSyncThread();
      queryClient.invalidateQueries({ queryKey: ['assistant', 'actions', threadId] });
    };

    document.addEventListener('visibilitychange', handleVisibilityOrFocus);
    window.addEventListener('focus', handleVisibilityOrFocus);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityOrFocus);
      window.removeEventListener('focus', handleVisibilityOrFocus);
    };
  }, [threadId, queryClient]);

  /**
   * Dừng lượt sinh hiện tại (Stop button): gọi abort fetch + gọi POST /assistant/threads/{id}/stop.
   */
  const stopStreaming = useCallback(async () => {
    if (!threadId) return;
    const current = getThreadStreamState(threadId);
    if (!current.isStreaming) return;

    const ctrl = controllersByThread.get(threadId);
    if (ctrl) {
      ctrl.abort();
      controllersByThread.delete(threadId);
    }
    stopPollingForThread(threadId);

    if (!(import.meta.env.DEV && isSimulatorActive)) {
      try {
        await assistantApi.stop(threadId);
      } catch (err) {
        if (import.meta.env.DEV) {
          console.warn('[Assistant] Lỗi khi gọi stop API:', err);
        }
      }
    }

    updateThreadStreamState(threadId, (prev) => ({
      ...prev,
      isStreaming: false,
      phase: null,
    }));

    if (current.assistantMessageId) {
      queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', threadId], (old = []) => {
        return old.map((msg) =>
          msg.id === current.assistantMessageId ? { ...msg, status: 'STOPPED' } : msg,
        );
      });
    }
  }, [threadId, queryClient]);

  /**
   * Bắt đầu một luồng stream (dùng chung cho gửi mới hoặc tạo lại).
   */
  const executeStream = useCallback(
    async (
      activeThreadId: number,
      executeCall: (
        controller: AbortController,
        callbacks: {
          onMessageStart: (data: { user_message: AiMessage | null; assistant_message: { id: number; status: 'STREAMING' } }) => void;
          onStatus: (data: { phase: AssistantPhase; queue_position?: number }) => void;
          onText: (data: { content: string }) => void;
          onToolCall: (data: { id: string; name: string; args: Record<string, unknown>; status: ToolCallStatus; summary?: string | null }) => void;
          onAction: (data: AiAction) => void;
          onMessageEnd: (data: { message: AiMessage }) => void;
          onError: (data: { code: string; message: string }) => void;
        },
      ) => Promise<void>,
    ) => {
      // Huỷ kết nối cũ trên cùng thread (nếu có)
      const existingCtrl = controllersByThread.get(activeThreadId);
      if (existingCtrl) {
        existingCtrl.abort();
        controllersByThread.delete(activeThreadId);
      }
      stopPollingForThread(activeThreadId);

      const controller = new AbortController();
      controllersByThread.set(activeThreadId, controller);

      updateThreadStreamState(activeThreadId, {
        isStreaming: true,
        phase: 'queued',
        queuePosition: undefined,
        userMessageId: undefined,
        assistantMessageId: undefined,
        accumulatedText: '',
        toolCalls: [],
        proposedActions: [],
        error: null,
      });

      const callbacks = {
        onMessageStart: (data: { user_message: AiMessage | null; assistant_message: { id: number; status: 'STREAMING' } }) => {
          updateThreadStreamState(activeThreadId, (prev) => ({
            ...prev,
            userMessageId: data.user_message?.id,
            assistantMessageId: data.assistant_message.id,
          }));

          queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', activeThreadId], (old = []) => {
            const userMessage = data.user_message;
            const list = old.filter(
              (m) => !(userMessage && m.id > OPTIMISTIC_ID_MIN && m.role === 'USER' && m.content === userMessage.content),
            );
            if (userMessage && !list.some((m) => m.id === userMessage.id)) {
              list.push(userMessage);
            }
            if (!list.some((m) => m.id === data.assistant_message.id)) {
              const placeholderAssistant: AiMessage = {
                id: data.assistant_message.id,
                thread_id: activeThreadId,
                role: 'ASSISTANT',
                content: '',
                parts_json: [],
                status: 'STREAMING',
                error_code: null,
                model: null,
                latency_ms: null,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              };
              list.push(placeholderAssistant);
            }
            return list;
          });
        },

        onStatus: (data: { phase: AssistantPhase; queue_position?: number }) => {
          updateThreadStreamState(activeThreadId, (prev) => ({
            ...prev,
            phase: data.phase,
            queuePosition: data.queue_position,
          }));
        },

        onText: (data: { content: string }) => {
          updateThreadStreamState(activeThreadId, (prev) => ({
            ...prev,
            accumulatedText: data.content,
          }));

          queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', activeThreadId], (old = []) => {
            if (!old) return [];
            return old.map((msg) =>
              msg.status === 'STREAMING' ? { ...msg, content: data.content } : msg,
            );
          });
        },

        onToolCall: (data: { id: string; name: string; args: Record<string, unknown>; status: ToolCallStatus; summary?: string | null }) => {
          updateThreadStreamState(activeThreadId, (prev) => {
            const existingIndex = prev.toolCalls.findIndex((t) => t.id === data.id);
            const updatedCalls = [...prev.toolCalls];
            if (existingIndex >= 0) {
              updatedCalls[existingIndex] = {
                ...updatedCalls[existingIndex],
                ...data,
              };
            } else {
              updatedCalls.push({
                ...data,
              });
            }
            return {
              ...prev,
              toolCalls: updatedCalls,
            };
          });

          queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', activeThreadId], (old = []) => {
            if (!old) return [];
            return old.map((msg) => {
              if (msg.status !== 'STREAMING') return msg;
              const currentParts = (msg.parts_json || []) as AiToolCallPart[];
              const idx = currentParts.findIndex((p) => p.type === 'tool_call' && p.id === data.id);
              const newParts = [...currentParts];
              if (idx >= 0) {
                newParts[idx] = { ...newParts[idx], ...data };
              } else {
                newParts.push({ type: 'tool_call', ...data });
              }
              return { ...msg, parts_json: newParts };
            });
          });
        },

        onAction: (action: AiAction) => {
          updateThreadStreamState(activeThreadId, (prev) => ({
            ...prev,
            proposedActions: [...prev.proposedActions, action],
          }));

          queryClient.setQueryData<AiAction[]>(['assistant', 'actions', activeThreadId], (old = []) => {
            if (old.some((a) => a.id === action.id)) {
              return old.map((a) => (a.id === action.id ? action : a));
            }
            return [action, ...old];
          });
        },

        onMessageEnd: (data: { message: AiMessage }) => {
          controllersByThread.delete(activeThreadId);
          stopPollingForThread(activeThreadId);

          updateThreadStreamState(activeThreadId, (prev) => ({
            ...prev,
            isStreaming: false,
            phase: null,
            accumulatedText: data.message.content,
          }));

          queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', activeThreadId], (old = []) => {
            return old.map((msg) => (msg.id === data.message.id ? data.message : msg));
          });

          queryClient.invalidateQueries({ queryKey: ['assistant', 'messages', activeThreadId] });
          queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
          queryClient.invalidateQueries({ queryKey: ['assistant', 'actions', activeThreadId] });
        },

        onError: (data: { code: string; message: string }) => {
          controllersByThread.delete(activeThreadId);
          stopPollingForThread(activeThreadId);

          updateThreadStreamState(activeThreadId, (prev) => ({
            ...prev,
            isStreaming: false,
            phase: null,
            error: data,
          }));

          queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', activeThreadId], (old = []) => {
            return old.map((msg) =>
              msg.status === 'STREAMING'
                ? {
                    ...msg,
                    status: 'ERROR',
                    error_code: data.code,
                  }
                : msg,
            );
          });
        },
      };

      try {
        await executeCall(controller, callbacks);
      } catch (err: unknown) {
        controllersByThread.delete(activeThreadId);
        if (controller.signal.aborted) {
          return;
        }
        const errObj = err as {
          code?: string;
          message?: string;
          interruptedAfterStart?: boolean;
        };

        // Nếu kết nối SSE bị ngắt sau khi lượt chạy đã bắt đầu trên máy chủ (vd: đổi tab trình duyệt, mạng chập chờn)
        // hoặc phiên đang bận xử lý nền (THREAD_BUSY), chuyển sang chế độ đồng bộ nền (polling) thay vì báo lỗi!
        if (
          errObj.interruptedAfterStart ||
          errObj.code === 'STREAM_INTERRUPTED' ||
          errObj.code === 'THREAD_BUSY' ||
          Boolean(getThreadStreamState(activeThreadId).assistantMessageId)
        ) {
          startPollingRecovery(activeThreadId, queryClient);
          return;
        }

        callbacks.onError({
          code: errObj.code || 'AI_INTERNAL',
          message: errObj.message || 'Đã xảy ra lỗi trong quá trình xử lý luồng.',
        });
      } finally {
        if (controllersByThread.get(activeThreadId) === controller) {
          controllersByThread.delete(activeThreadId);
        }
      }
    },
    [queryClient],
  );

  /**
   * Gửi tin nhắn người dùng và mở luồng SSE.
   */
  const sendMessage = useCallback(
    async (content: string, overrideThreadId?: number) => {
      const activeId = overrideThreadId ?? threadId;
      if (!activeId || !content.trim()) return;

      const trimmed = content.trim();

      const optimisticUserMsg: AiMessage = {
        id: Date.now(),
        thread_id: activeId,
        role: 'USER',
        content: trimmed,
        parts_json: [],
        status: 'COMPLETE',
        error_code: null,
        model: null,
        latency_ms: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', activeId], (old = []) => [
        ...old,
        optimisticUserMsg,
      ]);

      await executeStream(activeId, (controller, callbacks) => {
        if (import.meta.env.DEV && isSimulatorActive) {
          return simulateAssistantStream(activeId, trimmed, callbacks, controller.signal);
        }
        return streamSendMessage(activeId, trimmed, callbacks, controller.signal);
      });
    },
    [threadId, executeStream, queryClient],
  );

  /**
   * Tạo lại phản hồi của tin nhắn AI cuối cùng.
   */
  const regenerateMessage = useCallback(
    async (messageId: number) => {
      if (!threadId) return;

      // Xoá tạm bong bóng lỗi/cũ và các đề xuất chưa thực thi gắn với messageId trên UI ngay khi bấm Tạo lại
      queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', threadId], (old = []) =>
        old.filter((m) => m.id !== messageId),
      );
      queryClient.setQueryData<AiAction[]>(['assistant', 'actions', threadId], (old = []) =>
        old.filter((a) => !(a.message_id === messageId && a.status !== 'EXECUTED')),
      );

      await executeStream(threadId, (controller, callbacks) => {
        if (import.meta.env.DEV && isSimulatorActive) {
          return simulateAssistantStream(threadId, 'Tạo lại câu trả lời', callbacks, controller.signal);
        }
        return streamRegenerateMessage(messageId, callbacks, controller.signal);
      });
    },
    [threadId, executeStream, queryClient],
  );

  return {
    streamingState,
    isStreaming: streamingState.isStreaming,
    phase: streamingState.phase,
    queuePosition: streamingState.queuePosition,
    accumulatedText: streamingState.accumulatedText,
    toolCalls: streamingState.toolCalls,
    sendMessage,
    regenerateMessage,
    stopStreaming,
  };
}
