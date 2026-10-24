import {
  useState,
  type KeyboardEvent,
} from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Megaphone,
  MoreVertical,
  Pencil,
  Pin,
  PinOff,
  Plus,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import type { AiThread } from '@/lib/types';
import { Button, ConfirmDialog } from '@/components/ui';

interface ThreadListProps {
  threads: AiThread[];
  activeThreadId?: number | null;
  onSelectThread: (threadId: number) => void;
  onNewThread: () => void;
  onRenameThread: (threadId: number, newTitle: string) => Promise<void>;
  onTogglePinThread: (threadId: number, currentPinned: boolean) => Promise<void>;
  onDeleteThread: (threadId: number) => Promise<void>;
  className?: string;
  onCloseMobile?: () => void;
}

export function ThreadList({
  threads,
  activeThreadId,
  onSelectThread,
  onNewThread,
  onRenameThread,
  onTogglePinThread,
  onDeleteThread,
  className,
  onCloseMobile,
}: ThreadListProps) {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [renamingThreadId, setRenamingThreadId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [threadToDelete, setThreadToDelete] = useState<AiThread | null>(null);
  const [openMenuThreadId, setOpenMenuThreadId] = useState<number | null>(null);

  // Lọc theo từ khoá tìm kiếm
  const filteredThreads = threads.filter((t) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const titleMatch = t.title.toLowerCase().includes(q);
    const campaignMatch = t.campaign?.name?.toLowerCase().includes(q);
    return titleMatch || campaignMatch;
  });

  // Phân nhóm theo: Ghim / Hôm nay / 7 ngày qua / Cũ hơn
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const sevenDaysAgo = startOfToday - 7 * 24 * 60 * 60 * 1000;

  const pinnedThreads: AiThread[] = [];
  const todayThreads: AiThread[] = [];
  const last7DaysThreads: AiThread[] = [];
  const olderThreads: AiThread[] = [];

  for (const t of filteredThreads) {
    if (t.pinned) {
      pinnedThreads.push(t);
      continue;
    }
    const tTime = new Date(t.last_message_at || t.created_at).getTime();
    if (tTime >= startOfToday) {
      todayThreads.push(t);
    } else if (tTime >= sevenDaysAgo) {
      last7DaysThreads.push(t);
    } else {
      olderThreads.push(t);
    }
  }

  const handleStartRename = (thread: AiThread) => {
    setRenamingThreadId(thread.id);
    setRenameValue(thread.title);
    setOpenMenuThreadId(null);
  };

  const handleSaveRename = async (threadId: number) => {
    if (renameValue.trim()) {
      await onRenameThread(threadId, renameValue.trim());
    }
    setRenamingThreadId(null);
  };

  const handleRenameKeyDown = (e: KeyboardEvent<HTMLInputElement>, threadId: number) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveRename(threadId);
    } else if (e.key === 'Escape') {
      setRenamingThreadId(null);
    }
  };

  const renderThreadItem = (thread: AiThread) => {
    const isActive = thread.id === activeThreadId;
    const isRenaming = thread.id === renamingThreadId;
    const isMenuOpen = thread.id === openMenuThreadId;

    return (
      <div
        key={thread.id}
        className={cn(
          'group relative flex items-center justify-between rounded-lg px-2.5 py-2 text-xs transition-colors',
          isActive
            ? 'bg-subtle font-medium text-fg shadow-xs border border-border-strong'
            : 'text-fg-muted hover:bg-subtle/70 hover:text-fg',
        )}
      >
        {isRenaming ? (
          <div className="flex w-full items-center gap-1">
            <input
              type="text"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onBlur={() => handleSaveRename(thread.id)}
              onKeyDown={(e) => handleRenameKeyDown(e, thread.id)}
              autoFocus
              className="w-full rounded border border-accent bg-surface px-1.5 py-0.5 text-xs text-fg focus:outline-none"
            />
          </div>
        ) : (
          <button
            type="button"
            onClick={() => {
              onSelectThread(thread.id);
              onCloseMobile?.();
            }}
            className="flex min-w-0 flex-1 flex-col text-left focus:outline-none"
          >
            <div className="flex items-center gap-1.5">
              {thread.pinned && (
                <Pin className="h-3 w-3 shrink-0 text-accent" aria-hidden />
              )}
              <span className="truncate">{thread.title || 'Phiên chưa đặt tên'}</span>
            </div>
            {thread.campaign && (
              <div className="mt-0.5 flex items-center gap-1 text-[10px] text-fg-subtle">
                <Megaphone className="h-2.5 w-2.5 shrink-0" aria-hidden />
                <span className="truncate">{thread.campaign.name}</span>
              </div>
            )}
          </button>
        )}

        {/* Nút menu 3 chấm khi hover hoặc active */}
        {!isRenaming && (
          <div className="relative shrink-0">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpenMenuThreadId(isMenuOpen ? null : thread.id);
              }}
              className={cn(
                'rounded p-1 text-fg-subtle hover:bg-muted hover:text-fg focus:outline-none',
                isMenuOpen || isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
              )}
              aria-label="Tuỳ chọn phiên"
            >
              <MoreVertical className="h-3.5 w-3.5" aria-hidden />
            </button>

            {isMenuOpen && (
              <div
                role="menu"
                tabIndex={-1}
                className="absolute right-0 top-full z-30 mt-1 w-36 rounded-md border border-border bg-surface p-1 shadow-overlay animate-scale-in"
                onMouseDown={(e) => e.stopPropagation()}
              >
                <button
                  type="button"
                  onClick={() => handleStartRename(thread)}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-fg hover:bg-subtle"
                >
                  <Pencil className="h-3 w-3 text-fg-muted" aria-hidden />
                  <span>Đổi tên</span>
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    setOpenMenuThreadId(null);
                    await onTogglePinThread(thread.id, thread.pinned);
                  }}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-fg hover:bg-subtle"
                >
                  {thread.pinned ? (
                    <>
                      <PinOff className="h-3 w-3 text-fg-muted" aria-hidden />
                      <span>Bỏ ghim</span>
                    </>
                  ) : (
                    <>
                      <Pin className="h-3 w-3 text-fg-muted" aria-hidden />
                      <span>Ghim phiên</span>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setOpenMenuThreadId(null);
                    setThreadToDelete(thread);
                  }}
                  className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-danger hover:bg-danger-soft"
                >
                  <Trash2 className="h-3 w-3" aria-hidden />
                  <span>Xoá phiên</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderGroup = (title: string, groupThreads: AiThread[]) => {
    if (groupThreads.length === 0) return null;
    return (
      <div className="mb-4">
        <div className="mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-wider text-fg-subtle">
          {title}
        </div>
        <div className="space-y-0.5">{groupThreads.map(renderThreadItem)}</div>
      </div>
    );
  };

  return (
    <aside
      className={cn(
        'flex h-full flex-col border-r border-border bg-surface shadow-xs',
        className,
      )}
      aria-label="Danh sách phiên hội thoại"
    >
      {/* Header bên trái: Tiêu đề + Nút Phiên mới */}
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-3.5">
        <h2 className="text-sm font-semibold text-fg">Phiên làm việc</h2>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            onNewThread();
            onCloseMobile?.();
          }}
          className="h-8 gap-1 px-2.5 text-xs"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden />
          <span>Phiên mới</span>
        </Button>
      </div>

      {/* Ô tìm kiếm phiên */}
      <div className="p-3">
        <div className="relative">
          <Search
            className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-fg-subtle"
            aria-hidden
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm phiên..."
            className="w-full rounded-md border border-border bg-subtle py-1.5 pl-8 pr-7 text-xs text-fg placeholder:text-fg-subtle focus:border-accent focus:bg-surface focus:outline-none focus:ring-1 focus:ring-accent"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-fg-subtle hover:text-fg"
              aria-label="Xoá tìm kiếm"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          )}
        </div>
      </div>

      {/* Danh sách các nhóm phiên */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {filteredThreads.length === 0 ? (
          <div className="py-8 text-center text-xs text-fg-subtle">
            {searchQuery ? 'Không tìm thấy phiên phù hợp' : 'Chưa có phiên hội thoại nào'}
          </div>
        ) : (
          <>
            {renderGroup('Đã ghim', pinnedThreads)}
            {renderGroup('Hôm nay', todayThreads)}
            {renderGroup('7 ngày qua', last7DaysThreads)}
            {renderGroup('Cũ hơn', olderThreads)}
          </>
        )}
      </div>

      {/* Hộp thoại xác nhận xoá phiên */}
      <ConfirmDialog
        open={Boolean(threadToDelete)}
        onClose={() => setThreadToDelete(null)}
        onConfirm={async () => {
          if (threadToDelete) {
            await onDeleteThread(threadToDelete.id);
            setThreadToDelete(null);
            if (activeThreadId === threadToDelete.id) {
              navigate('/assistant');
            }
          }
        }}
        title="Xoá phiên hội thoại"
        description={`Bạn có chắc chắn muốn xoá phiên "${threadToDelete?.title}"? Toàn bộ tin nhắn và đề xuất trong phiên này sẽ bị xoá vĩnh viễn.`}
        confirmLabel="Xoá vĩnh viễn"
        cancelLabel="Giữ lại"
        destructive
      />
    </aside>
  );
}
