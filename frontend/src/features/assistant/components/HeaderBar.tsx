import {
  useState,
  type KeyboardEvent,
} from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  Layers,
  Megaphone,
  Menu,
  Pencil,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import type { AiThread, AssistantStatus } from '@/lib/types';
import { Popover } from '@/components/ui';
import { isSimulatorActive } from '../simulator';

interface HeaderBarProps {
  currentThread?: AiThread | null;
  status?: AssistantStatus | null;
  proposedCount: number;
  onRenameThread?: (newTitle: string) => Promise<void>;
  onToggleSidebar: () => void;
  onToggleActionsPanel: () => void;
  isActionsPanelOpen: boolean;
}

export function HeaderBar({
  currentThread,
  status,
  proposedCount,
  onRenameThread,
  onToggleSidebar,
  onToggleActionsPanel,
  isActionsPanelOpen,
}: HeaderBarProps) {
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleValue, setTitleValue] = useState(currentThread?.title || '');

  const handleStartEdit = () => {
    if (!currentThread) return;
    setTitleValue(currentThread.title || '');
    setIsEditingTitle(true);
  };

  const handleSaveTitle = async () => {
    if (currentThread && titleValue.trim() && titleValue.trim() !== currentThread.title) {
      await onRenameThread?.(titleValue.trim());
    }
    setIsEditingTitle(false);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveTitle();
    } else if (e.key === 'Escape') {
      setIsEditingTitle(false);
    }
  };

  // Trạng thái AI runner
  const isAvailable = status?.available ?? true;
  const queueLength = status?.queue_length ?? 0;
  const lastError = status?.last_error;

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-4 shadow-xs">
      {/* Vùng bên trái: Nút mở sidebar + Tiêu đề phiên + Chip chiến dịch */}
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="rounded-md p-1.5 text-fg-subtle hover:bg-subtle hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          title="Đóng / mở danh sách phiên"
          aria-label="Đóng mở danh sách phiên"
        >
          <Menu className="h-4 w-4" aria-hidden />
        </button>

        <div className="flex min-w-0 items-center gap-2">
          {currentThread ? (
            isEditingTitle ? (
              <input
                type="text"
                value={titleValue}
                onChange={(e) => setTitleValue(e.target.value)}
                onBlur={handleSaveTitle}
                onKeyDown={handleKeyDown}
                autoFocus
                className="max-w-[200px] rounded border border-accent bg-surface px-2 py-0.5 text-sm font-semibold text-fg sm:max-w-[320px] focus:outline-none"
              />
            ) : (
              <div className="group flex items-center gap-1.5">
                <h1 className="max-w-[180px] truncate text-sm font-semibold text-fg sm:max-w-[300px] lg:max-w-[450px]">
                  {currentThread.title || 'Phiên mới'}
                </h1>
                <button
                  type="button"
                  onClick={handleStartEdit}
                  className="rounded p-1 text-fg-subtle opacity-0 transition-opacity hover:bg-subtle hover:text-fg group-hover:opacity-100 focus:opacity-100"
                  title="Đổi tên phiên"
                  aria-label="Đổi tên phiên"
                >
                  <Pencil className="h-3 w-3" aria-hidden />
                </button>
              </div>
            )
          ) : (
            <h1 className="text-sm font-semibold text-fg">Phiên làm việc mới</h1>
          )}

          {currentThread?.campaign && (
            <Link
              to={`/campaigns/${currentThread.campaign.id}`}
              className="hidden items-center gap-1 rounded-md border border-accent/30 bg-accent-soft px-2 py-0.5 text-[11px] font-medium text-accent-soft-fg hover:underline sm:inline-flex"
              title="Xem chiến dịch được gắn"
            >
              <Megaphone className="h-3 w-3" aria-hidden />
              <span className="max-w-[150px] truncate">{currentThread.campaign.name}</span>
            </Link>
          )}
        </div>
      </div>

      {/* Vùng bên phải: Nhãn mô phỏng + Trạng thái AI dot + Nút mở Actions panel */}
      <div className="flex items-center gap-3">
        {/* Nhãn mô phỏng (chỉ hiện khi DEV và VITE_ASSISTANT_SIMULATOR=true) */}
        {import.meta.env.DEV && isSimulatorActive && (
          <span className="hidden rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[11px] font-medium text-amber-700 dark:text-amber-300 md:inline-block">
            Mô phỏng (chỉ dùng khi phát triển)
          </span>
        )}

        {/* Chấm tròn báo trạng thái AI */}
        <Popover
          trigger={(props) => (
            <button
              type="button"
              {...props}
              className="flex items-center gap-1.5 rounded-full px-2 py-1 text-xs text-fg-subtle hover:bg-subtle focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
              aria-label="Trạng thái hệ thống AI"
            >
              <span
                className={cn(
                  'h-2 w-2 rounded-full',
                  !isAvailable
                    ? 'bg-danger'
                    : queueLength > 0
                      ? 'bg-warning animate-pulse'
                      : 'bg-success',
                )}
              />
              <span className="hidden text-[11px] text-fg-muted sm:inline">
                {!isAvailable ? 'AI lỗi' : queueLength > 0 ? `Hàng đợi (${queueLength})` : 'AI sẵn sàng'}
              </span>
            </button>
          )}
          className="w-64 p-3 text-xs"
        >
          {() => (
            <div className="space-y-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-fg">
                {!isAvailable ? (
                  <>
                    <AlertCircle className="h-4 w-4 text-danger" aria-hidden />
                    <span>Dịch vụ AI không khả dụng</span>
                  </>
                ) : queueLength > 0 ? (
                  <>
                    <Clock className="h-4 w-4 text-warning" aria-hidden />
                    <span>Đang có hàng đợi xử lý</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4 text-success" aria-hidden />
                    <span>Hệ thống AI hoạt động bình thường</span>
                  </>
                )}
              </div>

              <div className="text-[11px] text-fg-muted">
                {status?.runner?.model && (
                  <div>Mô hình: <span className="font-mono">{status.runner.model}</span></div>
                )}
                {queueLength > 0 && <div>Lượt đang đợi: {queueLength}</div>}
                {lastError && (
                  <div className="mt-1 rounded bg-danger-soft p-1.5 text-danger-soft-fg">
                    Lỗi gần nhất: {lastError}
                  </div>
                )}
              </div>
            </div>
          )}
        </Popover>

        {/* Nút bật tắt panel Đề xuất & bản nháp */}
        <button
          type="button"
          onClick={onToggleActionsPanel}
          className={cn(
            'relative flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
            isActionsPanelOpen
              ? 'border-accent/40 bg-accent-soft text-accent-soft-fg'
              : 'border-border bg-surface text-fg hover:bg-subtle',
          )}
          title="Đề xuất & bản nháp"
          aria-label="Đề xuất & bản nháp"
        >
          <Layers className="h-3.5 w-3.5" aria-hidden />
          <span className="hidden sm:inline">Đề xuất</span>
          {proposedCount > 0 && (
            <span className="flex h-4 min-w-[16px] items-center justify-center rounded-full bg-warning px-1 text-[10px] font-bold text-white">
              {proposedCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}
