import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  AlertTriangle,
  Bot,
  Check,
  Copy,
  ExternalLink,
  RotateCw,
  Sparkles,
  User,
} from 'lucide-react';
import { formatTime } from '@/lib/format';
import type {
  AiActionPart,
  AiMessage,
  AiToolCallPart,
} from '@/lib/types';
import { Button } from '@/components/ui';
import { getAiErrorMessage } from '../types';
import { useTypingReveal } from '../useTypingReveal';
import { ToolCallRow } from './ToolCallRow';

interface MessageItemProps {
  message: AiMessage;
  isLastAssistant: boolean;
  isStreamingThisMessage: boolean;
  onRegenerate?: () => void;
  onSelectAction?: (actionId: number) => void;
  onRetry?: () => void;
}

function MarkdownCodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-3 overflow-hidden rounded-md border border-border bg-subtle">
      <div className="flex items-center justify-between border-b border-border/80 bg-muted/30 px-3 py-1.5 text-xs text-fg-subtle">
        <span className="font-mono lowercase">{language || 'text'}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] hover:bg-surface hover:text-fg focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-success" aria-hidden />
              <span>Đã sao chép</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" aria-hidden />
              <span>Sao chép</span>
            </>
          )}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-xs leading-relaxed text-fg">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function MessageItem({
  message,
  isLastAssistant,
  isStreamingThisMessage,
  onRegenerate,
  onSelectAction,
  onRetry,
}: MessageItemProps) {
  const [copiedAll, setCopiedAll] = useState(false);
  const isUser = message.role === 'USER';

  // Hiệu ứng gõ chữ mượt mà cho tin nhắn AI đang stream
  const displayedContent = useTypingReveal(
    message.content,
    isStreamingThisMessage && message.status === 'STREAMING',
  );

  const handleCopyMarkdown = () => {
    navigator.clipboard.writeText(message.content);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  if (isUser) {
    return (
      <div className="my-4 flex justify-end">
        <div className="flex max-w-[85%] items-end gap-2 sm:max-w-[75%]">
          <div className="min-w-0">
            <div className="rounded-2xl rounded-tr-sm bg-stone-200 px-4 py-2.5 text-sm text-fg dark:bg-stone-800">
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
            </div>
            <div className="mt-1 flex justify-end pr-1 text-[11px] text-fg-subtle">
              <span>{formatTime(message.created_at)}</span>
            </div>
          </div>
          <div
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-border text-fg-muted"
            title="Bạn"
          >
            <User className="h-3.5 w-3.5" aria-hidden />
          </div>
        </div>
      </div>
    );
  }

  // Tách parts_json
  const toolParts: AiToolCallPart[] = [];
  const actionParts: AiActionPart[] = [];

  if (Array.isArray(message.parts_json)) {
    for (const part of message.parts_json) {
      if (part.type === 'tool_call') {
        toolParts.push(part);
      } else if (part.type === 'action') {
        actionParts.push(part);
      }
    }
  }

  const hasError = message.status === 'ERROR' || Boolean(message.error_code);
  const errorMessageText = getAiErrorMessage(message.error_code);

  return (
    <div className="my-5 flex w-full gap-3">
      <div
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent"
        title="Trợ lý AI"
      >
        <Bot className="h-4 w-4" aria-hidden />
      </div>

      <div className="min-w-0 flex-1">
        {/* Tiêu đề & thời gian */}
        <div className="mb-1.5 flex items-center gap-2">
          <span className="text-xs font-semibold text-fg">Trợ lý AI</span>
          <span className="text-[11px] text-fg-subtle">
            {formatTime(message.created_at)}
          </span>
          {message.status === 'STOPPED' && (
            <span className="rounded bg-muted/60 px-1.5 py-0.5 text-[10px] text-fg-subtle">
              Đã dừng
            </span>
          )}
        </div>

        {/* Danh sách tool calls thực hiện trong tin nhắn này */}
        {toolParts.length > 0 && (
          <div className="mb-2 space-y-1">
            {toolParts.map((tool) => (
              <ToolCallRow
                key={tool.id}
                name={tool.name}
                args={tool.args}
                status={tool.status}
                summary={tool.summary}
              />
            ))}
          </div>
        )}

        {/* Nội dung markdown */}
        {displayedContent ? (
          <div className="prose-mf min-w-0">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const rawString = String(children).replace(/\n$/, '');
                  const isInline = !match && !rawString.includes('\n');

                  if (isInline) {
                    return (
                      <code
                        className="rounded bg-subtle px-1 py-0.5 font-mono text-[0.8125rem] text-fg"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }

                  return (
                    <MarkdownCodeBlock
                      language={match ? match[1] : ''}
                      code={rawString}
                    />
                  );
                },
                table({ children }) {
                  return (
                    <div className="my-3 overflow-x-auto rounded border border-border">
                      <table className="w-full border-collapse text-left text-xs">
                        {children}
                      </table>
                    </div>
                  );
                },
                th({ children }) {
                  return (
                    <th className="border-b border-border bg-subtle px-3 py-2 font-semibold text-fg">
                      {children}
                    </th>
                  );
                },
                td({ children }) {
                  return (
                    <td className="border-b border-border/50 px-3 py-2 text-fg">
                      {children}
                    </td>
                  );
                },
                a({ href, children }) {
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-0.5 text-accent underline underline-offset-2 hover:text-accent-hover"
                    >
                      {children}
                      <ExternalLink className="inline h-3 w-3" aria-hidden />
                    </a>
                  );
                },
              }}
            >
              {displayedContent}
            </ReactMarkdown>
          </div>
        ) : isStreamingThisMessage ? (
          // Đang stream nhưng chưa có text (ví dụ đang gọi tool)
          <div className="py-2 text-xs text-fg-subtle italic">
            Đang chuẩn bị câu trả lời...
          </div>
        ) : null}

        {/* Các chip liên kết hành động (ai_action) được đề xuất */}
        {actionParts.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {actionParts.map((act) => (
              <button
                key={act.action_id}
                type="button"
                onClick={() => onSelectAction?.(act.action_id)}
                className="inline-flex items-center gap-1.5 rounded-full border border-accent/40 bg-accent-soft px-3 py-1 text-xs font-medium text-accent-soft-fg shadow-xs transition-colors hover:bg-accent-soft/80 focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
              >
                <Sparkles className="h-3.5 w-3.5" aria-hidden />
                <span>Xem đề xuất #{act.action_id}</span>
              </button>
            ))}
          </div>
        )}

        {/* Thông báo lỗi inline nếu có */}
        {hasError && (
          <div
            className="mt-3 flex items-start gap-2.5 rounded-md border border-danger/30 bg-danger-soft p-3 text-xs text-danger-soft-fg"
            role="alert"
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-danger" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="font-semibold">Lỗi phản hồi từ AI</p>
              <p className="mt-0.5 text-fg-muted">{errorMessageText}</p>
              {onRetry && (
                <div className="mt-2">
                  <Button size="sm" variant="secondary" onClick={onRetry}>
                    Thử lại
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Thanh tác vụ dưới tin nhắn */}
        {!isStreamingThisMessage && displayedContent && (
          <div className="mt-2 flex items-center gap-2 text-xs text-fg-subtle">
            <button
              type="button"
              onClick={handleCopyMarkdown}
              className="inline-flex items-center gap-1 rounded px-2 py-1 hover:bg-subtle hover:text-fg focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
              title="Sao chép toàn bộ nội dung"
            >
              {copiedAll ? (
                <>
                  <Check className="h-3.5 w-3.5 text-success" aria-hidden />
                  <span className="text-success">Đã sao chép</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" aria-hidden />
                  <span>Sao chép</span>
                </>
              )}
            </button>

            {isLastAssistant && onRegenerate && (
              <button
                type="button"
                onClick={onRegenerate}
                className="inline-flex items-center gap-1 rounded px-2 py-1 hover:bg-subtle hover:text-fg focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
                title="Tạo lại câu trả lời này"
              >
                <RotateCw className="h-3.5 w-3.5" aria-hidden />
                <span>Tạo lại</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
