import type { ReactNode } from 'react';
import { createBrowserRouter, Navigate, Outlet, useLocation } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { isManager } from '@/lib/permissions';
import { EmptyState, Spinner } from '@/components/ui';
import LoginPage from '@/features/auth/LoginPage';
import DashboardPage from '@/features/dashboard/DashboardPage';
import CampaignsPage from '@/features/campaigns/CampaignsPage';
import CampaignCreatePage from '@/features/campaigns/CampaignCreatePage';
import CampaignDetailPage from '@/features/campaigns/CampaignDetailPage';
import ContentsPage from '@/features/contents/ContentsPage';
import ContentDetailPage from '@/features/contents/ContentDetailPage';
import ReviewsPage from '@/features/reviews/ReviewsPage';
import CalendarPage from '@/features/calendar/CalendarPage';
import AssistantPage from '@/features/assistant/AssistantPage';
import SettingsPage from '@/features/settings/SettingsPage';
import { AppLayout } from './layout/AppLayout';
import { NotFoundPage, RouteErrorPage } from './ErrorPages';

function FullScreenLoader() {
  return (
    <div className="flex h-screen items-center justify-center bg-canvas">
      <Spinner label="Đang tải MarketFlow" />
    </div>
  );
}

function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullScreenLoader />;
  if (!user) {
    const next = location.pathname + location.search;
    return <Navigate to={next && next !== '/' ? `/login?next=${encodeURIComponent(next)}` : '/login'} replace />;
  }
  return <AppLayout />;
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function RequireManager({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (!isManager(user)) {
    return (
      <EmptyState
        icon={<ShieldAlert />}
        title="Bạn không có quyền truy cập trang này"
        description="Trang này chỉ dành cho vai trò Quản lý."
        className="mt-16"
      />
    );
  }
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    path: '/login',
    errorElement: <RouteErrorPage />,
    element: (
      <GuestOnly>
        <LoginPage />
      </GuestOnly>
    ),
  },
  {
    path: '/register',
    errorElement: <RouteErrorPage />,
    element: (
      <GuestOnly>
        <LoginPage />
      </GuestOnly>
    ),
  },
  {
    path: '/',
    element: <RequireAuth />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'campaigns', element: <CampaignsPage /> },
      { path: 'campaigns/new', element: <CampaignCreatePage /> },
      { path: 'campaigns/:id', element: <CampaignDetailPage /> },
      { path: 'contents', element: <ContentsPage /> },
      { path: 'contents/:id', element: <ContentDetailPage /> },
      {
        path: 'reviews',
        element: (
          <RequireManager>
            <ReviewsPage />
          </RequireManager>
        ),
      },
      { path: 'calendar', element: <CalendarPage /> },
      {
        path: 'assistant',
        element: <Outlet />,
        children: [
          { index: true, element: <AssistantPage /> },
          { path: ':threadId', element: <AssistantPage /> },
        ],
      },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'settings/:section', element: <SettingsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
