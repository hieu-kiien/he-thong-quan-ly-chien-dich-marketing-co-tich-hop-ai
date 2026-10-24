import { Link, isRouteErrorResponse, useRouteError } from 'react-router-dom';
import { FileQuestion, AlertTriangle } from 'lucide-react';
import { EmptyState } from '@/components/ui';

export function NotFoundPage() {
  return (
    <EmptyState
      icon={<FileQuestion />}
      title="Không tìm thấy trang"
      description="Đường dẫn không tồn tại hoặc đã bị thay đổi."
      action={
        <Link to="/" className="text-sm font-medium text-accent hover:underline">
          Về trang Tổng quan
        </Link>
      }
      className="mt-16"
    />
  );
}

export function RouteErrorPage() {
  const error = useRouteError();
  const message = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : 'Đã có lỗi không mong muốn.';
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas p-6">
      <EmptyState
        icon={<AlertTriangle />}
        title="Ứng dụng gặp lỗi"
        description={message}
        action={
          <a href="/" className="text-sm font-medium text-accent hover:underline">
            Tải lại trang
          </a>
        }
      />
    </div>
  );
}
