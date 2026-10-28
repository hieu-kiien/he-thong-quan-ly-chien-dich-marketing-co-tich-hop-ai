import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

/** Khung nội dung mở rộng toàn bộ chiều ngang màn hình làm việc để hạn chế tối đa thanh trượt. */
export function PageContainer({ children, className }: { children: ReactNode; className?: string; wide?: boolean }) {
  return <div className={cn('w-full max-w-none px-5 py-5 lg:px-7', className)}>{children}</div>;
}
