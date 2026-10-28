import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import { cn } from '@/lib/cn';

/** Bảng dữ liệu: vùng cuộn ngang có thể focus bằng bàn phím. */
export function Table({ className, children, label }: { className?: string; children: ReactNode; label?: string }) {
  return (
    <div
      className={cn('overflow-x-auto rounded-lg border border-border bg-surface', className)}
      role="region"
      aria-label={label}
      tabIndex={0}
    >
      <table className="w-full border-collapse text-left text-sm">{children}</table>
    </div>
  );
}

export function THead({ children }: { children: ReactNode }) {
  return (
    <thead className="sticky top-0 z-10 border-b border-border bg-subtle/80 text-xs font-medium text-fg-muted backdrop-blur-xs">
      {children}
    </thead>
  );
}

export function TBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-border">{children}</tbody>;
}

export function TR({ className, ...rest }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn('h-11 transition-colors hover:bg-subtle', className)} {...rest} />;
}

export function TH({ className, align, ...rest }: ThHTMLAttributes<HTMLTableCellElement> & { align?: 'left' | 'right' | 'center' }) {
  return (
    <th
      scope="col"
      className={cn(
        'whitespace-nowrap px-3.5 py-2.5 font-medium text-fg-muted',
        align === 'right' && 'text-right',
        align === 'center' && 'text-center',
        className,
      )}
      {...rest}
    />
  );
}

export function TD({ className, align, ...rest }: TdHTMLAttributes<HTMLTableCellElement> & { align?: 'left' | 'right' | 'center' }) {
  return (
    <td
      className={cn(
        'px-3.5 py-2.5 align-middle text-fg tabular-nums',
        align === 'right' && 'text-right tabular',
        align === 'center' && 'text-center',
        className,
      )}
      {...rest}
    />
  );
}

export interface SortableTHProps {
  label: string;
  field: string;
  /** Giá trị sort hiện tại theo CONTRACT §4: "field" hoặc "-field". */
  sort: string | undefined;
  onSort: (sort: string) => void;
  align?: 'left' | 'right';
  className?: string;
}

/** Tiêu đề cột sắp xếp được: bấm lần 1 tăng dần, lần 2 giảm dần. */
export function SortableTH({ label, field, sort, onSort, align, className }: SortableTHProps) {
  const active = sort === field || sort === `-${field}`;
  const desc = sort === `-${field}`;
  const Icon = !active ? ArrowUpDown : desc ? ArrowDown : ArrowUp;
  return (
    <th
      scope="col"
      aria-sort={active ? (desc ? 'descending' : 'ascending') : 'none'}
      className={cn('whitespace-nowrap px-3 py-2.5 font-medium', align === 'right' && 'text-right', className)}
    >
      <button
        type="button"
        onClick={() => onSort(active && !desc ? `-${field}` : field)}
        className={cn('inline-flex items-center gap-1 rounded hover:text-fg', active && 'text-fg')}
      >
        {label}
        <Icon className="h-3.5 w-3.5" aria-hidden />
      </button>
    </th>
  );
}
