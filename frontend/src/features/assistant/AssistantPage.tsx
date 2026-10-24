import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { assistantApi } from '@/lib/api/endpoints';
import { useDocumentTitle } from '@/lib/hooks';
import type { AiThread } from '@/lib/types';
import { Drawer, useToast } from '@/components/ui';
import { ActionsPanel } from './components/ActionsPanel';
import { ChatView } from './components/ChatView';
import { Composer } from './components/Composer';
import { HeaderBar } from './components/HeaderBar';
import { ThreadList } from './components/ThreadList';
import { useAssistantStream } from './useAssistantStream';

export default function AssistantPage() {
  useDocumentTitle('Trợ lý AI — MarketFlow');
  const navigate = useNavigate();
  const { threadId: threadIdParam } = useParams();
  const [searchParams] = useSearchParams();
  const campaignIdQuery = searchParams.get('campaign_id');
  const queryClient = useQueryClient();
  const toast = useToast();

  const currentThreadId = threadIdParam ? parseInt(threadIdParam, 10) : undefined;

  // Trạng thái giao diện
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isActionsPanelOpen, setIsActionsPanelOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isMobileActionsOpen, setIsMobileActionsOpen] = useState(false);
  const [composerText, setComposerText] = useState('');
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(
    campaignIdQuery ? parseInt(campaignIdQuery, 10) : null,
  );
  const [highlightedActionId, setHighlightedActionId] = useState<number | null>(null);

  // 1. Lấy danh sách phiên
  const { data: threads = [] } = useQuery({
    queryKey: ['assistant', 'threads'],
    queryFn: () => assistantApi.listThreads(),
  });

  // 2. Lấy trạng thái hệ thống AI
  const { data: statusData } = useQuery({
    queryKey: ['assistant', 'status'],
    queryFn: () => assistantApi.status(),
    refetchInterval: 30_000,
  });

  // 3. Lấy thông tin phiên hiện tại
  const currentThread = threads.find((t: AiThread) => t.id === currentThreadId) || null;

  // 4. Lấy danh sách tin nhắn của phiên hiện tại
  const { data: messages = [] } = useQuery({
    queryKey: ['assistant', 'messages', currentThreadId],
    queryFn: () => (currentThreadId ? assistantApi.messages(currentThreadId) : Promise.resolve([])),
    enabled: Boolean(currentThreadId),
  });

  // 5. Lấy danh sách hành động (ai_actions) của phiên hiện tại
  const { data: actions = [] } = useQuery({
    queryKey: ['assistant', 'actions', currentThreadId],
    queryFn: () =>
      currentThreadId
        ? assistantApi.listActions({ thread_id: currentThreadId })
        : Promise.resolve([]),
    enabled: Boolean(currentThreadId),
  });

  // Hook điều khiển luồng streaming
  const {
    isStreaming,
    phase,
    queuePosition,
    sendMessage,
    regenerateMessage,
    stopStreaming,
  } = useAssistantStream(currentThreadId);

  // Xử lý khi có query param ?campaign_id=<id> (§5): tạo phiên mới gắn chiến dịch
  useEffect(() => {
    if (campaignIdQuery && !currentThreadId) {
      const cid = parseInt(campaignIdQuery, 10);
      if (!Number.isNaN(cid)) {
        assistantApi
          .createThread({ campaign_id: cid, title: `Chiến dịch #${cid}` })
          .then((newThread) => {
            queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
            navigate(`/assistant/${newThread.id}`, { replace: true });
          })
          .catch((err) => {
            toast.error(err instanceof Error ? err.message : 'Không thể khởi tạo phiên cho chiến dịch.');
          });
      }
    }
  }, [campaignIdQuery, currentThreadId, navigate, queryClient, toast]);

  // Cập nhật selectedCampaignId khi currentThread thay đổi
  useEffect(() => {
    if (currentThread) {
      setSelectedCampaignId(currentThread.campaign_id);
    }
  }, [currentThread]);

  // Mutation: Tạo phiên mới
  const createThreadMutation = useMutation({
    mutationFn: (data: { title?: string; campaign_id?: number | null }) =>
      assistantApi.createThread(data),
    onSuccess: (newThread) => {
      queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
      navigate(`/assistant/${newThread.id}`);
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Không thể tạo phiên mới.');
    },
  });

  // Mutation: Đổi tên phiên
  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: number; title: string }) =>
      assistantApi.updateThread(id, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
      toast.success('Đã đổi tên phiên.');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Không thể đổi tên phiên.');
    },
  });

  // Mutation: Ghim/Bỏ ghim
  const pinMutation = useMutation({
    mutationFn: ({ id, pinned }: { id: number; pinned: boolean }) =>
      assistantApi.updateThread(id, { pinned }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Lỗi khi cập nhật ghim.');
    },
  });

  // Mutation: Xoá phiên
  const deleteMutation = useMutation({
    mutationFn: (id: number) => assistantApi.deleteThread(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
      toast.success('Đã xoá phiên.');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Không thể xoá phiên.');
    },
  });

  // Mutation: Đổi ngữ cảnh chiến dịch cho phiên
  const attachCampaignMutation = useMutation({
    mutationFn: ({ id, campaign_id }: { id: number; campaign_id: number | null }) =>
      assistantApi.updateThread(id, { campaign_id }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
      toast.success('Đã cập nhật ngữ cảnh chiến dịch.');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Không thể gắn chiến dịch.');
    },
  });

  // Mutation: Xác nhận hành động (ai_action)
  const confirmActionMutation = useMutation({
    mutationFn: ({ id, args }: { id: number; args?: Record<string, unknown> }) =>
      assistantApi.confirmAction(id, { args }),
    onSuccess: () => {
      if (currentThreadId) {
        queryClient.invalidateQueries({ queryKey: ['assistant', 'actions', currentThreadId] });
      }
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
      toast.success('Đã xác nhận và thực thi đề xuất thành công.');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Không thể xác nhận đề xuất.');
    },
  });

  // Mutation: Bỏ qua hành động (ai_action)
  const rejectActionMutation = useMutation({
    mutationFn: (id: number) => assistantApi.rejectAction(id),
    onSuccess: () => {
      if (currentThreadId) {
        queryClient.invalidateQueries({ queryKey: ['assistant', 'actions', currentThreadId] });
      }
      toast.info('Đã bỏ qua đề xuất.');
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Lỗi khi bỏ qua đề xuất.');
    },
  });

  // Gửi tin nhắn từ Composer
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isStreaming) return;

    if (!currentThreadId) {
      // Đang ở route /assistant (chưa có thread): tự động tạo thread mới trước
      const titlePrompt = text.trim().slice(0, 36) + (text.length > 36 ? '...' : '');
      try {
        const newThread = await assistantApi.createThread({
          title: titlePrompt,
          campaign_id: selectedCampaignId,
        });
        queryClient.invalidateQueries({ queryKey: ['assistant', 'threads'] });
        setComposerText('');
        navigate(`/assistant/${newThread.id}`);
        await sendMessage(text, newThread.id);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Không thể khởi tạo phiên mới.');
      }
      return;
    }

    setComposerText('');
    await sendMessage(text);
  };

  // Chọn mẫu câu lệnh nhanh
  const handleSelectQuickPrompt = (template: string) => {
    setComposerText(template);
  };

  // Chọn action từ tin nhắn -> mở panel và highlight
  const handleSelectActionFromMessage = (actionId: number) => {
    setHighlightedActionId(actionId);
    if (window.innerWidth < 1280) {
      setIsMobileActionsOpen(true);
    } else {
      setIsActionsPanelOpen(true);
    }
  };

  // Gắn/gỡ chiến dịch
  const handleSelectCampaign = (cId: number | null) => {
    setSelectedCampaignId(cId);
    if (currentThreadId) {
      attachCampaignMutation.mutate({ id: currentThreadId, campaign_id: cId });
    }
  };

  const proposedCount = actions.filter((a) => a.status === 'PROPOSED').length;

  // Panel "Đề xuất & bản nháp" mặc định đóng để khung chat đủ rộng;
  // tự mở khi phiên có đề xuất đang chờ xác nhận (khi mở phiên hoặc khi AI vừa tạo đề xuất mới).
  useEffect(() => {
    if (proposedCount > 0) setIsActionsPanelOpen(true);
  }, [proposedCount, currentThreadId]);

  return (
    <div className="flex h-full w-full overflow-hidden bg-canvas">
      {/* CỘT TRÁI (Desktop): Danh sách phiên (~260px) */}
      {isSidebarOpen && (
        <div className="hidden lg:block lg:w-64 xl:w-72 shrink-0 h-full">
          <ThreadList
            threads={threads}
            activeThreadId={currentThreadId}
            onSelectThread={(id) => navigate(`/assistant/${id}`)}
            onNewThread={() => navigate('/assistant')}
            onRenameThread={async (id, title) => {
              await renameMutation.mutateAsync({ id, title });
            }}
            onTogglePinThread={async (id, pinned) => {
              await pinMutation.mutateAsync({ id, pinned: !pinned });
            }}
            onDeleteThread={async (id) => {
              await deleteMutation.mutateAsync(id);
            }}
          />
        </div>
      )}

      {/* CỘT TRÁI (Mobile / Tablet Drawer): Danh sách phiên */}
      <Drawer
        open={isMobileSidebarOpen}
        onClose={() => setIsMobileSidebarOpen(false)}
        title="Phiên làm việc"
        width="md"
      >
        <div className="-mx-6 -my-5 h-full">
          <ThreadList
            threads={threads}
            activeThreadId={currentThreadId}
            onSelectThread={(id) => {
              navigate(`/assistant/${id}`);
              setIsMobileSidebarOpen(false);
            }}
            onNewThread={() => {
              navigate('/assistant');
              setIsMobileSidebarOpen(false);
            }}
            onRenameThread={async (id, title) => {
              await renameMutation.mutateAsync({ id, title });
            }}
            onTogglePinThread={async (id, pinned) => {
              await pinMutation.mutateAsync({ id, pinned: !pinned });
            }}
            onDeleteThread={async (id) => {
              await deleteMutation.mutateAsync(id);
            }}
            onCloseMobile={() => setIsMobileSidebarOpen(false)}
          />
        </div>
      </Drawer>

      {/* CỘT GIỮA: Header + ChatView + Composer */}
      <div className="flex min-w-0 flex-1 flex-col h-full overflow-hidden">
        <HeaderBar
          currentThread={currentThread}
          status={statusData}
          proposedCount={proposedCount}
          onRenameThread={async (title) => {
            if (currentThreadId) {
              await renameMutation.mutateAsync({ id: currentThreadId, title });
            }
          }}
          onToggleSidebar={() => {
            if (window.innerWidth < 1024) {
              setIsMobileSidebarOpen(true);
            } else {
              setIsSidebarOpen((prev) => !prev);
            }
          }}
          onToggleActionsPanel={() => {
            if (window.innerWidth < 1280) {
              setIsMobileActionsOpen(true);
            } else {
              setIsActionsPanelOpen((prev) => !prev);
            }
          }}
          isActionsPanelOpen={isActionsPanelOpen}
        />

        <ChatView
          messages={messages}
          isStreaming={isStreaming}
          phase={phase}
          queuePosition={queuePosition}
          onSelectPrompt={handleSelectQuickPrompt}
          onRegenerate={(msgId) => regenerateMessage(msgId)}
          onSelectAction={handleSelectActionFromMessage}
          onRetryLast={() => {
            const lastUserMsg = [...messages].reverse().find((m) => m.role === 'USER');
            if (lastUserMsg) {
              sendMessage(lastUserMsg.content);
            }
          }}
        />

        <Composer
          value={composerText}
          onChange={setComposerText}
          onSend={handleSendMessage}
          onStop={stopStreaming}
          isStreaming={isStreaming}
          attachedCampaignId={selectedCampaignId}
          onSelectCampaign={handleSelectCampaign}
          disabled={createThreadMutation.isPending}
        />
      </div>

      {/* CỘT PHẢI (Desktop): Đề xuất & bản nháp (~380px) */}
      {isActionsPanelOpen && (
        <div className="hidden xl:block xl:w-96 2xl:w-[420px] shrink-0 h-full">
          <ActionsPanel
            actions={actions}
            onConfirmAction={async (actionId, args) => {
              await confirmActionMutation.mutateAsync({ id: actionId, args });
            }}
            onRejectAction={async (actionId) => {
              await rejectActionMutation.mutateAsync(actionId);
            }}
            onClose={() => setIsActionsPanelOpen(false)}
            highlightedActionId={highlightedActionId}
          />
        </div>
      )}

      {/* CỘT PHẢI (Mobile / Tablet Drawer): Đề xuất & bản nháp */}
      <Drawer
        open={isMobileActionsOpen}
        onClose={() => setIsMobileActionsOpen(false)}
        title="Đề xuất & bản nháp"
        width="lg"
      >
        <div className="-mx-6 -my-5 h-full">
          <ActionsPanel
            actions={actions}
            onConfirmAction={async (actionId, args) => {
              await confirmActionMutation.mutateAsync({ id: actionId, args });
            }}
            onRejectAction={async (actionId) => {
              await rejectActionMutation.mutateAsync(actionId);
            }}
            highlightedActionId={highlightedActionId}
          />
        </div>
      </Drawer>
    </div>
  );
}
