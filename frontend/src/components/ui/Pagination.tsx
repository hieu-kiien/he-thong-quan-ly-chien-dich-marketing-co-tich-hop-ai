import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/cn';
import { formatNumber } from '@/lib/format';
import { IconButton } from './Button';

export interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  className?: string;
}

const SIZES = [10, 20, 50, 100];

export function Pagination({ page, pageSize, total, onPageChange, onPageSizeChange, className }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);
  return (
    <nav
      aria-label="Phân trang"
      className={cn('flex flex-wrap items-center justify-between gap-3 text-[0.8125rem] text-fg-muted', className)}
    >
      <p className="tabular">
        {formatNumber(from)}–{formatNumber(to)} trên {formatNumber(total)}
      </p>
      <div className="flex items-center gap-3">
        {onPageSizeChange && (
          <label className="flex items-center gap-2">
            <span>Số dòng</span>
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="h-8 rounded-md border border-border-strong bg-surface px-2 text-[0.8125rem] text-fg"
            >
              {SIZES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        )}
        <div className="flex items-center gap-1">
          <IconButton label="Trang trước" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </IconButton>
          <span className="min-w-[4.5rem] text-center tabular">
            Trang {page}/{pages}
          </span>
          <IconButton label="Trang sau" size="sm" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>
            <ChevronRight className="h-4 w-4" />
          </IconButton>
        </div>
      </div>
    </nav>
  );
}
