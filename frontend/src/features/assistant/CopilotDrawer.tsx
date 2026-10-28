import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Layers,
  Maximize2,
  Megaphone,
  MessageSquareText,
  Sparkles,
  X,
} from 'lucide-react';
import { assistantApi } from '@/lib/api/endpoints';
import { cn } from '@/lib/cn';
import type { AiThread } from '@/lib/types';
import { Badge, useToast } from '@/components/ui';
import { ActionCardRouter } from './components/ActionCards';
import { ChatView } from './components/ChatView';
import { Composer } from './components/Composer';
import { useAssistantStream } from './useAssistantStream';

interface CopilotState {
  open: boolean;
  threadId?: number;
  campaignId: number | null;
  campaignName?: string;
  prefillPrompt: string;
  activeTab: 'chat' | 'actions';
}

let copilotState: CopilotState = {
  open: false,
  threadId: undefined,
  campaignId: null,
  campaignName: undefined,
  prefillPrompt: '',
  activeTab: 'chat',
};

const listeners = new Set<() => void>();

function setCopilotState(updater: Partial<CopilotState> | ((prev: CopilotState) => CopilotState)) {
  copilotState = typeof updater === 'function' ? updater(copilotState) : { ...copilotState, ...updater };
  listeners.forEach((fn) => fn());
}

export function useCopilotDrawerState() {
  const [, setTick] = useState(0);
  useEffect(() => {
    const fn = () => setTick((t) => t + 1);
    listeners.add(fn);
    return () => {
      listeners.delete(fn);
    };
  }, []);
  return copilotState;
}

export function toggleContextualCopilot() {
  setCopilotState((prev) => ({ ...prev, open: !prev.open }));
}

export function closeContextualCopilot() {
  setCopilotState((prev) => ({ ...prev, open: false }));
}

export function openContextualCopilot(opts?: {
  campaignId?: number | null;
  campaignName?: string;
  prompt?: string;
}) {
  setCopilotState((prev) => ({
    ...prev,
    open: true,
    campaignId: opts?.campaignId !== undefined ? opts.campaignId : prev.campaignId,
    campaignName: opts?.campaignName ?? prev.campaignName,
    prefillPrompt: opts?.prompt ?? prev.prefillPrompt,
    activeTab: 'chat',
  }));
}

/**
 * Cột phải AI Copilot Drawer (380px - 420px, đóng/mở bằng Ctrl + K hoặc Cmd + J).
 * Cho phép làm việc với Trợ lý AI ngay cạnh bảng dữ liệu chiến dịch & biểu đồ mà không cần rời trang.
 */
