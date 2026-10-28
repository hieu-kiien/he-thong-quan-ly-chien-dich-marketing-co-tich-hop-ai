import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import {
  ArrowDown,
  Bot,
  Sparkles,
} from 'lucide-react';
import type { AiMessage, AssistantPhase } from '@/lib/types';
import { QUICK_PROMPTS, type QuickPrompt } from '../types';
import { MessageItem } from './MessageItem';

interface ChatViewProps {
  messages: AiMessage[];
  isStreaming: boolean;
  phase: AssistantPhase | null;
  queuePosition?: number;
  onSelectPrompt: (template: string) => void;
  onRegenerate: (messageId: number) => void;
  onSelectAction: (actionId: number) => void;
  onRetryLast: () => void;
}

export function ChatView({
  messages,
  isStreaming,
  phase,
  queuePosition,
  onSelectPrompt,
  onRegenerate,
  onSelectAction,
  onRetryLast,
}: ChatViewProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomAnchorRef = useRef<HTMLDivElement>(null);
  const [showScrollBottomPill, setShowScrollBottomPill] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const isUserScrolledUpRef = useRef(false);

  // Bộ đếm thời gian thực thi (giây) để người dùng thấy phản hồi đang tiến triển
  useEffect(() => {
    if (!isStreaming) {
      setElapsedSec(0);
      return;
    }
    setElapsedSec(0);
    const timer = window.setInterval(() => {
      setElapsedSec((prev) => prev + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [isStreaming]);

  // Kiểm tra vị trí cuộn
  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;

    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    const isUp = distanceFromBottom > 100;

    isUserScrolledUpRef.current = isUp;
    setShowScrollBottomPill(isUp);
  }, []);

  // Tự động cuộn xuống đáy khi có tin nhắn mới hoặc streaming nếu người dùng chưa cuộn lên
  useEffect(() => {
    if (!isUserScrolledUpRef.current) {
      bottomAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isStreaming, phase]);

  const scrollToBottom = () => {
    isUserScrolledUpRef.current = false;
    setShowScrollBottomPill(false);
    bottomAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Xác định tin nhắn AI cuối cùng để kích hoạt nút "Tạo lại"
  let lastAssistantMsgId: number | null = null;
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'ASSISTANT') {
      lastAssistantMsgId = messages[i].id;
      break;
    }
  }

  // Nhãn trạng thái đang thực thi
  const getPhaseStatusText = () => {
    if (phase === 'queued') {
      return `Đang chờ đến lượt${queuePosition ? ` (vị trí ${queuePosition})` : ''}…`;
    }
    if (phase === 'thinking') {
      return 'Đang suy nghĩ…';
    }
    if (phase === 'tool') {
      return 'Đang tra cứu dữ liệu…';
    }
    if (phase === 'writing') {
      return 'Đang viết…';
    }
    return 'Đang xử lý…';
  };

  return (
    <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden bg-canvas">
      {/* Vùng cuộn danh sách tin nhắn */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8"
      >
        {messages.length === 0 ? (
          // Empty State khi phiên chưa có tin nhắn
          <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent shadow-xs">
              <Bot className="h-6 w-6" aria-hidden />
            </div>

            <h2 className="mt-4 text-lg font-semibold tracking-tight text-fg">
              Trợ lý Marketing AI
            </h2>
            <p className="mt-1.5 max-w-md text-sm text-fg-muted">
              Hỗ trợ lên ý tưởng, viết nội dung theo kênh, phân tích số liệu chiến dịch
              và lập kế hoạch tiếp thị.
            </p>

            {/* Danh sách 5 gợi ý nhanh */}
            <div className="mt-8 grid w-full grid-cols-1 gap-2.5 sm:grid-cols-2 text-left">
              {QUICK_PROMPTS.map((prompt: QuickPrompt) => (
                <button
                  key={prompt.id}
                  type="button"
                  onClick={() => onSelectPrompt(prompt.template)}
                  className="group flex flex-col rounded-lg border border-border bg-surface p-3.5 text-left transition-colors hover:border-accent hover:bg-subtle focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                >
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-3.5 w-3.5 text-accent" aria-hidden />
                    <span className="text-xs font-semibold text-fg group-hover:text-accent">
                      {prompt.title}
                    </span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[11px] text-fg-muted">
                    {prompt.description}
                  </p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl">
            {messages.map((message) => {
              const isThisStreaming =
                isStreaming && message.id === lastAssistantMsgId;
              const isLastAssistant =
                message.id === lastAssistantMsgId && !isStreaming;

              return (
                <MessageItem
                  key={message.id}
                  message={message}
                  isLastAssistant={isLastAssistant}
                  isStreamingThisMessage={isThisStreaming}
                  onRegenerate={() => onRegenerate(message.id)}
                  onSelectAction={onSelectAction}
                  onRetry={onRetryLast}
                />
              );
            })}

            {/* Dòng trạng thái khi đang stream (Shimmer Skeleton màu xanh Teal #0D9488) */}
            {isStreaming && phase && (
              <div
                aria-live="polite"
                className="my-3 inline-flex items-center gap-2 rounded-full border border-ai/25 px-3 py-1 text-xs font-medium text-ai shimmer-ai"
              >
                <span className="h-2 w-2 rounded-full bg-ai animate-pulse" aria-hidden />
                <span>{getPhaseStatusText()}</span>
                {elapsedSec > 0 && (
                  <span className="font-mono text-[11px] text-fg-subtle tabular-nums">
                    ({elapsedSec}s)
                  </span>
                )}
              </div>
            )}

            <div ref={bottomAnchorRef} className="h-4" />
          </div>
        )}
      </div>

      {/* Nút nổi "Xuống cuối" khi người dùng cuộn lên */}
      {showScrollBottomPill && (
        <div className="pointer-events-none absolute bottom-4 left-1/2 -translate-x-1/2">
          <button
            type="button"
            onClick={scrollToBottom}
            className="pointer-events-auto inline-flex items-center gap-1.5 rounded-full border border-border bg-surface/95 px-3.5 py-1.5 text-xs font-medium text-fg shadow-md backdrop-blur-xs transition-colors hover:bg-subtle focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <ArrowDown className="h-3.5 w-3.5 text-fg-muted" aria-hidden />
            <span>Xuống cuối</span>
          </button>
        </div>
      )}
    </div>
  );
}
