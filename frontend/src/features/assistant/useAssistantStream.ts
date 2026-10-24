import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
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

export function useAssistantStream(threadId?: number) {
  const queryClient = useQueryClient();
  const [streamingState, setStreamingState] = useState<StreamingState>(INITIAL_STREAMING_STATE);
  const abortControllerRef = useRef<AbortController | null>(null);
  const activeStreamThreadIdRef = useRef<number | null>(null);

  // Dọn dẹp khi unmount (huỷ luồng fetch ngầm để tránh rò rỉ)
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  // Huỷ luồng khi người dùng chuyển sang xem một phiên khác (tránh huỷ khi chuyển từ undefined sang newThread.id)
  useEffect(() => {
    if (threadId && activeStreamThreadIdRef.current && threadId !== activeStreamThreadIdRef.current) {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      activeStreamThreadIdRef.current = null;
    }
  }, [threadId]);

  /**
   * Dừng lượt sinh hiện tại (Stop button): gọi abort fetch + gọi POST /assistant/threads/{id}/stop.
   */
  const stopStreaming = useCallback(async () => {
    if (!streamingState.isStreaming) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    if (threadId && !(import.meta.env.DEV && isSimulatorActive)) {
      try {
        await assistantApi.stop(threadId);
      } catch (err) {
        if (import.meta.env.DEV) {
          console.warn('[Assistant] Lỗi khi gọi stop API:', err);
        }
      }
    }

    setStreamingState((prev) => ({
      ...prev,
      isStreaming: false,
      phase: null,
    }));

    // Cập nhật tin nhắn cuối trong cache sang trạng thái STOPPED nếu có
    if (threadId && streamingState.assistantMessageId) {
      queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', threadId], (old = []) => {
        return old.map((msg) =>
          msg.id === streamingState.assistantMessageId ? { ...msg, status: 'STOPPED' } : msg,
        );
      });
    }
  }, [streamingState.isStreaming, streamingState.assistantMessageId, threadId, queryClient]);

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
      // Huỷ luồng cũ nếu còn
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;
      activeStreamThreadIdRef.current = activeThreadId;

      setStreamingState({
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
          setStreamingState((prev) => ({
            ...prev,
            userMessageId: data.user_message?.id,
            assistantMessageId: data.assistant_message.id,
          }));

          // Đồng bộ cache tin nhắn
          queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', activeThreadId], (old = []) => {
            const list = [...old];
            if (data.user_message && !list.some((m) => m.id === data.user_message?.id)) {
              list.push(data.user_message);
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
          setStreamingState((prev) => ({
            ...prev,
            phase: data.phase,
            queuePosition: data.queue_position,
          }));
        },

        onText: (data: { content: string }) => {
          setStreamingState((prev) => ({
            ...prev,
            accumulatedText: data.content,
          }));

          // Cập nhật nội dung tạm vào cache tin nhắn đang stream
          queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', activeThreadId], (old = []) => {
            if (!old) return [];
            return old.map((msg) =>
              msg.status === 'STREAMING' ? { ...msg, content: data.content } : msg,
            );
          });
        },

        onToolCall: (data: { id: string; name: string; args: Record<string, unknown>; status: ToolCallStatus; summary?: string | null }) => {
          setStreamingState((prev) => {
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

          // Cập nhật parts_json vào tin nhắn đang stream trong cache
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
          setStreamingState((prev) => ({
            ...prev,
            proposedActions: [...prev.proposedActions, action],
          }));

          // Cập nhật danh sách actions của thread trong React Query
          queryClient.setQueryData<AiAction[]>(['assistant', 'actions', activeThreadId], (old = []) => {
            if (old.some((a) => a.id === action.id)) {
              return old.map((a) => (a.id === action.id ? action : a));
            }
            return [action, ...old];
          });
        },

        onMessageEnd: (data: { message: AiMessage }) => {
          setStreamingState((prev) => ({
            ...prev,
            isStreaming: false,
            phase: null,
            accumulatedText: data.message.content,
          }));

          // Ghi đè tin nhắn hoàn chỉnh đã lưu DB vào cache
          queryClient.setQueryData<AiMessage[]>(['assistant', 'messages', activeThreadId], (old = []) => {
            return old.map((msg) => (msg.id === data.message.id ? data.message : msg));
          });

          // Làm mới danh sách phiên để cập nhật last_message_at
          queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
          // Đồng bộ lại danh sách actions
          queryClient.invalidateQueries({ queryKey: ['assistant', 'actions', activeThreadId] });
        },

        onError: (data: { code: string; message: string }) => {
          setStreamingState((prev) => ({
            ...prev,
            isStreaming: false,
            phase: null,
            error: data,
          }));

          // Đánh dấu tin nhắn đang stream thành ERROR trong cache
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
        if (!controller.signal.aborted) {
          const errObj = err as { code?: string; message?: string };
          callbacks.onError({
            code: errObj.code || 'AI_INTERNAL',
            message: errObj.message || 'Đã xảy ra lỗi trong quá trình xử lý luồng.',
          });
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

      // Thêm ngay tin nhắn người dùng tạm thời vào giao diện
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

      await executeStream(threadId, (controller, callbacks) => {
        if (import.meta.env.DEV && isSimulatorActive) {
          return simulateAssistantStream(threadId, 'Tạo lại câu trả lời', callbacks, controller.signal);
        }
        return streamRegenerateMessage(messageId, callbacks, controller.signal);
      });
    },
    [threadId, executeStream],
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