export function CopilotDrawer() {
  const state = useCopilotDrawerState();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [composerText, setComposerText] = useState('');

  // Phím tắt toàn cục Ctrl + K hoặc Cmd + J
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isCtrlK = (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k';
      const isCmdJ = (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'j';
      if (isCtrlK || isCmdJ) {
        e.preventDefault();
        if (location.pathname.startsWith('/assistant')) {
          const textarea = document.querySelector<HTMLTextAreaElement>('textarea');
          textarea?.focus();
          return;
        }
        toggleContextualCopilot();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [location.pathname]);

  // Đồng bộ prefillPrompt vào ô nhập khi người dùng bấm [Tối ưu bằng AI] từ dòng bảng
  useEffect(() => {
    if (state.prefillPrompt) {
      setComposerText(state.prefillPrompt);
      setCopilotState({ prefillPrompt: '' });
    }
  }, [state.prefillPrompt]);

  // Lấy danh sách phiên để tự gắn phiên của chiến dịch đang chọn (hoặc phiên gần nhất)
  const { data: threads = [] } = useQuery({
    queryKey: ['assistant', 'threads'],
    queryFn: () => assistantApi.listThreads(),
    enabled: state.open,
  });

  useEffect(() => {
    if (!state.open) return;
    if (state.campaignId) {
      const matching = threads.find((t: AiThread) => t.campaign_id === state.campaignId);
      if (matching && matching.id !== state.threadId) {
        setCopilotState({ threadId: matching.id });
        return;
      }
      if (!matching) {
        assistantApi
          .createThread({
            campaign_id: state.campaignId,
            title: state.campaignName ? `Tối ưu: ${state.campaignName}` : `Chiến dịch #${state.campaignId}`,
          })
          .then((t) => {
            queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
            setCopilotState({ threadId: t.id });
          })
          .catch(() => {
            // Bỏ qua nếu đang tạo
          });
      }
    } else if (!state.threadId && threads.length > 0) {
      setCopilotState({ threadId: threads[0].id, campaignId: threads[0].campaign_id });
    }
  }, [state.open, state.campaignId, state.campaignName, state.threadId, threads, queryClient]);

  const activeThreadId = state.threadId;

  const { data: messages = [] } = useQuery({
    queryKey: ['assistant', 'messages', activeThreadId],
    queryFn: () => (activeThreadId ? assistantApi.messages(activeThreadId) : Promise.resolve([])),
    enabled: state.open && Boolean(activeThreadId),
  });

  const { data: actions = [] } = useQuery({
    queryKey: ['assistant', 'actions', activeThreadId],
    queryFn: () =>
      activeThreadId ? assistantApi.listActions({ thread_id: activeThreadId }) : Promise.resolve([]),
    enabled: state.open && Boolean(activeThreadId),
  });

  const { isStreaming, phase, queuePosition, sendMessage, regenerateMessage, stopStreaming } =
    useAssistantStream(activeThreadId);

  const proposedCount = actions.filter((a) => a.status === 'PROPOSED').length;

  const confirmActionMutation = useMutation({
    mutationFn: ({ id, args }: { id: number; args?: Record<string, unknown> }) =>
      assistantApi.confirmAction(id, { args }),
    onSuccess: () => {
      if (activeThreadId) {
        queryClient.invalidateQueries({ queryKey: ['assistant', 'actions', activeThreadId] });
      }
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      toast.success('Đã áp dụng gợi ý vào hệ thống.');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Không thể xác nhận đề xuất.');
    },
  });

  const rejectActionMutation = useMutation({
    mutationFn: (id: number) => assistantApi.rejectAction(id),
    onSuccess: () => {
      if (activeThreadId) {
        queryClient.invalidateQueries({ queryKey: ['assistant', 'actions', activeThreadId] });
      }
      toast.info('Đã bỏ qua đề xuất.');
    },
  });

  // Ẩn drawer trên trang /assistant vì trang đó đã là không gian AI toàn màn hình
  if (!state.open || location.pathname.startsWith('/assistant')) {
    return null;
  }

  const handleSend = async (text: string) => {
    if (!text.trim() || isStreaming) return;
    if (!activeThreadId) {
      try {
        const newThread = await assistantApi.createThread({
          title: text.trim().slice(0, 40),
          campaign_id: state.campaignId,
        });
        queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
        setCopilotState({ threadId: newThread.id });
        setComposerText('');
        await sendMessage(text, newThread.id);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Không thể khởi tạo phiên AI.');
      }
      return;
    }
    setComposerText('');
    await sendMessage(text);
  };

  return (
    <aside
      aria-label="Khung Tác Vụ AI (Contextual AI Panel)"
      className="contain-panel flex h-full w-full shrink-0 flex-col border-l border-border bg-ai-panel sm:w-[380px] xl:w-[410px] animate-slide-in-right"
    >
      {/* Header Contextual AI Panel */}
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface/90 px-3.5 backdrop-blur-xs">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-ai-soft text-ai">
            <Sparkles className="h-4 w-4" aria-hidden />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <h2 className="truncate text-xs font-semibold text-fg">Trợ lý AI ngữ cảnh</h2>
              <kbd className="hidden rounded border border-border bg-subtle px-1 py-0.5 font-mono text-[10px] text-fg-subtle sm:inline">
                Ctrl+K
              </kbd>
            </div>
            {state.campaignId ? (
              <p className="truncate text-[11px] font-medium text-ai">
                <Megaphone className="mr-1 inline h-3 w-3" aria-hidden />
                {state.campaignName || `Chiến dịch #${state.campaignId}`}
              </p>
            ) : (
              <p className="truncate text-[11px] text-fg-subtle">Hỗ trợ phân tích & tối ưu tại chỗ</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => {
              closeContextualCopilot();
              navigate(activeThreadId ? `/assistant/${activeThreadId}` : '/assistant');
            }}
            className="rounded-md p-1.5 text-fg-subtle hover:bg-subtle hover:text-fg"
            title="Mở không gian AI toàn màn hình"
            aria-label="Mở không gian AI toàn màn hình"
          >
            <Maximize2 className="h-3.5 w-3.5" aria-hidden />
          </button>
          <button
            type="button"
            onClick={closeContextualCopilot}
            className="rounded-md p-1.5 text-fg-subtle hover:bg-subtle hover:text-fg"
            title="Đóng khung AI (Ctrl+K)"
            aria-label="Đóng khung AI"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>
      </div>

      {/* Thanh chuyển tab Hội thoại / Đề xuất */}
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-surface/60 px-3 py-1.5">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setCopilotState({ activeTab: 'chat' })}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
              state.activeTab === 'chat'
                ? 'bg-surface text-fg shadow-xs ring-1 ring-border'
                : 'text-fg-muted hover:text-fg',
            )}
          >
            <MessageSquareText className="h-3.5 w-3.5 text-ai" aria-hidden />
            <span>Hội thoại</span>
          </button>
          <button
            type="button"
            onClick={() => setCopilotState({ activeTab: 'actions' })}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
              state.activeTab === 'actions'
                ? 'bg-surface text-fg shadow-xs ring-1 ring-border'
                : 'text-fg-muted hover:text-fg',
            )}
          >
            <Layers className="h-3.5 w-3.5 text-ai" aria-hidden />
            <span>Đề xuất & bản nháp</span>
            {proposedCount > 0 && <Badge tone="warning">{proposedCount}</Badge>}
          </button>
        </div>

        <select
          aria-label="Chọn phiên hội thoại"
          value={activeThreadId ?? ''}
          onChange={(e) => {
            const val = e.target.value;
            if (!val) {
              setCopilotState({ threadId: undefined });
              return;
            }
            const tid = Number(val);
            const found = threads.find((t: AiThread) => t.id === tid);
            setCopilotState({
              threadId: tid,
              campaignId: found?.campaign_id ?? state.campaignId,
              campaignName: found?.campaign?.name,
            });
          }}
          className="max-w-[135px] truncate rounded border border-border bg-surface px-1.5 py-1 text-[11px] text-fg-muted focus:outline-none"
        >
          <option value="">+ Phiên mới</option>
          {threads.map((t: AiThread) => (
            <option key={t.id} value={t.id}>
              {t.title}
            </option>
          ))}
        </select>
      </div>

      {/* Nội dung chính */}
      {state.activeTab === 'actions' ? (
        <div className="flex-1 overflow-y-auto p-3.5 space-y-3">
          {actions.length === 0 ? (
            <div className="py-12 text-center text-xs text-fg-muted">
              Chưa có đề xuất nào trong phiên này. Hãy yêu cầu AI phân tích hoặc tối ưu chiến dịch.
            </div>
          ) : (
            actions.map((act) => (
              <ActionCardRouter
                key={act.id}
                action={act}
                onConfirm={async (id, editedArgs) => {
                  await confirmActionMutation.mutateAsync({ id, args: editedArgs });
                }}
                onReject={async (id) => {
                  await rejectActionMutation.mutateAsync(id);
                }}
              />
            ))
          )}
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <ChatView
            messages={messages}
            isStreaming={isStreaming}
            phase={phase}
            queuePosition={queuePosition}
            onSelectPrompt={(tpl) => setComposerText(tpl)}
            onRegenerate={(msgId) => regenerateMessage(msgId)}
            onSelectAction={() => setCopilotState({ activeTab: 'actions' })}
            onRetryLast={() => {
              const lastAsst = [...messages].reverse().find((m) => m.role === 'ASSISTANT');
              if (lastAsst) regenerateMessage(lastAsst.id);
            }}
          />

          <Composer
            value={composerText}
            onChange={setComposerText}
            onSend={handleSend}
            onStop={stopStreaming}
            isStreaming={isStreaming}
            attachedCampaignId={state.campaignId}
            onSelectCampaign={(cid) => setCopilotState({ campaignId: cid, campaignName: undefined })}
          />
        </div>
      )}
    </aside>
  );
}
