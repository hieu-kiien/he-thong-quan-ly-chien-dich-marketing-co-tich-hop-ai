import { Outlet, useLocation } from 'react-router-dom';
import { CopilotDrawer } from '@/features/assistant/CopilotDrawer';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

/**
 * Khung ứng dụng: Bố cục 3 Cột Linh Hoạt (Collapsible Split-Pane):
 * 1. Cột trái: Sidebar điều hướng (240px <-> 64px).
 * 2. Khu vực trung tâm: Main Workspace.
 * 3. Cột phải: Contextual AI Copilot Drawer (380px - 410px, phím tắt Ctrl + K / Cmd + J).
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
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <main
            id="main"
            tabIndex={-1}
            className={fullBleed ? 'min-h-0 flex-1 overflow-hidden' : 'min-h-0 flex-1 overflow-y-auto focus:outline-none'}
          >
            <Outlet />
          </main>
          <CopilotDrawer />
        </div>
      </div>
    </div>
  );
}
