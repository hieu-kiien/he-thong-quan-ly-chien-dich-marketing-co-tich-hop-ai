import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

/**
 * Khung ứng dụng: Sidebar trái + Topbar + vùng nội dung.
 * Vùng <main> không có padding: trang thường dùng <PageContainer>, còn /assistant
 * dùng toàn bộ chiều cao/chiều rộng với bố cục 3 cột riêng (`h-full`).
 */
export function AppLayout() {
  const location = useLocation();
  const fullBleed = location.pathname.startsWith('/assistant');
  return (
    <div className="flex h-screen overflow-hidden bg-canvas">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[70] focus:rounded-md focus:bg-surface focus:px-3 focus:py-2 focus:text-sm focus:shadow-overlay"
      >
        Bỏ qua tới nội dung chính
      </a>
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main
          id="main"
          tabIndex={-1}
          className={fullBleed ? 'min-h-0 flex-1 overflow-hidden' : 'min-h-0 flex-1 overflow-y-auto focus:outline-none'}
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
