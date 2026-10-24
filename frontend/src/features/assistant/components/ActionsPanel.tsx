import { useEffect } from 'react';
import { Layers, X } from 'lucide-react';
import { cn } from '@/lib/cn';
import type { AiAction } from '@/lib/types';
import { Badge, EmptyState } from '@/components/ui';
import { ActionCardRouter } from './ActionCards';

interface ActionsPanelProps {
  actions: AiAction[];
  onConfirmAction: (actionId: number, editedArgs: Record<string, unknown>) => Promise<void>;
  onRejectAction: (actionId: number) => Promise<void>;
  onClose?: () => void;
  highlightedActionId?: number | null;
  className?: string;
}

export function ActionsPanel({
  actions,
  onConfirmAction,
  onRejectAction,
  onClose,
  highlightedActionId,
  className,
}: ActionsPanelProps) {
  const proposedCount = actions.filter((a) => a.status === 'PROPOSED').length;

  // Tự động cuộn đến thẻ hành động khi người dùng bấm vào chip trong tin nhắn
  useEffect(() => {
    if (highlightedActionId) {
      const el = document.getElementById(`action-${highlightedActionId}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [highlightedActionId]);

  return (
    <aside
      className={cn(
        'flex h-full flex-col border-l border-border bg-surface shadow-xs',
        className,
      )}
      aria-label="Panel đề xuất và bản nháp"
    >
      {/* Header của panel */}
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-accent" aria-hidden />
          <h2 className="text-sm font-semibold text-fg">Đề xuất & bản nháp</h2>
          {proposedCount > 0 && (
            <Badge tone="warning">
              {proposedCount} chờ xác nhận
            </Badge>
          )}
        </div>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-fg-subtle hover:bg-subtle hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            title="Đóng panel"
            aria-label="Đóng panel"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        )}
      </div>

      {/* Vùng danh sách thẻ đề xuất */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {actions.length === 0 ? (
          <EmptyState
            icon={<Layers />}
            title="Chưa có đề xuất nào"
            description="Khi Trợ lý AI tạo đề xuất nội dung, chiến dịch hay số liệu, chúng sẽ xuất hiện tại đây để bạn kiểm tra, chỉnh sửa và xác nhận."
            className="py-12"
          />
        ) : (
          actions.map((act) => (
            <ActionCardRouter
              key={act.id}
              action={act}
              onConfirm={onConfirmAction}
              onReject={onRejectAction}
              highlighted={highlightedActionId === act.id}
            />
          ))
        )}
      </div>
    </aside>
  );
}
