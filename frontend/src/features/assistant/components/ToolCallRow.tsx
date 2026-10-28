import { useState } from 'react';
import {
  AlertCircle,
  Check,
  ChevronDown,
  ChevronRight,
  Database,
  Loader2,
  Wrench,
} from 'lucide-react';
import { cn } from '@/lib/cn';
import type { ToolCallStatus } from '@/lib/types';
import { getToolLabel } from '../types';

export interface ToolCallRowProps {
  id?: string;
  name: string;
  args?: Record<string, unknown>;
  status: ToolCallStatus;
  summary?: string | null;
  className?: string;
}

export function ToolCallRow({
  name,
  args = {},
  status,
  summary,
  className,
}: ToolCallRowProps) {
  const [isOpen, setIsOpen] = useState(false);
  const toolLabel = getToolLabel(name);

  // Biểu tượng theo trạng thái
  const renderStatusIcon = () => {
    switch (status) {
      case 'running':
        return (
          <Loader2
            className="h-3.5 w-3.5 shrink-0 animate-spin text-accent"
            aria-hidden
          />
        );
      case 'done':
        return (
          <div className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-success-soft text-success-soft-fg">
            <Check className="h-2.5 w-2.5" aria-hidden />
          </div>
        );
      case 'error':
        return (
          <AlertCircle
            className="h-3.5 w-3.5 shrink-0 text-danger"
            aria-hidden
          />
        );
      default:
        return null;
    }
  };

  const isQuery =
    name.startsWith('list_') ||
    name.startsWith('get_') ||
    name.includes('stats') ||
    name.includes('banned');

  return (
    <div
      className={cn(
        'my-1.5 overflow-hidden rounded-md border border-border/80 bg-subtle/70 text-xs transition-colors',
        className,
      )}
    >
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left hover:bg-muted/40 focus:outline-none focus-visible:ring-1 focus-visible:ring-accent"
        aria-expanded={isOpen}
      >
        <div className="flex min-w-0 flex-1 items-center gap-2">
          {renderStatusIcon()}
          <span className="shrink-0 text-fg-subtle">
            {isQuery ? (
              <Database className="h-3.5 w-3.5" aria-hidden />
            ) : (
              <Wrench className="h-3.5 w-3.5" aria-hidden />
            )}
          </span>
          <span className="shrink-0 whitespace-nowrap font-medium text-fg">{toolLabel}</span>
          {summary && (
            <span className="min-w-0 truncate text-fg-muted" title={summary}>
              — {summary}
            </span>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1.5 whitespace-nowrap text-fg-subtle">
          <span className="text-[11px]">
            {status === 'running'
              ? 'Đang thực thi'
              : status === 'done'
                ? 'Hoàn tất'
                : 'Thất bại'}
          </span>
          {isOpen ? (
            <ChevronDown className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" aria-hidden />
          )}
        </div>
      </button>

      {isOpen && (
        <div className="border-t border-border/60 bg-surface/80 p-2.5">
          <div className="mb-1 text-[11px] font-semibold text-fg-subtle">
            Tham số đầu vào:
          </div>
          <pre className="overflow-x-auto rounded border border-border/60 bg-subtle p-2 font-mono text-[11px] text-fg">
            {Object.keys(args).length > 0
              ? JSON.stringify(args, null, 2)
              : '// Không có tham số'}
          </pre>
        </div>
      )}
    </div>
  );
}
