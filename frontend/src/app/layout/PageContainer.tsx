import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

/** Khung nội dung chuẩn cho các trang thường (không dùng cho /assistant). */
export function PageContainer({ children, className, wide }: { children: ReactNode; className?: string; wide?: boolean }) {
  return <div className={cn('mx-auto w-full px-4 py-6 md:px-6 lg:px-8', wide ? 'max-w-[90rem]' : 'max-w-7xl', className)}>{children}</div>;
}
